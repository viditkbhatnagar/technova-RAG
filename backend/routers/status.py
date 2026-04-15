"""GET /api/status — health check + collection stats."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.models import CollectionStats, StatusResponse

router = APIRouter()


@router.get("/api/status")
def status(request: Request):
    embedder = getattr(request.app.state, "embedder", None)
    store = getattr(request.app.state, "store", None)
    bm25 = getattr(request.app.state, "bm25", None)

    # Qdrant connectivity
    qdrant_connected = False
    try:
        if store is not None:
            store.client.get_collections()
            qdrant_connected = True
    except Exception:
        qdrant_connected = False

    if not qdrant_connected:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "qdrant_connected": False,
                "message": (
                    "Cannot connect to Qdrant. Ensure Docker is running: "
                    "docker compose up -d qdrant"
                ),
            },
        )

    collection_exists = store.collection_exists() if store else False
    if not collection_exists:
        return StatusResponse(
            status="not_initialized",
            qdrant_connected=True,
            collection_exists=False,
            embedding_model=settings.embedding_model,
            embedding_device=embedder.device if embedder else None,
            reranker_model=settings.reranker_model,
            llm_configured=bool(settings.openai_api_key),
            message="No documents ingested. Call POST /api/ingest to initialize.",
        )

    info = store.get_collection_info()
    documents_ingested = 0
    try:
        documents_ingested = store.count_distinct_docs()
    except Exception:
        pass

    return StatusResponse(
        status="healthy",
        qdrant_connected=True,
        collection_exists=True,
        collection_stats=CollectionStats(**info),
        bm25_index_loaded=bm25.is_ready() if bm25 else False,
        embedding_model=settings.embedding_model,
        embedding_device=embedder.device if embedder else None,
        reranker_model=settings.reranker_model,
        llm_configured=bool(settings.openai_api_key),
        documents_ingested=documents_ingested,
    )
