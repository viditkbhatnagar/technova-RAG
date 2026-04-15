"""Documents router — browse the corpus mirrored in Postgres."""

from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query, Request

from backend.config import DOCUMENT_METADATA
from backend.models import (
    ChunkPage,
    ChunkRecord,
    DocumentDetail,
    DocumentSummary,
    SyncResponse,
)
from backend.services.db import chat_store

router = APIRouter()


def _db_required() -> None:
    if not chat_store.enabled:
        raise HTTPException(
            status_code=503,
            detail="Postgres not configured. Set DATABASE_URL in backend/.env.",
        )


@router.get("/api/documents", response_model=list[DocumentSummary])
async def list_documents() -> list[DocumentSummary]:
    _db_required()
    rows = await chat_store.list_documents()
    return [DocumentSummary(**r) for r in rows]


@router.get("/api/documents/{slug}", response_model=DocumentDetail)
async def get_document(slug: str) -> DocumentDetail:
    _db_required()
    doc = await chat_store.get_document(slug)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document '{slug}' not found.")
    sample = await chat_store.list_chunks(slug, limit=5, offset=0)
    return DocumentDetail(
        **doc,
        sample_chunks=[ChunkRecord(**c) for c in sample],
    )


@router.get("/api/documents/{slug}/chunks", response_model=ChunkPage)
async def list_document_chunks(
    slug: str,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ChunkPage:
    _db_required()
    doc = await chat_store.get_document(slug)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document '{slug}' not found.")
    items = await chat_store.list_chunks(slug, limit=limit, offset=offset)
    total = await chat_store.count_chunks(slug)
    return ChunkPage(
        items=[ChunkRecord(**c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/api/documents/sync", response_model=SyncResponse)
async def sync_documents_to_db(request: Request) -> SyncResponse:
    """Backfill Postgres from existing Qdrant chunks. Idempotent.

    Avoids forcing a re-ingest when the user just wired up DATABASE_URL.
    Reads every chunk payload from Qdrant and upserts into Postgres.
    """
    _db_required()

    store = request.app.state.store
    if store is None or not store.collection_exists():
        raise HTTPException(
            status_code=404,
            detail="No Qdrant collection found. Run /api/ingest first.",
        )

    payloads = store.scroll_all()
    if not payloads:
        return SyncResponse(
            status="empty",
            documents_written=0,
            chunks_written=0,
            message="No chunks found in Qdrant.",
        )

    by_doc: dict[str, list[dict]] = defaultdict(list)
    for p in payloads:
        slug = p.get("doc_slug")
        if slug:
            by_doc[slug].append(p)

    doc_rows: list[dict] = []
    chunk_rows: list[dict] = []
    for slug, chunks in by_doc.items():
        first = chunks[0]
        file_name = first.get("file_name", "")
        meta = DOCUMENT_METADATA.get(file_name, {})
        doc_rows.append({
            "doc_slug": slug,
            "doc_name": first.get("doc_name") or meta.get("doc_name", slug),
            "file_name": file_name,
            "domain": first.get("domain") or meta.get("domain", ""),
            "security_level": int(first.get("security_level", 0) or 0),
            "security_label": first.get("security_label") or meta.get("security_label", "PUBLIC"),
            "page_count": max((int(c.get("page_number", 0) or 0) for c in chunks), default=0),
            "chunk_count": len(chunks),
            "char_count": sum(int(c.get("char_count", 0) or 0) for c in chunks),
        })
        chunk_rows.extend(chunks)

    await chat_store.upsert_documents(doc_rows)
    written = await chat_store.upsert_chunks(
        chunk_rows,
        replace_doc_slugs=list(by_doc.keys()),
    )
    return SyncResponse(
        status="ok",
        documents_written=len(doc_rows),
        chunks_written=written,
    )
