"""FastAPI app entry point for TechNova RAG."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routers import documents as documents_router
from backend.routers import graph as graph_router
from backend.routers import ingest as ingest_router
from backend.routers import pipeline as pipeline_router
from backend.routers import query as query_router
from backend.routers import sessions as sessions_router
from backend.routers import status as status_router
from backend.services.bm25_index import BM25Index
from backend.services.db import chat_store
from backend.services.embedder import EmbeddingService
from backend.services.retriever import HybridRetriever
from backend.services.sql_engine import SQLEngine
from backend.services.store import QdrantStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[startup] loading embedding model...")
    embedder = EmbeddingService(model_name=settings.embedding_model)

    print("[startup] connecting to Qdrant...")
    store = QdrantStore(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection_name=settings.collection_name,
    )

    print("[startup] loading BM25 index (if persisted)...")
    bm25 = BM25Index()
    try:
        loaded = bm25.load(settings.bm25_index_file)
        if loaded:
            print(f"[startup] BM25 index loaded ({len(bm25.chunk_ids)} chunks)")
        else:
            print("[startup] no persisted BM25 index found — build via /api/ingest")
    except Exception as exc:
        print(f"[startup] BM25 load failed: {exc}")

    print("[startup] loading reranker...")
    retriever = HybridRetriever(
        store=store,
        bm25=bm25,
        embedder=embedder,
        reranker_model=settings.reranker_model,
    )

    app.state.embedder = embedder
    app.state.store = store
    app.state.bm25 = bm25
    app.state.retriever = retriever

    print("[startup] loading SQL engine (structured corpus)...")
    sql_engine = SQLEngine()
    if sql_engine.is_ready():
        tbl_count = len(sql_engine.registry.get("tables", []))
        print(f"[startup] SQL engine ready ({tbl_count} tables)")
    else:
        print("[startup] SQL engine not ready — run /api/ingest to build SQLite")
    app.state.sql_engine = sql_engine

    app.state.graph_data = None
    graph_file = settings.graph_data_file
    if graph_file.exists():
        try:
            import json
            app.state.graph_data = json.loads(graph_file.read_text())
            stats = app.state.graph_data.get("stats", {})
            print(
                f"[startup] graph loaded: "
                f"{stats.get('total_documents', 0)} docs, "
                f"{stats.get('total_chunks', 0)} chunks, "
                f"{stats.get('total_entities', 0)} entities, "
                f"{stats.get('total_relationships', 0)} relationships"
            )
        except Exception as exc:
            print(f"[startup] graph load failed: {exc}")
    else:
        print("[startup] no persisted graph found — build via /api/ingest")

    print("[startup] connecting to Postgres (chat history)...")
    await chat_store.init(settings.database_url)

    print("[startup] ready.")

    yield

    print("[shutdown] closing Qdrant client")
    try:
        store.client.close()
    except Exception:
        pass
    print("[shutdown] closing Postgres pool")
    await chat_store.close()


app = FastAPI(
    title="TechNova RAG API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router.router)
app.include_router(query_router.router)
app.include_router(status_router.router)
app.include_router(graph_router.router)
app.include_router(sessions_router.router)
app.include_router(documents_router.router)
app.include_router(pipeline_router.router)


@app.get("/")
def root():
    return {"name": "TechNova RAG API", "version": "1.0.0"}
