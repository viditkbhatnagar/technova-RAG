"""LLM-extracted policy digest from the PDF corpus.

For every PDF in DOCUMENT_METADATA, at ingest we ask gpt-4o-mini to extract
the rules, thresholds, rates, dates, and named facts an analyst would
reference. The result is a structured JSON cached to disk and injected into
the agent's system prompt, so the agent no longer has to retrieve these
common numbers repeatedly.

This is *not* per-question hardcoding — it's a data distillation of the
PDFs themselves. Add a new PDF tomorrow, re-run ingest, digest rebuilds.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from openai import AsyncOpenAI, OpenAIError

from backend.config import DOCUMENT_METADATA, PROJECT_ROOT, settings
from backend.services.loader import load_pdf


DIGEST_PATH = PROJECT_ROOT / "backend" / "policy_digest.json"


_EXTRACTION_SYSTEM = (
    "You extract structured policy knowledge from a corporate document. "
    "You return ONLY JSON with these four arrays (each element short, factual, no fluff):\n"
    " - `rules`: enforceable rules with a threshold, rate, or percentage. "
    "Format: {\"rule\": str, \"value\": str (include unit), \"section\": str (if known)}\n"
    " - `timelines`: time-bound events, deadlines, milestones. "
    "Format: {\"event\": str, \"date_or_window\": str}\n"
    " - `key_facts`: named amounts, policies, coverage limits, budgets, or quantitative facts. "
    "Format: {\"fact\": str, \"value\": str (include unit)}\n"
    " - `definitions`: concept definitions an analyst might reference. "
    "Format: {\"term\": str, \"meaning\": str}\n"
    "Skip fluff, backstory, narrative. Keep each string under 150 characters. "
    "If a category has nothing, return an empty list."
)


def _user_prompt(doc_name: str, doc_text: str) -> str:
    trimmed = doc_text[:15000]  # ~4k tokens; fits context easily
    return f"DOCUMENT: {doc_name}\n\n{trimmed}\n\nReturn JSON only."


async def _extract_one(
    client: AsyncOpenAI, file_name: str, doc_name: str, pdf_path: Path
) -> dict:
    try:
        pages = load_pdf(pdf_path)
    except Exception as exc:
        return {"error": f"load failed: {exc}"}
    full_text = "\n\n".join(p["text"] for p in pages)
    if not full_text.strip():
        return {"rules": [], "timelines": [], "key_facts": [], "definitions": []}
    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM},
                {"role": "user", "content": _user_prompt(doc_name, full_text)},
            ],
            temperature=0.0,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
        payload = json.loads(resp.choices[0].message.content or "{}")
        return {
            "rules": payload.get("rules") or [],
            "timelines": payload.get("timelines") or [],
            "key_facts": payload.get("key_facts") or [],
            "definitions": payload.get("definitions") or [],
        }
    except (OpenAIError, json.JSONDecodeError) as exc:
        return {"error": str(exc)}


async def build_policy_digest(
    docs_dir: Path | None = None, concurrency: int = 4
) -> dict:
    """Run extraction over every PDF in DOCUMENT_METADATA. Cached — only
    PDFs without a cache entry hit the LLM."""
    docs_dir = docs_dir or settings.docs_dir
    if not settings.openai_api_key:
        print("[policy_digest] no OPENAI_API_KEY — skipping")
        return _load_cached()

    cached = _load_cached()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    sem = asyncio.Semaphore(concurrency)

    tasks = []
    file_names = []
    for file_name, meta in DOCUMENT_METADATA.items():
        if cached.get(file_name, {}).get("rules") is not None and not cached[file_name].get("error"):
            continue
        pdf_path = docs_dir / file_name
        if not pdf_path.exists():
            continue

        async def _bounded(fn=file_name, m=meta, p=pdf_path):
            async with sem:
                return await _extract_one(client, fn, m["doc_name"], p)

        tasks.append(asyncio.create_task(_bounded()))
        file_names.append(file_name)

    if tasks:
        print(f"[policy_digest] extracting from {len(tasks)} PDFs...")
        results = await asyncio.gather(*tasks)
        for fn, res in zip(file_names, results):
            cached[fn] = res
        DIGEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        DIGEST_PATH.write_text(json.dumps(cached, indent=2))
        print(f"[policy_digest] wrote {len(tasks)} digests to {DIGEST_PATH.name}")
    else:
        print("[policy_digest] cache hit for all PDFs")

    return cached


def _load_cached() -> dict:
    if not DIGEST_PATH.exists():
        return {}
    try:
        return json.loads(DIGEST_PATH.read_text())
    except Exception:
        return {}


def load_policy_digest() -> dict:
    return _load_cached()


def invalidate_policy_digest() -> None:
    if DIGEST_PATH.exists():
        DIGEST_PATH.unlink()


def format_digest_for_prompt(digest: dict, max_chars: int = 4000) -> str:
    """Render the digest as a compact markdown block to inject into the
    agent's system prompt. Trims to max_chars to keep prompts manageable."""
    if not digest:
        return ""

    lines: list[str] = ["POLICY DIGEST (pre-extracted from company PDFs):"]
    for file_name, payload in digest.items():
        if payload.get("error"):
            continue
        meta = DOCUMENT_METADATA.get(file_name)
        doc_name = meta["doc_name"] if meta else file_name
        bits: list[str] = []
        for r in (payload.get("rules") or [])[:8]:
            bits.append(f"  RULE: {r.get('rule','')} = {r.get('value','')}"
                        + (f" [{r['section']}]" if r.get("section") else ""))
        for t in (payload.get("timelines") or [])[:5]:
            bits.append(f"  TIMELINE: {t.get('event','')} — {t.get('date_or_window','')}")
        for kf in (payload.get("key_facts") or [])[:8]:
            bits.append(f"  FACT: {kf.get('fact','')} = {kf.get('value','')}")
        for d in (payload.get("definitions") or [])[:4]:
            bits.append(f"  DEF: {d.get('term','')} — {d.get('meaning','')}")
        if bits:
            lines.append(f"\n[{doc_name}]")
            lines.extend(bits)

    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n  ...<truncated>"
    return text
