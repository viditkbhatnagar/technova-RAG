"""Pipeline router — architecture diagram + live retrieval trace."""

import time

from fastapi import APIRouter, HTTPException, Request

from backend.config import ROLE_CLEARANCE, settings
from backend.models import (
    PipelineArchitectureResponse,
    PipelineStageInfo,
    PipelineTraceRequest,
    PipelineTraceResponse,
)
from backend.services.generator import assemble_prompt, generate_answer
from backend.services.security import get_allowed_chunk_ids, get_security_filter

router = APIRouter()


_TEXT_PREVIEW_CHARS = 240


def _candidate_view(chunk: dict, score_field: str) -> dict:
    text = chunk.get("text", "") or ""
    return {
        "chunk_id": chunk.get("chunk_id"),
        "doc_name": chunk.get("doc_name"),
        "doc_slug": chunk.get("doc_slug"),
        "page_number": chunk.get("page_number"),
        "security_level": chunk.get("security_level"),
        "security_label": chunk.get("security_label"),
        "score": float(chunk.get(score_field, chunk.get("score", 0.0)) or 0.0),
        "text_preview": text[:_TEXT_PREVIEW_CHARS] + ("…" if len(text) > _TEXT_PREVIEW_CHARS else ""),
        "retrieval_method": chunk.get("retrieval_method"),
    }


@router.get("/api/pipeline/architecture", response_model=PipelineArchitectureResponse)
def pipeline_architecture() -> PipelineArchitectureResponse:
    stages = [
        PipelineStageInfo(
            id="query",
            label="Query",
            description="The user's natural-language question.",
            role="input",
            color="#94a3b8",
        ),
        PipelineStageInfo(
            id="embed",
            label="Embed",
            description=(
                "Encode the query into a 768-dim vector with the BGE bi-encoder. "
                "Runs locally on MPS/CPU — no network call."
            ),
            role="encoder",
            model=settings.embedding_model,
            color="#a855f7",
        ),
        PipelineStageInfo(
            id="dense",
            label="Dense (Qdrant)",
            description=(
                "Cosine similarity search over the Qdrant vector store. "
                "Returns top-K candidates with optional security pre-filter."
            ),
            role="retriever",
            model="Qdrant",
            color="#22d3ee",
        ),
        PipelineStageInfo(
            id="bm25",
            label="BM25",
            description=(
                "Keyword search via rank_bm25 over the in-memory tokenized index. "
                "Returns top-K lexical matches, allow-list filtered for secure mode."
            ),
            role="retriever",
            model="rank_bm25",
            color="#facc15",
        ),
        PipelineStageInfo(
            id="rrf",
            label="RRF Fusion",
            description=(
                "Reciprocal Rank Fusion combines dense + BM25 rankings using "
                f"score = sum(1 / (k + rank)), k={settings.rrf_k}."
            ),
            role="fusion",
            model=None,
            color="#f97316",
        ),
        PipelineStageInfo(
            id="rerank",
            label="Cross-Encoder Rerank",
            description=(
                "Rerank the fused candidates with a cross-encoder that scores "
                "(query, chunk) pairs jointly. Local, MPS/CPU."
            ),
            role="reranker",
            model=settings.reranker_model,
            color="#ec4899",
        ),
        PipelineStageInfo(
            id="final",
            label="Top-K",
            description="Final cited chunks returned to the UI / passed to the LLM.",
            role="output",
            color="#10b981",
        ),
        PipelineStageInfo(
            id="llm",
            label="LLM Answer",
            description=(
                "Optional. Assembles a prompt from the top-K chunks and asks "
                f"{settings.llm_model} for a grounded answer. Skipped if no API key."
            ),
            role="generator",
            model=settings.llm_model,
            color="#8b5cf6",
            runs_locally=False,
        ),
    ]

    edges = [
        {"source": "query", "target": "embed"},
        {"source": "embed", "target": "dense"},
        {"source": "query", "target": "bm25"},
        {"source": "dense", "target": "rrf"},
        {"source": "bm25", "target": "rrf"},
        {"source": "rrf", "target": "rerank"},
        {"source": "rerank", "target": "final"},
        {"source": "final", "target": "llm"},
    ]

    return PipelineArchitectureResponse(stages=stages, edges=edges)


@router.post("/api/pipeline/trace", response_model=PipelineTraceResponse)
async def pipeline_trace(req: PipelineTraceRequest, request: Request) -> PipelineTraceResponse:
    retriever = request.app.state.retriever
    store = request.app.state.store
    bm25 = request.app.state.bm25
    embedder = request.app.state.embedder

    if not store.collection_exists():
        raise HTTPException(
            status_code=404,
            detail="No documents ingested. Call POST /api/ingest first.",
        )
    if not bm25.is_ready():
        raise HTTPException(
            status_code=404,
            detail="BM25 index not built. Call POST /api/ingest first.",
        )
    if req.mode == "secure" and not req.role:
        raise HTTPException(
            status_code=400,
            detail="Role is required when mode is 'secure'.",
        )

    t_total = time.perf_counter()

    security_filter = None
    allowed_ids = None
    if req.mode == "secure":
        security_filter = get_security_filter(req.role)
        allowed_ids = get_allowed_chunk_ids(store, req.role)

    result = retriever.retrieve(
        query=req.query,
        top_k=req.top_k,
        top_k_retrieval=settings.top_k_retrieval,
        rrf_k=settings.rrf_k,
        security_filter=security_filter,
        allowed_chunk_ids=allowed_ids,
        return_intermediates=True,
    )

    intermediates = result.get("intermediates", {})
    final_chunks = result["chunks"]
    stats = result["stats"]
    stats["mode"] = req.mode
    stats["role"] = req.role

    # Restricted-space probe (informational only) for secure mode
    restricted_info: dict | None = None
    if req.mode == "secure":
        query_vec = embedder.embed_query(req.query)
        restricted_hits = store.search(
            query_embedding=query_vec,
            top_k=10,
            security_filter={"security_level": {"$gt": ROLE_CLEARANCE[req.role]}},
        )
        restricted_info = {
            "count": len(restricted_hits),
            "top_cosine": round(
                max((float(h.get("score", 0.0)) for h in restricted_hits), default=0.0),
                4,
            ),
        }

    stages: dict = {
        "query": {"text": req.query},
        "embed": {
            "model": settings.embedding_model,
            "device": getattr(embedder, "device", "cpu"),
            "vector_dim": intermediates.get("embed", {}).get("vector_dim"),
            "elapsed_ms": intermediates.get("embed", {}).get("elapsed_ms", 0),
        },
        "dense": {
            "model": "Qdrant cosine",
            "candidates": [
                _candidate_view(c, "score")
                for c in intermediates.get("dense", {}).get("candidates", [])
            ],
            "elapsed_ms": intermediates.get("dense", {}).get("elapsed_ms", 0),
            "security_filtered": req.mode == "secure",
        },
        "bm25": {
            "model": "rank_bm25",
            "candidates": [
                _candidate_view(c, "score")
                for c in intermediates.get("bm25", {}).get("candidates", [])
            ],
            "elapsed_ms": intermediates.get("bm25", {}).get("elapsed_ms", 0),
            "security_filtered": req.mode == "secure",
        },
        "rrf": {
            "k": settings.rrf_k,
            "candidates": [
                _candidate_view(c, "rrf_score")
                for c in intermediates.get("rrf", {}).get("candidates", [])
            ],
            "elapsed_ms": intermediates.get("rrf", {}).get("elapsed_ms", 0),
            "overlap_count": stats.get("overlap_count", 0),
        },
        "rerank": {
            "model": settings.reranker_model,
            "device": getattr(retriever, "reranker_device", "cpu"),
            "candidates": [
                _candidate_view(c, "rerank_score")
                for c in intermediates.get("rerank", {}).get("candidates", [])
            ],
            "elapsed_ms": intermediates.get("rerank", {}).get("elapsed_ms", 0),
        },
        "final": {
            "top_k": [_candidate_view(c, "rerank_score") for c in final_chunks],
            "count": len(final_chunks),
        },
    }

    if restricted_info is not None:
        stages["security"] = {
            "role": req.role,
            "clearance": ROLE_CLEARANCE[req.role],
            "restricted_probe": restricted_info,
        }

    llm_used = False
    if req.run_llm:
        t_llm = time.perf_counter()
        answer, prompt = await generate_answer(req.query, final_chunks)
        llm_ms = int((time.perf_counter() - t_llm) * 1000)
        llm_used = bool(settings.openai_api_key) and bool(final_chunks)
        stages["llm"] = {
            "used": llm_used,
            "model": settings.llm_model if llm_used else None,
            "answer": answer,
            "prompt_chars": len(prompt or ""),
            "elapsed_ms": llm_ms,
        }
    else:
        stages["llm"] = {
            "used": False,
            "model": None,
            "answer": assemble_prompt(req.query, final_chunks),
            "prompt_chars": 0,
            "elapsed_ms": 0,
        }

    total_ms = int((time.perf_counter() - t_total) * 1000)

    return PipelineTraceResponse(
        query=req.query,
        mode=req.mode,
        role=req.role,
        stages=stages,
        stats=stats,
        total_elapsed_ms=total_ms,
    )
