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

from backend.config import ROLE_CLEARANCE, TABLE_HINTS, settings
from backend.services.structured_ingest import load_schema_registry


class SQLValidationError(Exception):
    pass


_SYSTEM_PROMPT = """You are a SQL analyst for TechNova Inc. You write a SINGLE SQLite SELECT query to answer the user's question using ONLY the tables and columns in SCHEMA below.

OUTPUT:
- Output ONLY the SQL query. No prose, no markdown fences, no comments.
- Use SELECT only. Never INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/ATTACH/PRAGMA.
- Only reference tables and columns listed in SCHEMA. Do not invent columns or values.
- Always include a LIMIT clause (<= {row_limit}). Default LIMIT {row_limit}.

CRITICAL RULES for correctness:

1) ADJECTIVE → WHERE FILTER. Every adjective, category, or scope word in the question must become a WHERE filter. Examples:
   - "critical services"        -> WHERE criticality_tier = 'Critical'
   - "flagged vendors"          -> WHERE risk_status IN ('Conditional','Suspended')
   - "active employees"         -> WHERE employment_status = 'Active'
   - "overdue training"         -> WHERE status = 'Overdue'
   - "training gap" / "behind"  -> WHERE status != 'Completed'
   - "SEV-1 or SEV-2 incidents" -> WHERE severity IN ('SEV-1','SEV-2')
   - "this fiscal year"         -> date range or period_quarter LIKE '%FY2025-26'
   See the per-table HINTS in SCHEMA for the canonical mapping.

2) ENUM VALUES ARE FIXED. A column shown as `values: [...]` has ONLY those values — never invent new ones (no 'Flagged', no 'Failed', no 'Pending' unless listed).

3) GRAIN = ENTITY IN QUESTION. If the user asks for a list of entity X (services, customers, vendors, incidents…), the SELECT must be at the grain of X — not X × employees × licenses. When you JOIN through intermediate tables, use DISTINCT or GROUP BY on the entity's primary key to dedupe. Never return repeated rows of the same entity.

4) "X WITH Y" needs EXISTS / aggregation, not naive JOIN. For questions like "services whose owning team has a flagged vendor", prefer one of:
   - SELECT ... FROM X JOIN Y ... WHERE ... GROUP BY X.pk  (and aggregate Y with GROUP_CONCAT / COUNT)
   - SELECT ... FROM X WHERE EXISTS (SELECT 1 FROM Y WHERE ...)
   Do NOT explode X by joining through per-employee tables unless the question is per-employee.

5) JOIN via FOREIGN KEYS shown in SCHEMA. For service→vendor relationships go via shared owner_department_id, NOT via assets_licenses (which is employee hardware).

6) DATES are TEXT in 'YYYY-MM-DD'. Use BETWEEN '2026-01-01' AND '2026-12-31' for year ranges.
"""


_CRITIQUE_PROMPT = """You review SQL drafts for a corporate analyst.

The user asked: {question}

The draft SQL is:
{sql}

Available schema:
{schema}

Check the draft against these rules:
(a) Does every adjective / category / scope word from the question become a WHERE filter? (e.g. "critical" -> criticality_tier='Critical', "flagged" -> risk_status IN ('Conditional','Suspended'), "overdue" -> status='Overdue').
(b) Does the SELECT grain match the entity the user asked about? If the question says "show me X" and the SQL joins through other tables, it needs DISTINCT on X's PK or GROUP BY on X's columns — otherwise rows will be duplicated.
(c) Are all enum values used in WHERE actually listed in the schema's `values: [...]` for that column? Invented values = 0 rows.
(d) For "X with any Y" patterns, prefer EXISTS or GROUP BY on X over a naive join that explodes rows.

If the draft is correct on all four, output the draft SQL unchanged.
Otherwise, output a corrected SQL query. Output SQL ONLY, no prose.
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
                distinct_count = c.get("distinct_count")
                distinct = c.get("distinct_preview") or []
                is_enum = (
                    c.get("sqlite_type") == "TEXT"
                    and distinct_count is not None
                    and distinct_count <= 10
                    and distinct
                )
                if is_enum:
                    vals = ", ".join(repr(v) for v in distinct[:distinct_count])
                    val_str = f"  values: [{vals}]"
                else:
                    sample = c.get("sample_value")
                    val_str = f"  e.g. {sample!r}" if sample is not None else ""
                col_lines.append(f"    - {c['name']} {c['sqlite_type']}{val_str}")
            fk_lines = []
            for fk in t.get("foreign_keys", []):
                fk_lines.append(f"    FK: {fk['column']} -> {fk['references']}")

            hint_lines = []
            for h in TABLE_HINTS.get(t["name"], []):
                hint_lines.append(f"    HINT: {h}")

            parts.append(
                f"TABLE {t['name']}  ({t['row_count']} rows, PK={t['primary_key']})\n"
                f"  -- {t['description']}\n"
                + "\n".join(col_lines)
                + ("\n" + "\n".join(fk_lines) if fk_lines else "")
                + ("\n" + "\n".join(hint_lines) if hint_lines else "")
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

        # Critique pass: catches missing filters, M:N explosions, invented
        # enum values. One extra LLM call — worth it for correctness.
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
