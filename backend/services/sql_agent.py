"""ReAct-style tool-use agent for structured-data questions.

The agent replaces the single-shot plan→draft→critique chain for
SQL/hybrid questions. It can call multiple tools in sequence, so it
handles multi-step queries naturally — e.g. questions that need two SQL
queries + a policy number retrieved from a PDF + a final arithmetic step.

Available tools (all respect role-based clearance):
- run_sql(query):     validate + execute a SELECT, return rows
- retrieve(query):    semantic search over PDFs + row docs + schema docs
- list_values(...):   distinct values for a column (cardinality check)
- sample_rows(...):   peek at actual rows of a table
- describe(table):    focused column profile + glossary for one table
- calculator(expr):   safe arithmetic (no eval, AST-walked)

The agent is cost-bounded: `max_iterations` tool calls (default 8). After
that it's forced to produce a final answer with what it has.

Security: every tool goes through `SQLEngine.validate_sql` or the
existing retriever's security filter. A restricted table blocked at the
SQL level cannot be probed via any tool path.
"""

from __future__ import annotations

import ast
import json
import operator
import sqlite3
import time
from typing import Any

from openai import AsyncOpenAI, OpenAIError

from backend.config import ROLE_CLEARANCE, settings
from backend.services.embedder import EmbeddingService
from backend.services.retriever import HybridRetriever
from backend.services.security import get_allowed_chunk_ids, get_security_filter
from backend.services.sql_engine import SQLEngine, SQLValidationError
from backend.services.store import QdrantStore


_AGENT_SYSTEM = """You are a data analyst for TechNova Inc. Answer the user's question using the available tools. Think step by step.

Strategy:
- For numeric, listing, ranking, or filtering questions, call `run_sql` with a SELECT query (SQLite dialect, LIMIT <= {row_limit}).
- If you are unsure which table or column holds a concept, call `retrieve` (it semantic-searches PDFs + schema docs + row docs), or `describe(table)` for a focused profile, or `list_values(table, column)` for the distinct values.
- If the question references a policy rate, threshold, or definition not in the schema (e.g. "retention bonus %", "on-call stipend", "data localization countries"), call `retrieve` on that concept FIRST to pull the PDF text, then use `calculator` to apply it to your SQL results.
- `sample_rows` is for cases where you need to see actual rows before writing a complex SQL.

Hard rules:
- Only reference tables and columns that actually exist. `describe` or `retrieve` first if unsure.
- Enum values are fixed — don't invent. Use `list_values` to verify.
- Watch null_rates: a column with null_rate ≈ 100% cannot be JOINed.
- For "X with Y" patterns, prefer EXISTS or GROUP BY over naive joins.
- Fuzzy negatives ("behind on", "hasn't bothered") = EXISTS on negative values, NOT `NOT EXISTS` on positive.
- If a concept isn't in the data, say so — don't substitute a loosely related column.
- Default budget: {max_iters} tool calls. Be efficient.

UNIT DISCIPLINE (critical — past failures mixed lakhs with rupees):
- Every column amount has a unit implied by its name (e.g. `total_ctc_inr_lakhs` is LAKHS, `annual_cost` on assets is INR (rupees), `amount` in financial_transactions is CRORES per `amount_unit`).
- Before passing numbers to `calculator`, verify they are all in the SAME unit. Convert if not:
    1 crore = 100 lakhs = 10,000,000 rupees.
    1 lakh = 100,000 rupees.
- When applying a per-unit rate (e.g. ₹5,000/week on-call × 8 weeks × N engineers), express the rate in the same unit as the other numbers. Example: if CTCs are in lakhs, on-call is 5000/100000 = 0.05 lakhs/week.
- Always state units in your final answer (e.g. "₹96.04 lakhs" not "96.04").
- In every `calculator` call, mentally verify: what unit is the result? Match the surrounding numbers.

AMBIGUITY HANDLING (state assumptions explicitly):
- Fuzzy business terms often have multiple valid interpretations. Examples:
    "senior engineering" → could mean L4+ or L5+
    "certifications" → could mean any training module OR external certs only
    "regulated Asian markets" → could mean APAC broadly OR countries with data-localization laws specifically (Vietnam, Indonesia, India)
    "this year" / "last year" → calendar year vs fiscal year
- When you detect ambiguity, use `retrieve` and `list_values` to ground the interpretation in the actual data (e.g. look at what level distribution exists, or retrieve the board minutes for "regulated markets").
- If multiple interpretations remain plausible, pick the broader / more inclusive one, and STATE THE ASSUMPTION in your final answer under an "Assumptions" section.

GRAIN:
- If the user asks for a list of entity X, the answer should be at the grain of X. Use DISTINCT / GROUP BY to dedupe when joining through intermediate tables.

FINAL ANSWER FORMAT:
- Quote exact numbers from SQL results with their units.
- Cite which sources you used (SQL query tables / PDF doc names).
- Include a short "Assumptions:" section when you had to interpret fuzzy terms.
- If part of the question couldn't be answered from the data, say so plainly.
"""


# ---------- Safe calculator ----------

_MATH_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(expr: str) -> float:
    def _eval(node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"non-numeric constant: {node.value!r}")
        if isinstance(node, ast.BinOp):
            return _MATH_OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            return _MATH_OPS[type(node.op)](_eval(node.operand))
        raise ValueError(f"unsupported: {ast.dump(node)}")

    tree = ast.parse(expr, mode="eval")
    return _eval(tree.body)


# ---------- Agent ----------

class SQLAgent:
    def __init__(
        self,
        sql_engine: SQLEngine,
        retriever: HybridRetriever,
        store: QdrantStore,
        embedder: EmbeddingService,
    ):
        self.sql = sql_engine
        self.retriever = retriever
        self.store = store
        self.embedder = embedder
        self.max_iters = settings.sql_agent_max_iters
        self.row_limit = settings.sql_row_limit

    # ---------- tool handlers ----------

    def _run_sql(self, query: str, role: str | None) -> dict:
        try:
            validated = self.sql.validate_sql(query, role)
            result = self.sql.execute(validated)
            return {
                "ok": True,
                "sql": validated,
                "columns": result["columns"],
                "rows": result["rows"][:30],
                "row_count": result["row_count"],
                "truncated": result["truncated"] or result["row_count"] > 30,
            }
        except SQLValidationError as exc:
            return {"ok": False, "error": f"validation: {exc}"}
        except sqlite3.Error as exc:
            return {"ok": False, "error": f"execution: {exc}"}

    def _retrieve(
        self, query: str, top_k: int, role: str | None
    ) -> dict:
        security_filter = get_security_filter(role) if role else None
        allowed_ids = (
            get_allowed_chunk_ids(self.store, role) if role else None
        )
        r = self.retriever.retrieve(
            query=query,
            top_k=top_k,
            top_k_retrieval=max(10, top_k * 2),
            rrf_k=settings.rrf_k,
            security_filter=security_filter,
            allowed_chunk_ids=allowed_ids,
        )
        return {
            "chunks": [
                {
                    "doc_name": c.get("doc_name"),
                    "source_type": c.get("source_type", "document_chunk"),
                    "table": c.get("table"),
                    "text": (c.get("text") or "")[:600],
                    "score": round(float(c.get("rerank_score", c.get("rrf_score", 0.0))), 3),
                }
                for c in r["chunks"]
            ]
        }

    def _list_values(
        self, table: str, column: str, role: str | None
    ) -> dict:
        sql = (
            f"SELECT {column}, COUNT(*) AS count "
            f"FROM {table} WHERE {column} IS NOT NULL "
            f"GROUP BY {column} ORDER BY count DESC LIMIT 25"
        )
        return self._run_sql(sql, role)

    def _sample_rows(
        self, table: str, n: int, where: str | None, role: str | None
    ) -> dict:
        n = max(1, min(int(n), 10))
        where_clause = f" WHERE {where}" if where else ""
        sql = f"SELECT * FROM {table}{where_clause} LIMIT {n}"
        return self._run_sql(sql, role)

    def _describe(self, table: str, role: str | None) -> dict:
        visible = {t["name"] for t in self.sql.visible_tables(role)}
        if table not in visible:
            return {"ok": False, "error": f"Table '{table}' not accessible at your clearance."}
        t = next(
            (x for x in self.sql.registry.get("tables", []) if x["name"] == table),
            None,
        )
        if t is None:
            return {"ok": False, "error": f"Unknown table: {table}"}
        gl = (self.sql.glossary or {}).get(table, {})
        return {
            "ok": True,
            "name": table,
            "description": t.get("description"),
            "row_count": t.get("row_count"),
            "primary_key": t.get("primary_key"),
            "columns": [
                {
                    "name": c["name"],
                    "type": c.get("sqlite_type"),
                    "description": (gl.get(c["name"]) or {}).get("description", ""),
                    "aliases": (gl.get(c["name"]) or {}).get("aliases", []),
                    "top_values": c.get("top_values", [])[:6],
                    "null_rate": c.get("null_rate", 0),
                    "min": c.get("min"),
                    "max": c.get("max"),
                }
                for c in t.get("columns", [])
            ],
            "foreign_keys": t.get("foreign_keys", []),
        }

    def _calculator(self, expression: str, unit: str = "") -> dict:
        try:
            result = _safe_eval(expression)
            return {
                "ok": True,
                "expression": expression,
                "result": result,
                "unit": unit or "(unit unspecified — state it in the final answer)",
            }
        except Exception as exc:
            return {"ok": False, "error": f"calculator error: {exc}"}

    # ---------- tool dispatch ----------

    def _dispatch(self, name: str, args: dict, role: str | None) -> dict:
        try:
            if name == "run_sql":
                return self._run_sql(args["query"], role)
            if name == "retrieve":
                return self._retrieve(args["query"], int(args.get("top_k", 5)), role)
            if name == "list_values":
                return self._list_values(args["table"], args["column"], role)
            if name == "sample_rows":
                return self._sample_rows(
                    args["table"], int(args.get("n", 3)), args.get("where"), role
                )
            if name == "describe":
                return self._describe(args["table"], role)
            if name == "calculator":
                return self._calculator(args["expression"], args.get("unit", ""))
            return {"ok": False, "error": f"unknown tool: {name}"}
        except KeyError as exc:
            return {"ok": False, "error": f"missing argument: {exc}"}

    # ---------- OpenAI function-calling schemas ----------

    def _tools_spec(self, role: str | None) -> list[dict]:
        visible = [t["name"] for t in self.sql.visible_tables(role)]
        return [
            {
                "type": "function",
                "function": {
                    "name": "run_sql",
                    "description": "Validate and execute a SQLite SELECT query. Returns columns + rows (capped at 30). Only SELECT; no DDL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "A single SQLite SELECT."}
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "retrieve",
                    "description": "Hybrid semantic + BM25 search over PDFs, incident row-docs, column docs, and value docs. Use when you need policy rates, definitions, or to discover which table holds a concept.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_values",
                    "description": "Get the distinct values of a column with counts. Use when you are unsure which literal value to filter on.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table": {"type": "string", "enum": visible},
                            "column": {"type": "string"},
                        },
                        "required": ["table", "column"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "sample_rows",
                    "description": "Peek at a few rows of a table to understand real data shape before writing complex SQL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table": {"type": "string", "enum": visible},
                            "n": {"type": "integer", "default": 3, "minimum": 1, "maximum": 10},
                            "where": {"type": "string", "description": "Optional WHERE clause (without the keyword)."},
                        },
                        "required": ["table"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "describe",
                    "description": "Return full column profile + business glossary for a single table (focused view, less noisy than the system schema prompt).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table": {"type": "string", "enum": visible},
                        },
                        "required": ["table"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": (
                        "Evaluate an arithmetic expression safely (+, -, *, /, **, parens). "
                        "CRITICAL UNIT RULE: every number in the expression must be in the "
                        "SAME unit. If mixing lakhs (like CTC) with rupees (like ₹5,000/week), "
                        "convert first: 1 lakh = 100,000 rupees, 1 crore = 100 lakhs. "
                        "Example: to apply ₹5,000/week × 8 weeks to 13 engineers whose CTCs are "
                        "in lakhs, express as (5000*8*13)/100000 to get lakhs. "
                        "Also provide the `unit` parameter so the result can be reported correctly."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string"},
                            "unit": {
                                "type": "string",
                                "description": "The unit of the result, e.g. 'lakhs', 'crores', 'INR', '%', 'count'.",
                            },
                        },
                        "required": ["expression", "unit"],
                    },
                },
            },
        ]

    # ---------- self-consistency orchestration ----------

    async def answer_with_voting(
        self, question: str, role: str | None, samples: int = 3
    ) -> dict:
        """Run the agent `samples` times in parallel, then reconcile the answers.

        When multiple runs agree, returns the consensus. When they disagree
        (common on ambiguous queries), a final reconciler LLM call picks the
        most defensible answer, explicitly listing the disagreement so the user
        sees it.

        Cost: samples × single-run cost + 1 reconciler call. At samples=3 this
        is ~$0.04-0.10 per hard query — acceptable for enterprise use-cases.
        """
        import asyncio

        if samples <= 1:
            return await self.answer(question, role, temperature=0.0)

        # Run N independent agent passes with slightly different temperatures
        # (0.0, 0.3, 0.5) to get genuine diversity without going off the rails
        temps = [0.0, 0.3, 0.5][:samples] + [0.4] * max(0, samples - 3)
        outcomes = await asyncio.gather(
            *[self.answer(question, role, temperature=t) for t in temps[:samples]],
            return_exceptions=True,
        )
        successful = [o for o in outcomes if isinstance(o, dict) and o.get("ok")]
        if not successful:
            first = outcomes[0] if outcomes else {"ok": False, "error": "all samples failed"}
            return first if isinstance(first, dict) else {"ok": False, "error": str(first)}
        if len(successful) == 1:
            return successful[0]

        # Reconcile: ask an LLM to pick or merge, showing all drafts
        reconciled = await self._reconcile(question, successful)
        # Attach the first successful run's trace/sql results for UI rendering
        primary = successful[0]
        return {
            "ok": True,
            "answer": reconciled,
            "trace": primary.get("trace", []),
            "iterations": primary.get("iterations"),
            "total_elapsed_ms": sum(
                int(o.get("total_elapsed_ms") or 0) for o in successful
            ),
            "sql_results": primary.get("sql_results", []),
            "self_consistency_samples": len(successful),
        }

    async def _reconcile(self, question: str, drafts: list[dict]) -> str:
        """Pick or merge answers from multiple agent runs."""
        if not settings.openai_api_key:
            return drafts[0].get("answer", "")
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        drafts_text = "\n\n".join(
            f"---- DRAFT {i+1} ----\n{d.get('answer', '')}"
            for i, d in enumerate(drafts)
        )
        system = (
            "You reconcile multiple LLM-generated answers to the same question. "
            "Return the single most accurate final answer. If the drafts AGREE on key "
            "numeric facts, return one consolidated answer. If they DISAGREE, pick the "
            "draft whose reasoning is most grounded (cites exact columns/tables/PDFs, "
            "uses consistent units, states assumptions), and call out the disagreement "
            "in an 'Analysis note:' line at the end so the user knows. Keep the final "
            "answer concise and professional."
        )
        try:
            resp = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"QUESTION: {question}\n\n{drafts_text}"},
                ],
                temperature=0.0,
                max_tokens=1200,
            )
            return (resp.choices[0].message.content or "").strip() or drafts[0].get("answer", "")
        except OpenAIError:
            return drafts[0].get("answer", "")

    # ---------- main loop ----------

    async def answer(
        self,
        question: str,
        role: str | None,
        temperature: float = 0.0,
    ) -> dict:
        """ReAct loop: LLM picks tools until it has enough to answer."""
        if not settings.openai_api_key:
            return {
                "ok": False,
                "error": "Agent requires OPENAI_API_KEY.",
                "trace": [],
            }

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        tools = self._tools_spec(role)

        system_prompt = _AGENT_SYSTEM.format(
            row_limit=self.row_limit,
            max_iters=self.max_iters,
        )
        schema_summary = self.sql.schema_prompt(role)

        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"SCHEMA SUMMARY (for reference; use `describe` or `retrieve` for more):\n"
                    f"{schema_summary}\n\nQUESTION: {question}"
                ),
            },
        ]

        trace: list[dict] = []
        sql_results: list[dict] = []  # structured SQL results we ran
        t0 = time.perf_counter()

        for step in range(self.max_iters):
            try:
                resp = await client.chat.completions.create(
                    model=settings.llm_model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=temperature,
                    max_tokens=1200,
                )
            except OpenAIError as exc:
                return {
                    "ok": False,
                    "error": f"LLM error: {exc}",
                    "trace": trace,
                    "iterations": step,
                }

            msg = resp.choices[0].message
            tool_calls = msg.tool_calls or []
            messages.append(_serialize_assistant(msg))

            if not tool_calls:
                final_answer = (msg.content or "").strip()
                total_ms = int((time.perf_counter() - t0) * 1000)
                return {
                    "ok": True,
                    "answer": final_answer,
                    "trace": trace,
                    "iterations": step + 1,
                    "total_elapsed_ms": total_ms,
                    "sql_results": sql_results,
                }

            for tc in tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = self._dispatch(name, args, role)

                trace.append(
                    {
                        "step": step,
                        "tool": name,
                        "args": args,
                        "result_preview": _preview(result),
                    }
                )
                if name == "run_sql" and result.get("ok"):
                    sql_results.append(
                        {
                            "sql": result.get("sql"),
                            "columns": result.get("columns"),
                            "rows": result.get("rows"),
                            "row_count": result.get("row_count"),
                        }
                    )

                tool_content = json.dumps(result, default=str)
                if len(tool_content) > 4000:
                    tool_content = tool_content[:4000] + "...<truncated>"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_content,
                    }
                )

        # Exceeded iteration budget — force final answer
        messages.append(
            {
                "role": "user",
                "content": (
                    "You've reached the tool budget. Write the final answer now using "
                    "what you have. Call out any part of the question you could not "
                    "confirm."
                ),
            }
        )
        try:
            resp = await client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=temperature,
                max_tokens=900,
            )
            final = (resp.choices[0].message.content or "").strip()
        except OpenAIError as exc:
            final = f"[Agent exceeded tool budget and final call failed: {exc}]"

        total_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "ok": True,
            "answer": final,
            "trace": trace,
            "iterations": self.max_iters,
            "exceeded": True,
            "total_elapsed_ms": total_ms,
            "sql_results": sql_results,
        }


def _serialize_assistant(msg) -> dict:
    """Convert an OpenAI message object to the plain dict OpenAI expects back."""
    d: dict = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return d


def _preview(result: dict, limit: int = 400) -> str:
    s = json.dumps(result, default=str)
    return s if len(s) <= limit else s[:limit] + "..."
