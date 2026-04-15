"""Async Postgres (Neon) chat-history persistence.

The DB is *off the hot path*: writes are scheduled via asyncio.create_task
so query latency is unchanged. Failures are logged and swallowed — chat
keeps working even if Neon is down.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import asyncpg


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id           UUID PRIMARY KEY,
    mode         TEXT NOT NULL,
    role         TEXT,
    title        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id                     UUID PRIMARY KEY,
    session_id             UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role                   TEXT NOT NULL,
    content                TEXT NOT NULL,
    sources                JSONB,
    retrieval_stats        JSONB,
    access_denied          BOOLEAN NOT NULL DEFAULT FALSE,
    access_denied_message  TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session_created
    ON messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_mode_updated
    ON sessions(mode, updated_at DESC);

CREATE TABLE IF NOT EXISTS documents (
    doc_slug       TEXT PRIMARY KEY,
    doc_name       TEXT NOT NULL,
    file_name      TEXT NOT NULL,
    domain         TEXT NOT NULL,
    security_level INT  NOT NULL,
    security_label TEXT NOT NULL,
    page_count     INT  NOT NULL DEFAULT 0,
    chunk_count    INT  NOT NULL DEFAULT 0,
    char_count     INT  NOT NULL DEFAULT 0,
    ingested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id       TEXT PRIMARY KEY,
    doc_slug       TEXT NOT NULL REFERENCES documents(doc_slug) ON DELETE CASCADE,
    text           TEXT NOT NULL,
    page_number    INT  NOT NULL,
    chunk_index    INT  NOT NULL,
    char_count     INT  NOT NULL,
    content_hash   TEXT NOT NULL,
    security_level INT  NOT NULL,
    security_label TEXT NOT NULL,
    domain         TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_slug ON chunks(doc_slug);
CREATE INDEX IF NOT EXISTS idx_chunks_security ON chunks(security_level);

CREATE TABLE IF NOT EXISTS query_runs (
    id                UUID PRIMARY KEY,
    query             TEXT NOT NULL,
    mode              TEXT NOT NULL,
    role              TEXT,
    top_k             INT  NOT NULL,
    dense_count       INT  NOT NULL DEFAULT 0,
    bm25_count        INT  NOT NULL DEFAULT 0,
    overlap_count     INT  NOT NULL DEFAULT 0,
    rrf_merged        INT  NOT NULL DEFAULT 0,
    reranked_final    INT  NOT NULL DEFAULT 0,
    avg_rerank_score  DOUBLE PRECISION,
    retrieval_time_ms INT,
    llm_used          BOOLEAN NOT NULL DEFAULT FALSE,
    access_denied     BOOLEAN NOT NULL DEFAULT FALSE,
    top_chunks        JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_query_runs_created ON query_runs(created_at DESC);
"""


def _normalize_dsn(url: str) -> str:
    """asyncpg doesn't accept all libpq URL params; strip the unsupported ones."""
    parsed = urlparse(url)
    if not parsed.query:
        return url
    params = parse_qs(parsed.query, keep_blank_values=True)
    params.pop("channel_binding", None)
    new_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse(parsed._replace(query=new_query))


class ChatStore:
    """Wraps an asyncpg pool and exposes session/message operations."""

    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled and self.pool is not None

    async def init(self, database_url: str) -> None:
        if not database_url:
            print("[db] DATABASE_URL not set — chat history disabled")
            return
        try:
            dsn = _normalize_dsn(database_url)
            self.pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=1,
                max_size=4,
                command_timeout=10,
            )
            async with self.pool.acquire() as conn:
                await conn.execute(_SCHEMA_SQL)
            self._enabled = True
            print("[db] connected to Postgres; schema ensured")
        except Exception as exc:
            print(f"[db] init failed — chat history disabled: {exc}")
            self.pool = None
            self._enabled = False

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
            self._enabled = False

    # ---------- writes ----------

    async def save_turn(
        self,
        *,
        session_id: uuid.UUID,
        mode: str,
        role: str | None,
        user_query: str,
        assistant_answer: str,
        sources: list[dict[str, Any]],
        retrieval_stats: dict[str, Any],
        access_denied: bool,
        access_denied_message: str | None,
        scheduled_at: datetime | None = None,
    ) -> None:
        if not self.enabled or self.pool is None:
            return
        try:
            title = user_query.strip()[:80] or "(empty query)"
            base = scheduled_at or datetime.now(timezone.utc)
            user_ts = base
            assistant_ts = datetime.fromtimestamp(
                base.timestamp() + 0.001, tz=timezone.utc
            )
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # First turn sets the title; later turns only bump updated_at.
                    await conn.execute(
                        """
                        INSERT INTO sessions (id, mode, role, title, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $5)
                        ON CONFLICT (id) DO UPDATE
                          SET updated_at = GREATEST(sessions.updated_at, EXCLUDED.updated_at),
                              role = COALESCE(EXCLUDED.role, sessions.role),
                              title = COALESCE(sessions.title, EXCLUDED.title)
                        """,
                        session_id,
                        mode,
                        role,
                        title,
                        assistant_ts,
                    )
                    await conn.execute(
                        """
                        INSERT INTO messages (id, session_id, role, content, created_at)
                        VALUES ($1, $2, 'user', $3, $4)
                        """,
                        uuid.uuid4(),
                        session_id,
                        user_query,
                        user_ts,
                    )
                    await conn.execute(
                        """
                        INSERT INTO messages (
                            id, session_id, role, content,
                            sources, retrieval_stats,
                            access_denied, access_denied_message, created_at
                        )
                        VALUES ($1, $2, 'assistant', $3, $4::jsonb, $5::jsonb, $6, $7, $8)
                        """,
                        uuid.uuid4(),
                        session_id,
                        assistant_answer,
                        json.dumps(sources),
                        json.dumps(retrieval_stats),
                        access_denied,
                        access_denied_message,
                        assistant_ts,
                    )
        except Exception as exc:
            print(f"[db] save_turn failed (swallowed): {exc}")

    def schedule_save(self, **kwargs: Any) -> None:
        """Fire-and-forget save. Pins the request timestamp NOW so ordering
        is preserved even if background tasks finish out of order."""
        if not self.enabled:
            return
        kwargs["scheduled_at"] = datetime.now(timezone.utc)
        try:
            asyncio.create_task(self.save_turn(**kwargs))
        except RuntimeError:
            pass

    # ---------- reads ----------

    async def list_sessions(self, mode: str | None = None, limit: int = 50) -> list[dict]:
        if not self.enabled or self.pool is None:
            return []
        async with self.pool.acquire() as conn:
            if mode:
                rows = await conn.fetch(
                    """
                    SELECT s.id, s.mode, s.role, s.title, s.created_at, s.updated_at,
                           (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id)
                             AS message_count
                    FROM sessions s
                    WHERE s.mode = $1
                    ORDER BY s.updated_at DESC
                    LIMIT $2
                    """,
                    mode,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT s.id, s.mode, s.role, s.title, s.created_at, s.updated_at,
                           (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id)
                             AS message_count
                    FROM sessions s
                    ORDER BY s.updated_at DESC
                    LIMIT $1
                    """,
                    limit,
                )
        return [dict(r) for r in rows]

    async def get_session(self, session_id: uuid.UUID) -> dict | None:
        if not self.enabled or self.pool is None:
            return None
        async with self.pool.acquire() as conn:
            session = await conn.fetchrow(
                "SELECT id, mode, role, title, created_at, updated_at FROM sessions WHERE id = $1",
                session_id,
            )
            if not session:
                return None
            messages = await conn.fetch(
                """
                SELECT id, role, content, sources, retrieval_stats,
                       access_denied, access_denied_message, created_at
                FROM messages
                WHERE session_id = $1
                ORDER BY created_at ASC
                """,
                session_id,
            )
        return {
            **dict(session),
            "messages": [
                {
                    **dict(m),
                    "sources": json.loads(m["sources"]) if m["sources"] else [],
                    "retrieval_stats": json.loads(m["retrieval_stats"]) if m["retrieval_stats"] else {},
                }
                for m in messages
            ],
        }

    async def delete_session(self, session_id: uuid.UUID) -> bool:
        if not self.enabled or self.pool is None:
            return False
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM sessions WHERE id = $1", session_id)
        return result.endswith(" 1")

    # ---------- corpus: documents + chunks ----------

    async def upsert_documents(self, rows: list[dict]) -> None:
        if not self.enabled or self.pool is None or not rows:
            return
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    for r in rows:
                        await conn.execute(
                            """
                            INSERT INTO documents (
                                doc_slug, doc_name, file_name, domain,
                                security_level, security_label,
                                page_count, chunk_count, char_count, ingested_at
                            )
                            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9, NOW())
                            ON CONFLICT (doc_slug) DO UPDATE SET
                                doc_name       = EXCLUDED.doc_name,
                                file_name      = EXCLUDED.file_name,
                                domain         = EXCLUDED.domain,
                                security_level = EXCLUDED.security_level,
                                security_label = EXCLUDED.security_label,
                                page_count     = EXCLUDED.page_count,
                                chunk_count    = EXCLUDED.chunk_count,
                                char_count     = EXCLUDED.char_count,
                                ingested_at    = NOW()
                            """,
                            r["doc_slug"],
                            r["doc_name"],
                            r["file_name"],
                            r["domain"],
                            int(r["security_level"]),
                            r["security_label"],
                            int(r.get("page_count", 0)),
                            int(r.get("chunk_count", 0)),
                            int(r.get("char_count", 0)),
                        )
        except Exception as exc:
            print(f"[db] upsert_documents failed (swallowed): {exc}")

    async def upsert_chunks(
        self,
        rows: list[dict],
        replace_doc_slugs: list[str] | None = None,
    ) -> int:
        if not self.enabled or self.pool is None or not rows:
            return 0
        written = 0
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    if replace_doc_slugs:
                        await conn.execute(
                            "DELETE FROM chunks WHERE doc_slug = ANY($1::text[])",
                            replace_doc_slugs,
                        )
                    for r in rows:
                        await conn.execute(
                            """
                            INSERT INTO chunks (
                                chunk_id, doc_slug, text, page_number, chunk_index,
                                char_count, content_hash,
                                security_level, security_label, domain
                            )
                            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                            ON CONFLICT (chunk_id) DO UPDATE SET
                                doc_slug       = EXCLUDED.doc_slug,
                                text           = EXCLUDED.text,
                                page_number    = EXCLUDED.page_number,
                                chunk_index    = EXCLUDED.chunk_index,
                                char_count     = EXCLUDED.char_count,
                                content_hash   = EXCLUDED.content_hash,
                                security_level = EXCLUDED.security_level,
                                security_label = EXCLUDED.security_label,
                                domain         = EXCLUDED.domain
                            """,
                            r["chunk_id"],
                            r["doc_slug"],
                            r["text"],
                            int(r.get("page_number", 0) or 0),
                            int(r.get("chunk_index", 0) or 0),
                            int(r.get("char_count", len(r.get("text", "")))),
                            r.get("content_hash", ""),
                            int(r.get("security_level", 0) or 0),
                            r.get("security_label", "PUBLIC"),
                            r.get("domain", ""),
                        )
                        written += 1
        except Exception as exc:
            print(f"[db] upsert_chunks failed (swallowed): {exc}")
        return written

    async def list_documents(self) -> list[dict]:
        if not self.enabled or self.pool is None:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT doc_slug, doc_name, file_name, domain,
                       security_level, security_label,
                       page_count, chunk_count, char_count, ingested_at
                FROM documents
                ORDER BY security_level ASC, doc_name ASC
                """
            )
        return [dict(r) for r in rows]

    async def get_document(self, slug: str) -> dict | None:
        if not self.enabled or self.pool is None:
            return None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT doc_slug, doc_name, file_name, domain,
                       security_level, security_label,
                       page_count, chunk_count, char_count, ingested_at
                FROM documents WHERE doc_slug = $1
                """,
                slug,
            )
        return dict(row) if row else None

    async def list_chunks(
        self,
        slug: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        if not self.enabled or self.pool is None:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT chunk_id, doc_slug, text, page_number, chunk_index,
                       char_count, content_hash,
                       security_level, security_label, domain, created_at
                FROM chunks
                WHERE doc_slug = $1
                ORDER BY chunk_index ASC
                LIMIT $2 OFFSET $3
                """,
                slug,
                limit,
                offset,
            )
        return [dict(r) for r in rows]

    async def count_chunks(self, slug: str) -> int:
        if not self.enabled or self.pool is None:
            return 0
        async with self.pool.acquire() as conn:
            n = await conn.fetchval(
                "SELECT COUNT(*) FROM chunks WHERE doc_slug = $1", slug
            )
        return int(n or 0)

    async def total_chunk_count(self) -> int:
        if not self.enabled or self.pool is None:
            return 0
        async with self.pool.acquire() as conn:
            n = await conn.fetchval("SELECT COUNT(*) FROM chunks")
        return int(n or 0)

    # ---------- query log ----------

    async def save_query_run(
        self,
        *,
        query: str,
        mode: str,
        role: str | None,
        top_k: int,
        stats: dict[str, Any],
        top_chunks: list[dict[str, Any]],
        llm_used: bool,
        access_denied: bool,
    ) -> None:
        if not self.enabled or self.pool is None:
            return
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO query_runs (
                        id, query, mode, role, top_k,
                        dense_count, bm25_count, overlap_count,
                        rrf_merged, reranked_final, avg_rerank_score,
                        retrieval_time_ms, llm_used, access_denied, top_chunks
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15::jsonb)
                    """,
                    uuid.uuid4(),
                    query,
                    mode,
                    role,
                    int(top_k),
                    int(stats.get("dense_results", 0) or 0),
                    int(stats.get("bm25_results", 0) or 0),
                    int(stats.get("overlap_count", 0) or 0),
                    int(stats.get("rrf_merged", 0) or 0),
                    int(stats.get("reranked_final", 0) or 0),
                    float(stats.get("avg_rerank_score", 0.0) or 0.0),
                    int(stats.get("retrieval_time_ms", 0) or 0),
                    bool(llm_used),
                    bool(access_denied),
                    json.dumps(top_chunks),
                )
        except Exception as exc:
            print(f"[db] save_query_run failed (swallowed): {exc}")

    def schedule_query_run(self, **kwargs: Any) -> None:
        if not self.enabled:
            return
        try:
            asyncio.create_task(self.save_query_run(**kwargs))
        except RuntimeError:
            pass


chat_store = ChatStore()
