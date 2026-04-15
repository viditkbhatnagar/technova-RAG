"""POST /api/ingest — load all PDFs, chunk, embed, store, build BM25."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from backend.config import DOCUMENT_METADATA, settings
from backend.models import IngestDocDetail, IngestRequest, IngestResponse
from backend.services.chunker import chunk_document
from backend.services.graph_builder import GraphBuilder
from backend.services.loader import IngestionError, list_pdfs, load_pdf

router = APIRouter()


@router.post("/api/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest, request: Request) -> IngestResponse:
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
        print(
            f"[ingest] {file_name}: {len(pages)} pages → {len(chunks)} chunks"
        )

    if not all_chunks:
        raise HTTPException(
            status_code=500,
            detail="No chunks were produced from any document.",
        )

    bm25.build(all_chunks)
    try:
        bm25.save(settings.bm25_index_file)
    except Exception as exc:
        print(f"[ingest] warning: failed to persist BM25 index: {exc}")

    try:
        print("[ingest] building knowledge graph...")
        graph_builder = GraphBuilder()
        graph_data = graph_builder.build_full_graph(
            all_chunks,
            use_llm=bool(settings.openai_api_key),
        )
        request.app.state.graph_data = graph_data
        print(
            f"[ingest] graph built: "
            f"{graph_data['stats']['total_documents']} docs, "
            f"{graph_data['stats']['total_chunks']} chunks, "
            f"{graph_data['stats']['total_entities']} entities, "
            f"{graph_data['stats']['total_relationships']} relationships"
        )
    except Exception as exc:
        print(f"[ingest] warning: knowledge graph build failed: {exc}")

    return IngestResponse(
        status="success",
        documents_processed=len(details),
        total_chunks=len(all_chunks),
        collection_name=settings.collection_name,
        details=details,
    )
