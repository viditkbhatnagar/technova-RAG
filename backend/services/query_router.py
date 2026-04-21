"""Route a natural-language question to SQL (structured), RAG (text), or both.

Heuristic first — cheap, deterministic; LLM fallback only when ambiguous.
The router's output is informational to the orchestrator in `routers/query.py`:
which retrieval path(s) to run and how to blend them.
"""

from __future__ import annotations

import re
from typing import Literal

from openai import AsyncOpenAI, OpenAIError

from backend.config import ROLE_CLEARANCE, TABLE_METADATA, settings


Route = Literal["sql", "rag", "hybrid"]


_SQL_VERBS = re.compile(
    r"\b(count|sum|average|avg|mean|median|total|how many|top \d+|rank|"
    r"list all|list the|highest|lowest|most|least|greatest|smallest|"
    r"per department|per employee|per vendor|per customer|per quarter|"
    r"group by|breakdown|distribution|compare|compared|versus|vs\.?|"
    r"ratio|percentage|percent|rate|above|below|more than|less than|"
    r"between \d|since \d|before \d|after \d|in (q[1-4]|fy\d|\d{4}))\b",
    re.IGNORECASE,
)

_RAG_VERBS = re.compile(
    r"\b(explain|describe|tell me about|what is|what are|why|how does|"
    r"summari[sz]e|overview|policy|procedure|guideline|process|"
    r"handbook|playbook|runbook|roadmap|narrative|story)\b",
    re.IGNORECASE,
)

_TABLE_SIGNALS = {
    # canonical table → keywords that hint at that table
    "departments": ["department", "cost center", "budget"],
    "employees": ["employee", "staff", "headcount", "manager", "reports to", "hire date"],
    "salary_records": ["salary", "compensation", "ctc", "esop", "pay", "bonus", "variable"],
    "customers": ["customer", "account", "arr", "tier", "renewal", "contract value"],
    "products_services": ["service", "microservice", "product", "sla", "uptime", "criticality"],
    "incidents": ["incident", "sev-", "breach", "outage", "remediation", "ransomware"],
    "vendors": ["vendor", "sig-lite", "supplier", "contract", "risk status"],
    "financial_transactions": ["revenue", "spend", "p&l", "pnl", "capex", "opex", "transaction"],
    "training_compliance": ["training", "certification", "compliance", "module", "dpdp", "infosec"],
    "assets_licenses": ["laptop", "license", "asset", "macbook", "thinkpad", "gpu", "workstation"],
}


def _normalized(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())


def _matched_tables(q: str) -> list[str]:
    qn = _normalized(q)
    hits: list[str] = []
    for table, kws in _TABLE_SIGNALS.items():
        for kw in kws:
            if kw in qn:
                hits.append(table)
                break
    return hits


def required_restricted_tables(query: str, role: str | None) -> list[str]:
    """Tables the question topically mentions that the role CANNOT access.

    Used to short-circuit with access_denied before the LLM silently
    substitutes a different (accessible) table and produces a wrong answer.
    """
    if role is None:
        return []
    clearance = ROLE_CLEARANCE.get(role)
    if clearance is None:
        return []
    hits = _matched_tables(query)
    restricted: list[str] = []
    for table in hits:
        meta = TABLE_METADATA.get(table)
        if meta and meta["security_level"] > clearance:
            restricted.append(table)
    return restricted


def heuristic_route(query: str) -> dict:
    """First-pass classification with no LLM call.

    Returns {route, reason, signals: {...}}. Callers should consult
    `confidence` — if 'low', escalate to `llm_route`.
    """
    qn = _normalized(query)
    sql_hits = bool(_SQL_VERBS.search(qn))
    rag_hits = bool(_RAG_VERBS.search(qn))
    tables = _matched_tables(qn)
    has_digit = bool(re.search(r"\b\d", qn))

    signals = {
        "sql_verbs": sql_hits,
        "rag_verbs": rag_hits,
        "tables_matched": tables,
        "has_number": has_digit,
    }

    if sql_hits and tables:
        return {
            "route": "sql",
            "confidence": "high",
            "reason": f"analytical verbs + table signals ({', '.join(tables)})",
            "signals": signals,
        }
    if sql_hits and has_digit and not rag_hits:
        return {
            "route": "sql",
            "confidence": "medium",
            "reason": "analytical verbs with numeric context but no clear table hit",
            "signals": signals,
        }
    if tables and not rag_hits:
        return {
            "route": "hybrid",
            "confidence": "medium",
            "reason": f"table signals without analytic verbs — blend SQL + RAG",
            "signals": signals,
        }
    if rag_hits and not sql_hits and not tables:
        return {
            "route": "rag",
            "confidence": "high",
            "reason": "narrative verbs + no structured signals",
            "signals": signals,
        }
    if rag_hits and tables:
        return {
            "route": "hybrid",
            "confidence": "medium",
            "reason": "narrative verbs but question mentions structured tables",
            "signals": signals,
        }
    return {
        "route": "rag",
        "confidence": "low",
        "reason": "no strong signals — defaulting to RAG, may escalate",
        "signals": signals,
    }


_LLM_SYSTEM = """You are a query router for a corporate assistant. Decide how to answer the user's question:

- "sql"    -> answerable from structured tables (counts, sums, rankings, filters, lookups by ID).
- "rag"    -> answerable from policy documents / narrative PDFs (concepts, procedures, explanations).
- "hybrid" -> needs BOTH structured aggregates and narrative context.

Tables available: {tables}

Reply with JSON only: {{"route": "sql"|"rag"|"hybrid", "reason": "<1 short sentence>"}}.
"""


async def llm_route(query: str) -> dict:
    if not settings.openai_api_key:
        return {"route": "rag", "confidence": "fallback", "reason": "no LLM configured"}
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    table_list = ", ".join(TABLE_METADATA.keys())
    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _LLM_SYSTEM.format(tables=table_list)},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
            max_tokens=80,
            response_format={"type": "json_object"},
        )
        import json
        payload = json.loads(resp.choices[0].message.content or "{}")
        route = payload.get("route", "rag")
        if route not in ("sql", "rag", "hybrid"):
            route = "rag"
        return {
            "route": route,
            "confidence": "llm",
            "reason": payload.get("reason", "LLM classification"),
        }
    except (OpenAIError, ValueError, KeyError) as exc:
        return {"route": "rag", "confidence": "fallback", "reason": f"LLM router error: {exc}"}


async def route_query(query: str) -> dict:
    """Cheap heuristic first; LLM only if heuristic confidence is 'low'."""
    h = heuristic_route(query)
    if h["confidence"] == "low":
        llm = await llm_route(query)
        return {**llm, "signals": h.get("signals", {}), "heuristic_reason": h["reason"]}
    return h
