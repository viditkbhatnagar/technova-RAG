"""Ingest TechNova structured (Excel) corpus into SQLite + a schema registry.

Each Excel file becomes one SQLite table keyed by the canonical name in
`TABLE_METADATA`. A JSON schema registry is persisted alongside, carrying
column types, sample values, FK relationships and security metadata. The
registry is the LLM's ground-truth schema context for text-to-SQL.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from backend.config import (
    EXAMPLE_SQL_QUERIES,
    FOREIGN_KEYS,
    TABLE_METADATA,
    settings,
)


def _infer_sqlite_type(series: pd.Series) -> str:
    """Map a pandas dtype / content to a SQLite affinity."""
    dtype = series.dtype
    if pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    if pd.api.types.is_float_dtype(dtype):
        return "REAL"
    if pd.api.types.is_bool_dtype(dtype):
        return "INTEGER"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "TEXT"
    non_null = series.dropna().astype(str).head(50).tolist()
    if non_null and all(_looks_like_iso_date(v) for v in non_null):
        return "DATE"
    return "TEXT"


def _looks_like_iso_date(v: str) -> bool:
    if len(v) < 10 or v.count("-") < 2:
        return False
    head = v[:10]
    return head[:4].isdigit() and head[5:7].isdigit() and head[8:10].isdigit()


def _sample_value(series: pd.Series) -> Any:
    non_null = series.dropna()
    if non_null.empty:
        return None
    val = non_null.iloc[0]
    if hasattr(val, "item"):
        try:
            val = val.item()
        except Exception:
            pass
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val


def _distinct_preview(series: pd.Series, limit: int = 8) -> list[Any]:
    non_null = series.dropna()
    if non_null.empty:
        return []
    uniq = non_null.drop_duplicates().head(limit).tolist()
    cleaned: list[Any] = []
    for v in uniq:
        if hasattr(v, "item"):
            try:
                v = v.item()
            except Exception:
                pass
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        cleaned.append(v)
    return cleaned


class StructuredIngestionError(Exception):
    pass


def ingest_structured_corpus(
    docs_dir: Path | None = None,
    sqlite_path: Path | None = None,
    registry_path: Path | None = None,
) -> dict:
    """Load every xlsx in `docs_dir` mapped in TABLE_METADATA into SQLite.

    Returns a summary dict `{tables: [...], schema_registry_path, sqlite_path}`.
    """
    docs_dir = docs_dir or settings.structured_docs_dir
    sqlite_path = sqlite_path or settings.sqlite_db_file
    registry_path = registry_path or settings.sql_schema_registry_file

    if not docs_dir.exists():
        raise StructuredIngestionError(f"Structured docs dir not found: {docs_dir}")

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    if sqlite_path.exists():
        sqlite_path.unlink()

    conn = sqlite3.connect(sqlite_path)
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        tables_out: list[dict] = []

        for table_name, meta in TABLE_METADATA.items():
            xlsx = docs_dir / meta["source_file"]
            if not xlsx.exists():
                print(f"[structured_ingest] missing file, skipping: {xlsx.name}")
                continue

            try:
                df = pd.read_excel(xlsx, sheet_name=meta["sheet"])
            except Exception as exc:
                print(f"[structured_ingest] failed {xlsx.name}: {exc}")
                continue

            df = df.dropna(how="all")
            df.columns = [str(c).strip() for c in df.columns]

            for col in df.columns:
                if pd.api.types.is_object_dtype(df[col]):
                    df[col] = df[col].where(df[col].notna(), None)

            df.to_sql(table_name, conn, if_exists="replace", index=False)

            columns_info: list[dict] = []
            for col in df.columns:
                sqlite_type = _infer_sqlite_type(df[col])
                distinct_count = int(df[col].dropna().nunique())
                columns_info.append(
                    {
                        "name": col,
                        "sqlite_type": sqlite_type,
                        "pandas_dtype": str(df[col].dtype),
                        "sample_value": _sample_value(df[col]),
                        "distinct_count": distinct_count,
                        "distinct_preview": _distinct_preview(df[col], limit=12),
                        "null_count": int(df[col].isna().sum()),
                    }
                )

            fks = [fk for fk in FOREIGN_KEYS if fk["table"] == table_name]

            tables_out.append(
                {
                    "name": table_name,
                    "source_file": meta["source_file"],
                    "description": meta["description"],
                    "domain": meta["domain"],
                    "primary_key": meta["primary_key"],
                    "security_level": meta["security_level"],
                    "security_label": meta["security_label"],
                    "row_count": int(len(df)),
                    "columns": columns_info,
                    "foreign_keys": fks,
                }
            )
            print(
                f"[structured_ingest] {table_name}: "
                f"{len(df)} rows, {len(df.columns)} cols "
                f"({meta['security_label']})"
            )

        conn.commit()
    finally:
        conn.close()

    registry = {
        "sqlite_path": str(sqlite_path),
        "tables": tables_out,
        "example_queries": EXAMPLE_SQL_QUERIES,
    }
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2, default=str))

    return {
        "sqlite_path": str(sqlite_path),
        "schema_registry_path": str(registry_path),
        "tables": [
            {"name": t["name"], "rows": t["row_count"], "security": t["security_label"]}
            for t in tables_out
        ],
    }


def load_schema_registry(path: Path | None = None) -> dict | None:
    path = path or settings.sql_schema_registry_file
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        print(f"[structured_ingest] failed to load registry: {exc}")
        return None
