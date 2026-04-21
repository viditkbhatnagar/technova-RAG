"""Emit embeddable 'schema documents' — one per column and one per low-cardinality
value — so that semantic retrieval returns relevant structured-schema context
alongside PDF chunks.

A user asking 'laptop spend' will semantic-match the column doc for
`assets_licenses.annual_cost` (because that doc carries the business description
and aliases) and the value doc for `assets_licenses.asset_type = 'Laptop'`.
The SQL engine's plan step sees these in the retrieved context and picks the
right table/column without any hardcoded hints.

Docs share the same payload schema as PDF chunks, just with source_type set to
`schema_column` or `schema_value`. They inherit the table's security_level so
role filtering works unchanged.
"""

from __future__ import annotations

import hashlib

from backend.config import ORG_ID, TABLE_METADATA


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_schema_docs(registry: dict, glossary: dict) -> list[dict]:
    """Produce chunk-dicts for every column and every low-cardinality value.

    Returns chunks compatible with store.upsert_chunks / bm25.build.
    """
    chunks: list[dict] = []
    table_desc_by_name = {t["name"]: t for t in registry.get("tables", [])}

    for t in registry.get("tables", []):
        tname = t["name"]
        meta = TABLE_METADATA.get(tname)
        if meta is None:
            continue

        for idx, col in enumerate(t.get("columns", [])):
            cname = col["name"]
            gl = (glossary.get(tname) or {}).get(cname, {})
            description = gl.get("description") or ""
            aliases = gl.get("aliases") or []

            # --- column-level document ---
            text = _render_column_doc(tname, t, col, description, aliases)
            chunk_id = f"{ORG_ID}_schema_col_{tname}_{cname}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "text": text,
                    "doc_name": f"Schema: {tname}",
                    "doc_slug": f"schema_{tname}",
                    "file_name": meta["source_file"],
                    "org_id": ORG_ID,
                    "domain": meta["domain"],
                    "security_level": meta["security_level"],
                    "security_label": meta["security_label"],
                    "page_number": 0,
                    "chunk_index": idx,
                    "total_chunks": len(t.get("columns", [])),
                    "char_count": len(text),
                    "content_hash": _hash(text),
                    "source_type": "schema_column",
                    "table": tname,
                    "row_id": cname,
                }
            )

            # --- value-level documents (only for low-cardinality TEXT) ---
            distinct_count = col.get("distinct_count") or 0
            if (
                col.get("sqlite_type") == "TEXT"
                and 0 < distinct_count <= 12
                and col.get("top_values")
            ):
                for v_idx, tv in enumerate(col["top_values"][:distinct_count]):
                    val = tv["value"]
                    cnt = tv["count"]
                    vtext = _render_value_doc(
                        tname, cname, val, cnt, description, aliases
                    )
                    vid = f"{ORG_ID}_schema_val_{tname}_{cname}_{_slug(str(val))}"
                    chunks.append(
                        {
                            "chunk_id": vid,
                            "text": vtext,
                            "doc_name": f"Schema values: {tname}.{cname}",
                            "doc_slug": f"schema_{tname}",
                            "file_name": meta["source_file"],
                            "org_id": ORG_ID,
                            "domain": meta["domain"],
                            "security_level": meta["security_level"],
                            "security_label": meta["security_label"],
                            "page_number": 0,
                            "chunk_index": v_idx,
                            "total_chunks": distinct_count,
                            "char_count": len(vtext),
                            "content_hash": _hash(vtext),
                            "source_type": "schema_value",
                            "table": tname,
                            "row_id": f"{cname}={val}",
                        }
                    )
    return chunks


def _render_column_doc(
    table: str, t: dict, col: dict, description: str, aliases: list[str]
) -> str:
    parts = [f"COLUMN {table}.{col['name']} ({col.get('sqlite_type', 'TEXT')})"]
    if description:
        parts.append(description)
    if aliases:
        parts.append("Business phrases: " + ", ".join(aliases))

    # data shape
    tv = col.get("top_values") or []
    if tv:
        vals = ", ".join(f"{x['value']!r} ({x['count']})" for x in tv[:6])
        parts.append(f"Top values: {vals}")
    if col.get("min") is not None and col.get("max") is not None:
        parts.append(
            f"Range: {col['min']} to {col['max']}, mean {col.get('mean')}"
        )
    if col.get("null_rate", 0) > 0:
        parts.append(f"Null rate: {int(col['null_rate']*100)}%")
    parts.append(f"Table purpose: {t.get('description', '')}")
    return ". ".join(parts) + "."


def _render_value_doc(
    table: str, column: str, value, count: int,
    column_description: str, aliases: list[str],
) -> str:
    parts = [
        f"VALUE {table}.{column} = {value!r}",
        f"Occurs {count} time(s) in {table}",
    ]
    if column_description:
        parts.append(column_description)
    if aliases:
        parts.append("Business phrases: " + ", ".join(aliases))
    return ". ".join(parts) + "."


def _slug(v: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in v)[:40]
