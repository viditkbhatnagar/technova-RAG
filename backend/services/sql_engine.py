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
from backend.services.structured_ingest import load_schema_registry


class SQLValidationError(Exception):
    pass


_SYSTEM_PROMPT = """You are a SQL analyst for TechNova Inc. You write a SINGLE SQLite SELECT query to answer the user's question using ONLY the tables and columns provided in SCHEMA below.

Hard rules:
- Output ONLY the SQL query. No prose, no markdown fences, no comments.
- Use SELECT only. Never INSERT, UPDATE, DELETE, CREATE, DROP, ATTACH, or PRAGMA.
- Only reference tables and columns listed in SCHEMA. Do not invent columns.
- Quote string literals with single quotes. Use ISO dates 'YYYY-MM-DD'.
- If the question asks for rankings or top-N, include ORDER BY and LIMIT.
- Always include a LIMIT clause (<= {row_limit}). If the user doesn't specify, default to LIMIT {row_limit}.
- For aggregations, return the grouping columns alongside the aggregates.
- Join tables on the foreign keys shown in SCHEMA.
- Dates are stored as TEXT in 'YYYY-MM-DD' format — compare with string ranges or substr().
"""


class SQLEngine:
    def __init__(
        self,
        sqlite_path: Path | None = None,
        registry: dict | None = None,
    ):
        self.sqlite_path = Path(sqlite_path or settings.sqlite_db_file)
        self.registry = registry or load_schema_registry() or {"tables": []}
        self.row_limit = settings.sql_row_limit
        self.statement_timeout_ms = settings.sql_statement_timeout_ms

    def reload(self) -> None:
        self.registry = load_schema_registry() or {"tables": []}

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
            for c in t["columns"]:
                sample = c.get("sample_value")
                sample_str = f"  e.g. {sample!r}" if sample is not None else ""
                col_lines.append(f"    - {c['name']} {c['sqlite_type']}{sample_str}")
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
            example_block = "\n\nEXAMPLE JOIN PATHS (for reference only):\n" + "\n".join(
                f"- {e['question']}\n  {e['join_path']}" for e in examples
            )

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

    async def generate_sql(self, question: str, role: str | None) -> str:
        if not settings.openai_api_key:
            raise SQLValidationError(
                "SQL generation requires OPENAI_API_KEY to be configured."
            )
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        system = _SYSTEM_PROMPT.format(row_limit=self.row_limit)
        user = f"{self.schema_prompt(role)}\n\nQUESTION: {question}\n\nSQL:"
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
            max_tokens=500,
        )
        text = (resp.choices[0].message.content or "").strip()
        return _strip_code_fence(text)

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
            max_tokens=500,
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

        try:
            draft = await self.generate_sql(question, role)
        except OpenAIError as exc:
            return {"ok": False, "error": f"LLM error: {exc}", "attempts": []}
        except SQLValidationError as exc:
            return {"ok": False, "error": str(exc), "attempts": []}

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
