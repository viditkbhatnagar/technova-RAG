"""POST /api/ingest — load all PDFs, chunk, embed, store, build BM25."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from backend.config import DOCUMENT_METADATA, settings
from backend.models import (
    IngestDocDetail,
    IngestRequest,
    IngestResponse,
    StructuredIngestSummary,
    StructuredTableSummary,
)
from backend.services.chunker import chunk_document
from backend.services.db import chat_store
from backend.services.graph_builder import GraphBuilder
from backend.services.loader import IngestionError, list_pdfs, load_pdf
from backend.services.policy_digest import build_policy_digest
from backend.services.schema_docs import build_schema_docs
from backend.services.schema_glossary import build_glossary, load_glossary
from backend.services.structured_ingest import (
    StructuredIngestionError,
    ingest_structured_corpus,
    load_schema_registry,
)
from backend.services.structured_rows import build_row_chunks

router = APIRouter()


@router.post("/api/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest, request: Request) -> IngestResponse:
    embedder = request.app.state.embedder
    store = request.app.state.store
    bm25 = request.app.state.bm25

    docs_path = Path(req.docs_path) if req.docs_path else settings.docs_dir
    if not docs_path.is_absolute():
        from backend.config import PROJECT_ROOT
        docs_path = PROJECT_ROOT / docs_path

    try:
        pdf_files = list_pdfs(docs_path)
    except IngestionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not pdf_files:
        raise HTTPException(
            status_code=404,
            detail=f"No PDFs found in {docs_path}",
        )

    if req.force_reingest:
        store.delete_collection()
    store.create_collection()

    all_chunks: list[dict] = []
    details: list[IngestDocDetail] = []
    skipped: list[str] = []
    doc_rows: list[dict] = []

    for pdf_path in pdf_files:
        file_name = pdf_path.name
        if file_name not in DOCUMENT_METADATA:
            skipped.append(file_name)
            print(f"[ingest] skipping unmapped file: {file_name}")
            continue

        try:
            pages = load_pdf(pdf_path)
        except IngestionError as exc:
            print(f"[ingest] failed to load {file_name}: {exc}")
            continue

        if not pages:
            print(f"[ingest] no extractable text in {file_name}")
            continue

        chunks = chunk_document(
            pages=pages,
            file_name=file_name,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        if not chunks:
            continue

        texts = [c["text"] for c in chunks]
        embeddings = embedder.embed_texts(texts)
        store.upsert_chunks(chunks, embeddings)
        all_chunks.extend(chunks)

        details.append(
            IngestDocDetail(
                file_name=file_name,
                pages=len(pages),
                chunks=len(chunks),
                security_level=DOCUMENT_METADATA[file_name]["security_label"],
            )
        )
        meta = DOCUMENT_METADATA[file_name]
        doc_rows.append({
            "doc_slug": meta["doc_slug"],
            "doc_name": meta["doc_name"],
            "file_name": file_name,
            "domain": meta["domain"],
            "security_level": meta["security_level"],
            "security_label": meta["security_label"],
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "char_count": sum(c.get("char_count", 0) for c in chunks),
        })
        print(
            f"[ingest] {file_name}: {len(pages)} pages → {len(chunks)} chunks"
        )

    if not all_chunks:
        raise HTTPException(
            status_code=500,
            detail="No chunks were produced from any document.",
        )

    try:
        row_chunks = build_row_chunks()
    except Exception as exc:
        print(f"[ingest] warning: row-level embedding build failed: {exc}")
        row_chunks = []

    schema_chunks: list[dict] = []
    try:
        registry = load_schema_registry() or {"tables": []}
        print("[ingest] building business glossary (LLM per column, cached)...")
        glossary = await build_glossary(registry)
        schema_chunks = build_schema_docs(registry, glossary)
        print("[ingest] building policy digest (LLM per PDF, cached)...")
        await build_policy_digest()
        if schema_chunks:
            print(
                f"[ingest] schema docs: {len(schema_chunks)} "
                f"(columns + value docs across {len(registry.get('tables', []))} tables)"
            )
    except Exception as exc:
        print(f"[ingest] warning: schema-doc build failed: {exc}")

    if row_chunks:
        texts = [c["text"] for c in row_chunks]
        embeddings = embedder.embed_texts(texts)
        store.upsert_chunks(row_chunks, embeddings)
        all_chunks.extend(row_chunks)

    if schema_chunks:
        texts = [c["text"] for c in schema_chunks]
        embeddings = embedder.embed_texts(texts)
        store.upsert_chunks(schema_chunks, embeddings)
        all_chunks.extend(schema_chunks)
        print(f"[ingest] embedded {len(schema_chunks)} schema docs")

        from collections import Counter
        per_table = Counter(c["table"] for c in row_chunks)
        seen_slugs: set[str] = set()
        for rc in row_chunks:
            seen_slugs.add(rc["doc_slug"])
        for slug in seen_slugs:
            same_slug = [c for c in row_chunks if c["doc_slug"] == slug]
            head = same_slug[0]
            doc_rows.append({
                "doc_slug": head["doc_slug"],
                "doc_name": head["doc_name"],
                "file_name": head["file_name"],
                "domain": head["domain"],
                "security_level": head["security_level"],
                "security_label": head["security_label"],
                "page_count": 0,
                "chunk_count": len(same_slug),
                "char_count": sum(c["char_count"] for c in same_slug),
            })
        print(
            f"[ingest] structured rows embedded: "
            + ", ".join(f"{k}={v}" for k, v in per_table.items())
        )

    bm25.build(all_chunks)
    try:
        bm25.save(settings.bm25_index_file)
    except Exception as exc:
        print(f"[ingest] warning: failed to persist BM25 index: {exc}")

    if chat_store.enabled:
        print(f"[ingest] mirroring {len(doc_rows)} docs / {len(all_chunks)} chunks → Postgres")
        await chat_store.upsert_documents(doc_rows)
        await chat_store.upsert_chunks(
            all_chunks,
            replace_doc_slugs=[d["doc_slug"] for d in doc_rows],
        )

    try:
        print("[ingest] building knowledge graph...")
        graph_builder = GraphBuilder()
        graph_data = graph_builder.build_full_graph(
            all_chunks,
            use_llm=bool(settings.openai_api_key),
        )
        request.app.state.graph_data = graph_data
        try:
            import json
            graph_file = settings.graph_data_file
            graph_file.parent.mkdir(parents=True, exist_ok=True)
            graph_file.write_text(json.dumps(graph_data))
        except Exception as exc:
            print(f"[ingest] warning: failed to persist graph: {exc}")
        print(
            f"[ingest] graph built: "
            f"{graph_data['stats']['total_documents']} docs, "
            f"{graph_data['stats']['total_chunks']} chunks, "
            f"{graph_data['stats']['total_entities']} entities, "
            f"{graph_data['stats']['total_relationships']} relationships"
        )
    except Exception as exc:
        print(f"[ingest] warning: knowledge graph build failed: {exc}")

    structured_summary: StructuredIngestSummary | None = None
    try:
        print("[ingest] ingesting structured corpus (Excel → SQLite)...")
        s = ingest_structured_corpus()
        structured_summary = StructuredIngestSummary(
            sqlite_path=s["sqlite_path"],
            schema_registry_path=s["schema_registry_path"],
            tables=[StructuredTableSummary(**t) for t in s["tables"]],
        )
        sql_engine = getattr(request.app.state, "sql_engine", None)
        if sql_engine is not None:
            sql_engine.reload()
            print(
                f"[ingest] SQL engine reloaded — "
                f"{len(sql_engine.registry.get('tables', []))} tables visible"
            )
    except StructuredIngestionError as exc:
        print(f"[ingest] warning: structured ingest failed: {exc}")
    except Exception as exc:
        print(f"[ingest] warning: structured ingest error: {exc}")

    return IngestResponse(
        status="success",
        documents_processed=len(details),
        total_chunks=len(all_chunks),
        collection_name=settings.collection_name,
        details=details,
        structured=structured_summary,
    )
