"""Build row-level 'chunks' from narrative tables for the RAG index.

Each row becomes a templated document that flows through the existing
embedder + Qdrant + BM25 pipeline with the normal security payload — so a
question like "what happened in the Eastern Europe data exfiltration?" can
reach the incidents row even though it lives in SQLite, not a PDF.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from backend.config import (
    NARRATIVE_ROW_TABLES,
    ORG_ID,
    TABLE_METADATA,
    settings,
)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fmt(v: object) -> str:
    if v is None:
        return "unknown"
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


def _render_row(table: str, row: dict, columns: list[str]) -> str:
    """Render a row as a compact natural-language document."""
    parts = []
    ref_cols = ("incident_ref", "vendor_code", "asset_tag", "customer_name")
    header_val = None
    for c in ref_cols:
        if c in row and row[c] not in (None, ""):
            header_val = row[c]
            break
    if header_val:
        parts.append(f"{table.upper()} {header_val}")

    for col in columns:
        if col not in row:
            continue
        val = row[col]
        if val is None or val == "":
            continue
        parts.append(f"{col.replace('_', ' ')}: {_fmt(val)}")

    return ". ".join(parts) + "."


def build_row_chunks(sqlite_path: Path | None = None) -> list[dict]:
    """Produce chunk-dicts for every row of every NARRATIVE_ROW_TABLES table.

    Each dict mirrors the PDF chunk schema plus `source_type='structured_row'`,
    `table=<name>`, `row_id=<pk value>`. Safe to pass straight to
    `store.upsert_chunks` and `bm25.build`.
    """
    sqlite_path = Path(sqlite_path or settings.sqlite_db_file)
    if not sqlite_path.exists():
        return []

    chunks: list[dict] = []
    conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    try:
        conn.row_factory = sqlite3.Row
        for table, spec in NARRATIVE_ROW_TABLES.items():
            table_meta = TABLE_METADATA.get(table)
            if table_meta is None:
                continue
            try:
                cur = conn.execute(f"SELECT * FROM {table}")
                rows = [dict(r) for r in cur.fetchall()]
            except sqlite3.Error as exc:
                print(f"[structured_rows] skip {table}: {exc}")
                continue

            for idx, row in enumerate(rows):
                pk_value = row.get(spec["id_column"])
                text = _render_row(table, row, spec["template_columns"])
                chunk_id = f"{ORG_ID}_{spec['doc_slug']}_r{pk_value}"
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "text": text,
                        "doc_name": spec["doc_name"],
                        "doc_slug": spec["doc_slug"],
                        "file_name": table_meta["source_file"],
                        "org_id": ORG_ID,
                        "domain": table_meta["domain"],
                        "security_level": table_meta["security_level"],
                        "security_label": table_meta["security_label"],
                        "page_number": 0,
                        "chunk_index": idx,
                        "total_chunks": len(rows),
                        "char_count": len(text),
                        "content_hash": _hash(text),
                        "source_type": "structured_row",
                        "table": table,
                        "row_id": pk_value,
                    }
                )
            print(
                f"[structured_rows] {table}: {len(rows)} row-docs "
                f"({table_meta['security_label']})"
            )
    finally:
        conn.close()

    return chunks
