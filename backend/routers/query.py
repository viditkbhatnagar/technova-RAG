"""POST /api/query — hybrid retrieval + (optional) security + generation."""

from fastapi import APIRouter, HTTPException, Request

from backend.models import ChunkResult, QueryRequest, QueryResponse
from backend.services.generator import assemble_prompt, generate_answer
from backend.services.security import self_correcting_retrieve

router = APIRouter()


def _to_chunk_result(chunk: dict) -> ChunkResult:
    score = chunk.get("rerank_score")
    if score is None:
        score = chunk.get("rrf_score", chunk.get("score", 0.0))
    return ChunkResult(
        chunk_id=chunk["chunk_id"],
        text=chunk["text"],
        score=round(float(score), 4),
        doc_name=chunk.get("doc_name", ""),
        page_number=int(chunk.get("page_number", 0) or 0),
        security_level=int(chunk.get("security_level", 0) or 0),
        retrieval_method=chunk.get("retrieval_method", "hybrid"),
    )


@router.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest, request: Request) -> QueryResponse:
    retriever = request.app.state.retriever
    store = request.app.state.store
    bm25 = request.app.state.bm25

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
            detail="Role is required when mode is 'secure'. Use 'employee', 'manager', or 'admin'.",
        )

    from backend.config import settings as cfg

    if req.mode == "secure":
        outcome = self_correcting_retrieve(
            retriever=retriever,
            store=store,
            query=req.query,
            role=req.role,
            top_k=req.top_k,
            top_k_retrieval=cfg.top_k_retrieval,
            rrf_k=cfg.rrf_k,
        )
        chunks = outcome["chunks"]
        stats = outcome["stats"]
        access_denied = outcome["access_denied"]
        access_denied_message = outcome["access_denied_message"]
        stats["mode"] = "secure"
        stats["role"] = req.role
    else:
        result = retriever.retrieve(
            query=req.query,
            top_k=req.top_k,
            top_k_retrieval=cfg.top_k_retrieval,
            rrf_k=cfg.rrf_k,
        )
        chunks = result["chunks"]
        stats = result["stats"]
        stats["mode"] = "open"
        stats["role"] = None
        access_denied = False
        access_denied_message = None

    if access_denied:
        answer = (
            "I don't have access to that information at your current clearance level. "
            + (access_denied_message or "")
        )
        return QueryResponse(
            answer=answer.strip(),
            sources=[],
            prompt_assembled="",
            retrieval_stats=stats,
            access_denied=True,
            access_denied_message=access_denied_message,
        )

    answer, prompt = await generate_answer(req.query, chunks)
    if not prompt:
        prompt = assemble_prompt(req.query, chunks)

    return QueryResponse(
        answer=answer,
        sources=[_to_chunk_result(c) for c in chunks],
        prompt_assembled=prompt,
        retrieval_stats=stats,
        access_denied=False,
        access_denied_message=None,
    )
