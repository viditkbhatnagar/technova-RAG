"""LLM-generated business glossary for the structured schema.

At ingest, for each column we ask the LLM: 'in plain business English, what
does this column represent and what user phrases map to it?' Cached to disk
so the cost is paid once per schema change, not per query.

The glossary is consumed by sql_engine.schema_prompt() (to enrich what the
LLM sees when planning SQL) AND by column_doc_builder (to make an embedding
document per column that shows up in semantic retrieval).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI, OpenAIError

from backend.config import PROJECT_ROOT, settings


GLOSSARY_PATH = PROJECT_ROOT / "backend" / "schema_glossary.json"


_COLUMN_SYSTEM = (
    "You write concise business-English definitions of database columns. "
    "For each column you get: table name, column name, type, sample values, "
    "and null rate. You return a JSON object with two fields: "
    '`description` (one short sentence, plain language) and `aliases` '
    "(a list of 3-6 natural phrases a business user might use for this "
    "concept). No other fields. No prose outside the JSON."
)


def _column_user_prompt(table: str, table_desc: str, col: dict) -> str:
    bits = [
        f"Table: {table}",
        f"Table purpose: {table_desc}",
        f"Column: {col['name']}  type: {col.get('sqlite_type')}",
    ]
    if col.get("top_values"):
        vals = ", ".join(
            f"{tv['value']!r}({tv['count']})" for tv in col["top_values"][:8]
        )
        bits.append(f"Top values: {vals}")
    elif col.get("sample_value") is not None:
        bits.append(f"Sample: {col['sample_value']!r}")
    if col.get("min") is not None and col.get("max") is not None:
        bits.append(f"Range: {col['min']} .. {col['max']} (mean {col.get('mean')})")
    if col.get("min_date") and col.get("max_date"):
        bits.append(f"Date range: {col['min_date']} .. {col['max_date']}")
    if col.get("null_rate") is not None and col["null_rate"] > 0:
        bits.append(f"null_rate: {int(col['null_rate']*100)}%")
    return "\n".join(bits) + '\n\nRespond with JSON: {"description": "...", "aliases": [...]}'


async def _describe_one(
    client: AsyncOpenAI, table: str, table_desc: str, col: dict
) -> dict:
    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _COLUMN_SYSTEM},
                {"role": "user", "content": _column_user_prompt(table, table_desc, col)},
            ],
            temperature=0.0,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        payload = json.loads(resp.choices[0].message.content or "{}")
        desc = str(payload.get("description", "")).strip()
        aliases = payload.get("aliases") or []
        if not isinstance(aliases, list):
            aliases = []
        return {"description": desc, "aliases": [str(a) for a in aliases][:6]}
    except (OpenAIError, json.JSONDecodeError, KeyError, ValueError):
        return {"description": "", "aliases": []}


async def build_glossary(registry: dict, concurrency: int = 8) -> dict:
    """Generate {table: {column: {description, aliases}}} for every column.

    Resumes from cache — only new/changed columns hit the LLM.
    """
    if not settings.openai_api_key:
        print("[glossary] no OPENAI_API_KEY — skipping glossary build")
        return _load_cached()

    cache = _load_cached()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    sem = asyncio.Semaphore(concurrency)

    tasks = []
    keys = []

    for t in registry.get("tables", []):
        tname = t["name"]
        tdesc = t.get("description", "")
        cache.setdefault(tname, {})
        for col in t.get("columns", []):
            cname = col["name"]
            if cache[tname].get(cname, {}).get("description"):
                continue  # already cached

            async def _bounded(table=tname, desc=tdesc, c=col):
                async with sem:
                    return await _describe_one(client, table, desc, c)

            tasks.append(asyncio.create_task(_bounded()))
            keys.append((tname, cname))

    if tasks:
        print(f"[glossary] generating {len(tasks)} column descriptions...")
        results = await asyncio.gather(*tasks)
        for (tname, cname), res in zip(keys, results):
            cache[tname][cname] = res
        GLOSSARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        GLOSSARY_PATH.write_text(json.dumps(cache, indent=2))
        print(f"[glossary] wrote {len(tasks)} new descriptions to {GLOSSARY_PATH.name}")
    else:
        print("[glossary] all columns already described (cache hit)")

    return cache


def _load_cached() -> dict:
    if not GLOSSARY_PATH.exists():
        return {}
    try:
        return json.loads(GLOSSARY_PATH.read_text())
    except Exception:
        return {}


def load_glossary() -> dict:
    return _load_cached()


def invalidate_glossary() -> None:
    """Call when table metadata changes to force full regeneration."""
    if GLOSSARY_PATH.exists():
        GLOSSARY_PATH.unlink()
