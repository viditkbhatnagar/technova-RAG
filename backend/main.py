"""FastAPI app entry point for TechNova RAG."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routers import graph as graph_router
from backend.routers import ingest as ingest_router
from backend.routers import query as query_router
from backend.routers import status as status_router
from backend.services.bm25_index import BM25Index
from backend.services.embedder import EmbeddingService
from backend.services.retriever import HybridRetriever
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
    app.state.graph_data = None
    print("[startup] ready.")

    yield

    print("[shutdown] closing Qdrant client")
    try:
        store.client.close()
    except Exception:
        pass


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


@app.get("/")
def root():
    return {"name": "TechNova RAG API", "version": "1.0.0"}
