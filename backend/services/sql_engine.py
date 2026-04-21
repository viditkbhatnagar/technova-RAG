"""Safe text-to-SQL engine over the TechNova structured SQLite corpus.

Pipeline:
    question + role -> schema prompt (role-filtered) -> LLM draft SQL
                    -> sqlglot AST validation (SELECT only, visible tables)
                    -> sqlite execution (read-only, LIMIT enforced)
                    -> on error, one self-correcting retry with the error text

Security: the LLM is only shown tables whose security_level <= role clearance.
Validation rejects any SQL referencing a table outside that allowlist. This is
the real guarantee — prompt instructions are not a security boundary.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import sqlglot
from sqlglot import exp
from openai import AsyncOpenAI, OpenAIError

from backend.config import ROLE_CLEARANCE, settings
from backend.services.schema_glossary import load_glossary
from backend.services.structured_ingest import load_schema_registry


class SQLValidationError(Exception):
    pass


_SYSTEM_PROMPT = """You are a SQL analyst for TechNova Inc. Write a single SQLite SELECT query.

OUTPUT:
- Output only the SQL. No prose, no markdown fences.
- SELECT only. No INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/ATTACH/PRAGMA.
- Only reference tables and columns listed in SCHEMA. Never invent columns or literal values.
- Always include LIMIT (<= {row_limit}).

PRINCIPLES (use these to REASON, do not memorize):

1. SOURCE OF TRUTH. When multiple tables could contain a concept, pick the most specific one. Use the column samples and per-column profile (distinct counts, top values, null rate, min/max) to choose. If table A has a dedicated column for the concept (e.g. `asset_type` values) and table B only has a generic `amount`, A is the source of truth.

2. MAP EVERY SIGNIFICANT WORD TO A COLUMN. For each noun, adjective, scope word, and filter phrase in the question, find the column whose samples/values/name best match it. If nothing matches cleanly, the concept likely isn't in the data — do NOT substitute a loosely related column.

3. GRAIN = ENTITY IN THE QUESTION. If the user asks for a list of X, the SELECT grain is X. When joining through intermediaries, dedupe with DISTINCT on X's PK or GROUP BY X's columns. Never let joins through many-to-many tables explode rows.

4. "X WITH Y" PATTERN. Prefer `EXISTS` or `GROUP BY X.pk + HAVING ...` over naive joins. Pick join paths that match the real semantic relationship, not the shortest FK chain.

5. FUZZY NEGATIVES MEAN "INSUFFICIENT", NOT "ABSOLUTE ZERO". Phrases like "hasn't bothered with certifications", "behind on training", "lacking X", "missing Y" mean the person has at least one gap — not that they have zero of anything. Use the POSITIVE inclusive form: `EXISTS (... status IN ('Overdue','In Progress'))`. Do NOT use `NOT EXISTS (... status='Completed')` — that excludes everyone who has ever completed anything, which is virtually everyone.

6. ENUM MATCHING — LITERAL OVER LOOSE.
   a) EXACT MATCH FIRST. If the user's word case-insensitively matches one enum value exactly (e.g. user says "critical" and criticality_tier has value 'Critical'), filter to THAT value only — do not expand to related values. 'critical services' = `criticality_tier = 'Critical'`, not `IN ('Critical','High')`.
   b) INCLUSIVE ONLY FOR SYNONYMS. Only expand to multiple values when the user's word is a synonym or category that no single enum captures. e.g. "active" with values ['Active','In Use'] → both (both mean in-use). "serious incidents" with severity ['SEV-1','SEV-2','SEV-3','SEV-4'] → SEV-1 + SEV-2 (severity ladder, "serious" ≠ "Critical").
   c) When in doubt, prefer the narrower literal match — users expect precision.

7. CONSULT NULL RATES. A column profile with `null_rate` near 100% (especially ⚠ALWAYS-NULL) means that column cannot be JOIN-ed on. If revenue rows have customer_id always null, you cannot derive per-customer revenue — aggregate by whatever column IS populated (e.g. `region`, `department_id`).

8. ENUMS ARE CLOSED. Top values are the only valid values. Never invent (no 'Flagged', no 'Pending', no 'Failed' unless listed).

9. DO NOT OVER-FILTER. Do not add filters the user did not request. If the user says "engineers who did X", do not also filter by `department_id=Engineering` unless that's explicitly asked — "engineers" can be colloquial for "technical staff".

10. DATES are TEXT 'YYYY-MM-DD'. Compare with BETWEEN string ranges.

11. CONCEPTS NOT IN THE SCHEMA. If the user asks for something (e.g. "on-call pay", "retention bonus amount") and no column tracks it, DO NOT substitute a loosely related column. Leave that part out of the SQL; the narrative answer will flag it.
"""


_PLAN_PROMPT = """You are a SQL analyst planning a query against the TechNova database before writing it.

Question: {question}

Available schema (with per-column profile — top values, null rates, ranges):
{schema}

Produce a SHORT structured plan. For each concept/adjective/noun in the question, identify:
- which table.column is the source of truth for it
- what filter expression it becomes
- any schema gotchas (e.g. column is mostly NULL, concept not in data)

Also state:
- the SELECT grain (entity the user asked for)
- the join path, and whether DISTINCT / GROUP BY is needed
- any concept from the question that is NOT representable in the schema

Output as a numbered list, max 12 lines. Be precise — name exact tables/columns.
Do NOT write the SQL. Only the plan.
"""


_CRITIQUE_PROMPT = """You review SQL drafts against the user's question and the schema.

Question: {question}

Draft SQL:
{sql}

Schema:
{schema}

Check (each is a frequent silent-wrong-answer bug):
(a) Source-of-truth: for each concept, does the SQL use the MOST specific column? ('laptop spend' belongs in assets_licenses with asset_type='Laptop' + annual_cost, NOT financial_transactions.)
(b) Grain: does SELECT grain match the entity the user asked for? DISTINCT/GROUP BY needed?
(c) Enum INCLUSIVITY: did the SQL include ALL enum values that match the concept? If status has ['Active','In Use'] and question says "active", BOTH should be in WHERE. If severity has SEV-1/2/3/4 and question says "serious", at minimum SEV-1 AND SEV-2.
(d) Enum existence: every literal value in WHERE must appear in the column's top_values. No invented values.
(e) Null-rate trap: any JOIN on a column with null_rate≥99% (ALWAYS-NULL)? That join produces 0 rows — switch the aggregation to a populated column (region, department_id) or drop the join.
(f) Fuzzy negatives: "hasn't bothered", "behind on", "lacking" should become EXISTS on the negative values (Overdue, In Progress), NOT `NOT EXISTS` on Completed — the latter excludes essentially everyone.
(g) Over-filtering: did the SQL add filters (department, role, status) that the user did not state? Remove them.
(h) Unrepresentable concepts: if the question asks for X and no column tracks X, the SQL should leave it OUT (don't invent a proxy). The narrative answer will state it's unavailable.

If the draft is correct on all checks, output it unchanged.
Otherwise, output a corrected SQL. SQL only, no prose.
"""


class SQLEngine:
    def __init__(
        self,
        sqlite_path: Path | None = None,
        registry: dict | None = None,
    ):
        self.sqlite_path = Path(sqlite_path or settings.sqlite_db_file)
        self.registry = registry or load_schema_registry() or {"tables": []}
        self.glossary = load_glossary()
        self.row_limit = settings.sql_row_limit
        self.statement_timeout_ms = settings.sql_statement_timeout_ms

    def reload(self) -> None:
        self.registry = load_schema_registry() or {"tables": []}
        self.glossary = load_glossary()

    def is_ready(self) -> bool:
        return self.sqlite_path.exists() and bool(self.registry.get("tables"))

    def visible_tables(self, role: str | None) -> list[dict]:
        """Tables visible to this role (by security clearance)."""
        if role is None:
            clearance = max(ROLE_CLEARANCE.values())
        else:
            if role not in ROLE_CLEARANCE:
                raise ValueError(f"Unknown role: {role}")
            clearance = ROLE_CLEARANCE[role]
        return [t for t in self.registry["tables"] if t["security_level"] <= clearance]

    def restricted_tables(self, role: str | None) -> list[dict]:
        if role is None:
            return []
        clearance = ROLE_CLEARANCE.get(role, max(ROLE_CLEARANCE.values()))
        return [t for t in self.registry["tables"] if t["security_level"] > clearance]

    # ---------- schema prompt ----------

    def schema_prompt(self, role: str | None) -> str:
        tables = self.visible_tables(role)
        if not tables:
            return "(no tables visible to this role)"

        parts: list[str] = []
        for t in tables:
            col_lines = []
            table_gloss = (self.glossary or {}).get(t["name"], {})
            for c in t["columns"]:
                gloss = table_gloss.get(c["name"], {})
                col_lines.append("    - " + _format_column(c, gloss))
            fk_lines = []
            for fk in t.get("foreign_keys", []):
                fk_lines.append(f"    FK: {fk['column']} -> {fk['references']}")

            parts.append(
                f"TABLE {t['name']}  ({t['row_count']} rows, PK={t['primary_key']})\n"
                f"  -- {t['description']}\n"
                + "\n".join(col_lines)
                + ("\n" + "\n".join(fk_lines) if fk_lines else "")
            )

        examples = self.registry.get("example_queries", [])[:4]
        example_block = ""
        if examples:
            example_parts = []
            for e in examples:
                if e.get("sql"):
                    example_parts.append(
                        f"Q: {e['question']}\nSQL:\n{e['sql']};"
                    )
                elif e.get("join_path"):
                    example_parts.append(
                        f"Q: {e['question']}\nJoin path: {e['join_path']}"
                    )
            if example_parts:
                example_block = "\n\nFEW-SHOT EXAMPLES:\n" + "\n\n".join(example_parts)

        return "SCHEMA:\n" + "\n\n".join(parts) + example_block

    # ---------- validation ----------

    def validate_sql(self, sql: str, role: str | None) -> str:
        """Parse + allowlist check. Returns a canonicalized SQL string.

        Raises SQLValidationError on any issue.
        """
        if not sql or not sql.strip():
            raise SQLValidationError("Empty SQL.")

        cleaned = sql.strip().rstrip(";").strip()

        try:
            statements = sqlglot.parse(cleaned, read="sqlite")
        except Exception as exc:
            raise SQLValidationError(f"Could not parse SQL: {exc}") from exc

        if not statements or len(statements) != 1 or statements[0] is None:
            raise SQLValidationError("Exactly one SELECT statement is required.")
        tree = statements[0]

        disallowed = (
            exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop,
            exp.Alter, exp.Command,
        )
        for node in tree.walk():
            n = node[0]
            if isinstance(n, disallowed):
                raise SQLValidationError(f"Disallowed statement: {type(n).__name__}.")

        root = tree
        if not isinstance(root, (exp.Select, exp.Union, exp.Subquery, exp.With)):
            raise SQLValidationError("Only SELECT queries are allowed.")

        allowed = {t["name"] for t in self.visible_tables(role)}
        for t_node in tree.find_all(exp.Table):
            name = (t_node.name or "").lower()
            if not name:
                continue
            if name not in allowed:
                raise SQLValidationError(
                    f"Table '{name}' is not accessible at your clearance level."
                )

        lowered = cleaned.lower()
        for forbidden in ("attach ", "pragma ", "vacuum"):
            if forbidden in lowered:
                raise SQLValidationError(f"Forbidden token: {forbidden.strip()}.")

        if " limit " not in lowered and "\nlimit " not in lowered:
            cleaned = f"{cleaned}\nLIMIT {self.row_limit}"

        return cleaned

    # ---------- execution ----------

    def execute(self, sql: str) -> dict:
        """Run a validated SELECT in read-only mode. Caps rows at row_limit."""
        t0 = time.perf_counter()
        uri = f"file:{self.sqlite_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=self.statement_timeout_ms / 1000.0)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(sql)
            rows = cur.fetchmany(self.row_limit + 1)
            columns = [d[0] for d in cur.description] if cur.description else []
            truncated = len(rows) > self.row_limit
            rows = rows[: self.row_limit]
            result_rows = [dict(r) for r in rows]
        finally:
            conn.close()

        return {
            "columns": columns,
            "rows": result_rows,
            "row_count": len(result_rows),
            "truncated": truncated,
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        }

    # ---------- llm ----------

    async def plan_query(self, question: str, role: str | None) -> str:
        """First LLM pass: reason about which tables/columns answer the question
        and what schema gotchas apply. Output is a short plan that gets fed to
        generate_sql. No SQL yet.
        """
        if not settings.openai_api_key:
            return ""
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = _PLAN_PROMPT.format(
            question=question,
            schema=self.schema_prompt(role),
        )
        try:
            resp = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a careful SQL analyst. Output a plan, not SQL."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=400,
            )
            return (resp.choices[0].message.content or "").strip()
        except OpenAIError:
            return ""

    async def generate_sql(
        self, question: str, role: str | None, plan: str = ""
    ) -> str:
        if not settings.openai_api_key:
            raise SQLValidationError(
                "SQL generation requires OPENAI_API_KEY to be configured."
            )
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        system = _SYSTEM_PROMPT.format(row_limit=self.row_limit)
        plan_block = f"\n\nPLAN (follow this):\n{plan}" if plan else ""
        user = (
            f"{self.schema_prompt(role)}"
            f"{plan_block}"
            f"\n\nQUESTION: {question}\n\nSQL:"
        )
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
            max_tokens=900,
        )
        text = (resp.choices[0].message.content or "").strip()
        return _strip_code_fence(text)

    async def critique_sql(
        self, question: str, role: str | None, draft_sql: str
    ) -> str:
        """Second LLM pass: check the draft against the question; rewrite if needed.

        Catches the class of bugs where the draft parses and executes but returns
        wrong rows because it missed an adjective filter, exploded M:N joins, or
        invented an enum value.
        """
        if not settings.openai_api_key:
            return draft_sql
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = _CRITIQUE_PROMPT.format(
            question=question,
            sql=draft_sql,
            schema=self.schema_prompt(role),
        )
        try:
            resp = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You review SQL for correctness. Output SQL only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=600,
            )
            refined = _strip_code_fence((resp.choices[0].message.content or "").strip())
            return refined or draft_sql
        except OpenAIError:
            return draft_sql

    async def repair_sql(
        self, question: str, role: str | None, bad_sql: str, error: str
    ) -> str:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        system = _SYSTEM_PROMPT.format(row_limit=self.row_limit)
        user = (
            f"{self.schema_prompt(role)}\n\n"
            f"QUESTION: {question}\n\n"
            f"Your previous SQL failed:\n{bad_sql}\n\n"
            f"Error: {error}\n\n"
            f"Rewrite a correct SELECT. Output SQL only.\n\nSQL:"
        )
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
            max_tokens=900,
        )
        return _strip_code_fence((resp.choices[0].message.content or "").strip())

    # ---------- top-level ----------

    async def answer(self, question: str, role: str | None) -> dict:
        """Generate -> validate -> execute, with one self-correction attempt."""
        if not self.is_ready():
            return {
                "ok": False,
                "error": "SQL engine not ready — run /api/ingest first.",
                "attempts": [],
            }

        attempts: list[dict] = []
        t0 = time.perf_counter()

        # Plan step: the LLM first reasons about which tables/columns to use
        # and flags schema gotchas (null-rate traps, concepts not in data,
        # source-of-truth disambiguation). The plan is fed into generate_sql.
        plan = ""
        try:
            plan = await self.plan_query(question, role)
        except Exception as exc:
            print(f"[sql_engine] plan step failed (continuing): {exc}")

        try:
            draft = await self.generate_sql(question, role, plan=plan)
        except OpenAIError as exc:
            return {"ok": False, "error": f"LLM error: {exc}", "attempts": []}
        except SQLValidationError as exc:
            return {"ok": False, "error": str(exc), "attempts": []}

        # Critique pass: catches missing filters, M:N explosions, invented
        # enum values, null-rate traps that the plan missed.
        try:
            draft = await self.critique_sql(question, role, draft)
        except Exception as exc:
            print(f"[sql_engine] critique pass skipped: {exc}")

        validated: str | None = None
        exec_result: dict | None = None
        err_msg: str | None = None

        for attempt_idx in range(2):
            current_sql = draft if attempt_idx == 0 else draft
            try:
                validated = self.validate_sql(current_sql, role)
            except SQLValidationError as exc:
                err_msg = f"validation: {exc}"
                attempts.append({"sql": current_sql, "error": err_msg})
                if attempt_idx == 0:
                    try:
                        draft = await self.repair_sql(question, role, current_sql, err_msg)
                    except OpenAIError as oe:
                        err_msg = f"LLM repair error: {oe}"
                        break
                    continue
                break

            try:
                exec_result = self.execute(validated)
                attempts.append({"sql": validated, "error": None})
                err_msg = None
                break
            except sqlite3.Error as exc:
                err_msg = f"execution: {exc}"
                attempts.append({"sql": validated, "error": err_msg})
                if attempt_idx == 0:
                    try:
                        draft = await self.repair_sql(question, role, validated, err_msg)
                    except OpenAIError as oe:
                        err_msg = f"LLM repair error: {oe}"
                        break
                    continue
                break

        total_ms = int((time.perf_counter() - t0) * 1000)

        if exec_result is None:
            return {
                "ok": False,
                "error": err_msg or "SQL generation failed.",
                "attempts": attempts,
                "total_elapsed_ms": total_ms,
            }

        return {
            "ok": True,
            "sql": validated,
            "columns": exec_result["columns"],
            "rows": exec_result["rows"],
            "row_count": exec_result["row_count"],
            "truncated": exec_result["truncated"],
            "elapsed_ms": exec_result["elapsed_ms"],
            "total_elapsed_ms": total_ms,
            "attempts": attempts,
        }


def _format_column(c: dict, gloss: dict | None = None) -> str:
    """One line per column describing type, data shape, and statistics.
    The LLM uses this to pick the right column for each concept in the question.
    """
    sqlite_type = c.get("sqlite_type", "TEXT")
    name = c["name"]
    pieces = [f"{name} {sqlite_type}"]
    if gloss:
        desc = gloss.get("description")
        aliases = gloss.get("aliases") or []
        if desc:
            pieces.append(f"— {desc}")
        if aliases:
            pieces.append(f"phrases: [{', '.join(aliases[:4])}]")

    null_rate = c.get("null_rate")
    distinct_count = c.get("distinct_count")
    top_values = c.get("top_values") or []

    if sqlite_type == "TEXT":
        if distinct_count is not None and 0 < distinct_count <= 12 and top_values:
            # closed enum — list all values with frequencies
            vals = [f"{tv['value']!r}×{tv['count']}" for tv in top_values[:distinct_count]]
            pieces.append(f"values: [{', '.join(vals)}]")
        elif top_values:
            # open text — show top-3 + distinct count
            sample_vals = [f"{tv['value']!r}×{tv['count']}" for tv in top_values[:3]]
            pieces.append(
                f"top: [{', '.join(sample_vals)}] of {distinct_count} distinct"
            )
        else:
            sample = c.get("sample_value")
            if sample is not None:
                pieces.append(f"e.g. {sample!r}")
    elif sqlite_type in ("INTEGER", "REAL"):
        mn, mx, avg = c.get("min"), c.get("max"), c.get("mean")
        if mn is not None and mx is not None:
            pieces.append(f"range: [{mn} .. {mx}] mean={avg}")
        elif c.get("sample_value") is not None:
            pieces.append(f"e.g. {c['sample_value']!r}")
    elif sqlite_type == "DATE":
        mn, mx = c.get("min_date"), c.get("max_date")
        if mn and mx:
            pieces.append(f"range: [{mn} .. {mx}]")

    if null_rate is not None and null_rate > 0:
        pct = int(round(null_rate * 100))
        flag = " ⚠ALWAYS-NULL" if null_rate >= 0.99 else ""
        pieces.append(f"null_rate={pct}%{flag}")

    return "  ".join(pieces)


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if text.lower().startswith("sql:"):
        text = text[4:].strip()
    return text


def format_rows_for_llm(result: dict, max_rows: int = 50) -> str:
    """Render SQL result as a markdown table for inclusion in the answer prompt."""
    if not result.get("ok"):
        return f"[SQL error: {result.get('error')}]"
    cols = result["columns"]
    rows = result["rows"][:max_rows]
    if not cols:
        return "(no columns)"
    if not rows:
        return f"Query returned 0 rows.\nSQL:\n{result['sql']}"
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = [
        "| " + " | ".join(_fmt_cell(r.get(c)) for c in cols) + " |"
        for r in rows
    ]
    note = ""
    if result.get("truncated") or len(result["rows"]) > max_rows:
        note = f"\n(showing first {len(rows)} of {result['row_count']}"
        if result.get("truncated"):
            note += "+ truncated at server row-limit"
        note += ")"
    return "\n".join([header, sep, *body]) + note


def _fmt_cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        return f"{v:.4f}".rstrip("0").rstrip(".")
    s = str(v)
    return s.replace("|", "\\|").replace("\n", " ")
