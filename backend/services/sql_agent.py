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
- If the question references a policy rate, threshold, or definition not in the schema (e.g. "retention bonus %", "on-call stipend", "data localization countries"), call `retrieve` on that concept to pull the PDF text, then use `calculator` to apply it to your SQL results.
- `sample_rows` is for cases where you need to see actual rows before writing a complex SQL.

Hard rules (same as single-shot):
- Only reference tables and columns that actually exist. `describe` or `retrieve` first if unsure.
- Enum values are fixed — don't invent. Use `list_values` to verify.
- Watch null_rates: a column with null_rate ≈ 100% cannot be JOINed.
- For "X with Y" patterns, prefer EXISTS or GROUP BY over naive joins.
- Fuzzy negatives ("behind on", "hasn't bothered") = EXISTS on negative values, NOT `NOT EXISTS` on positive.
- If a concept isn't in the data, say so — don't substitute a loosely related column.
- Default budget: {max_iters} tool calls. Be efficient.

When you have enough information, stop calling tools and write the final answer. In your final answer:
- Quote exact numbers from SQL results (never estimate).
- Cite which sources you used (SQL query / PDF doc name).
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

    def _calculator(self, expression: str) -> dict:
        try:
            result = _safe_eval(expression)
            return {"ok": True, "expression": expression, "result": result}
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
                return self._calculator(args["expression"])
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
                    "description": "Evaluate an arithmetic expression safely (+, -, *, /, **, parens). Use for applying PDF-sourced rates to SQL results.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string"},
                        },
                        "required": ["expression"],
                    },
                },
            },
        ]

    # ---------- main loop ----------

    async def answer(self, question: str, role: str | None) -> dict:
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
                    temperature=0.0,
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
                temperature=0.0,
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
