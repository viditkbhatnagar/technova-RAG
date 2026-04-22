"""POST /api/query — router → (SQL | RAG | hybrid) → answer synthesis.

The orchestrator:
  1. Picks a route (sql / rag / hybrid) via heuristic + optional LLM fallback.
  2. Runs the structured (SQL) path and/or the unstructured (RAG) path.
  3. Synthesizes a single answer grounded on whichever evidence came back.
  4. Honors role clearance on BOTH paths — the SQL engine filters visible
     tables, the RAG path runs self_correcting_retrieve as before.
"""

import uuid

from fastapi import APIRouter, HTTPException, Request
from openai import AsyncOpenAI, OpenAIError

from backend.config import settings as cfg
from backend.models import (
    AgentStep,
    AgentTrace,
    ChunkResult,
    QueryRequest,
    QueryResponse,
    RouteDecision,
    SqlAttempt,
    SqlResult,
)
from backend.services.db import chat_store
from backend.services.generator import assemble_prompt, generate_answer
from backend.services.query_router import required_restricted_tables, route_query
from backend.services.security import self_correcting_retrieve
from backend.services.sql_agent import SQLAgent
from backend.services.sql_engine import SQLEngine, format_rows_for_llm

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


def _to_sql_result(raw: dict) -> SqlResult:
    return SqlResult(
        ok=bool(raw.get("ok")),
        sql=raw.get("sql"),
        columns=list(raw.get("columns") or []),
        rows=list(raw.get("rows") or []),
        row_count=int(raw.get("row_count") or 0),
        truncated=bool(raw.get("truncated", False)),
        elapsed_ms=raw.get("elapsed_ms"),
        total_elapsed_ms=raw.get("total_elapsed_ms"),
        error=raw.get("error"),
        attempts=[SqlAttempt(**a) for a in raw.get("attempts", []) if isinstance(a, dict)],
    )


_HYBRID_SYSTEM = """You are a TechNova analyst. Answer the user's question using:
- STRUCTURED RESULT: the table below is the authoritative source for numbers, counts, lists, rankings.
- DOCUMENT CONTEXT: use these excerpts for narrative/policy framing.

Rules:
- Cite [Source N] for any fact taken from DOCUMENT CONTEXT.
- Quote exact numbers from STRUCTURED RESULT — do not re-estimate or round.
- If both sources disagree, trust STRUCTURED RESULT for numeric facts.
- Keep the answer concise and directly address the question.
"""


async def _synthesize_hybrid(
    query: str,
    sql_result: dict,
    chunks: list[dict],
) -> str:
    """Compose a grounded answer from SQL rows + retrieved chunks."""
    table_md = format_rows_for_llm(sql_result, max_rows=30)
    if not chunks:
        doc_block = "(no supporting narrative retrieved)"
    else:
        doc_block = "\n\n".join(
            f"[Source {i+1}] ({c.get('doc_name', '?')}, page {c.get('page_number', '?')})\n{c.get('text', '')}"
            for i, c in enumerate(chunks)
        )

    if not cfg.openai_api_key:
        prompt = (
            f"SYSTEM:\n{_HYBRID_SYSTEM}\n\n"
            f"STRUCTURED RESULT (SQL):\n```sql\n{sql_result.get('sql', '')}\n```\n{table_md}\n\n"
            f"DOCUMENT CONTEXT:\n{doc_block}\n\nQUESTION: {query}\n"
        )
        return f"[LLM not configured — returning assembled prompt]\n\n{prompt}"

    client = AsyncOpenAI(api_key=cfg.openai_api_key)
    try:
        resp = await client.chat.completions.create(
            model=cfg.llm_model,
            messages=[
                {"role": "system", "content": _HYBRID_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"QUESTION: {query}\n\n"
                        f"STRUCTURED RESULT (SQL):\n```sql\n{sql_result.get('sql', '')}\n```\n{table_md}\n\n"
                        f"DOCUMENT CONTEXT:\n{doc_block}"
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=700,
        )
        return (resp.choices[0].message.content or "").strip() or "[Empty response from LLM]"
    except OpenAIError as exc:
        return f"[LLM synthesis failed: {exc}]"


async def _sql_only_answer(query: str, sql_result: dict) -> str:
    """Narrate a SQL-only result (numbers are authoritative)."""
    table_md = format_rows_for_llm(sql_result, max_rows=30)
    if not cfg.openai_api_key:
        return (
            f"[LLM not configured]\n\nSQL:\n```sql\n{sql_result.get('sql', '')}\n```\n\n{table_md}"
        )

    client = AsyncOpenAI(api_key=cfg.openai_api_key)
    system = (
        "You are a TechNova analyst. The STRUCTURED RESULT table below is the authoritative "
        "answer to the user's question. Narrate it concisely — quote exact numbers. If 0 rows, "
        "say so plainly. Do not invent facts beyond the table."
    )
    try:
        resp = await client.chat.completions.create(
            model=cfg.llm_model,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"QUESTION: {query}\n\nSTRUCTURED RESULT:\n```sql\n{sql_result.get('sql', '')}\n```\n{table_md}"
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=500,
        )
        return (resp.choices[0].message.content or "").strip() or "[Empty response from LLM]"
    except OpenAIError as exc:
        return f"[LLM call failed: {exc}]\n\n{table_md}"


@router.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest, request: Request) -> QueryResponse:
    retriever = request.app.state.retriever
    store = request.app.state.store
    bm25 = request.app.state.bm25
    sql_engine: SQLEngine | None = getattr(request.app.state, "sql_engine", None)

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

    session_id = req.session_id or uuid.uuid4()

    # ---- 1. Route the query ----
    route_info = await route_query(req.query)
    requested_route: str = route_info["route"]
    effective_role = req.role if req.mode == "secure" else None
    if requested_route in ("sql", "hybrid") and (sql_engine is None or not sql_engine.is_ready()):
        requested_route = "rag"
        route_info = {
            **route_info,
            "route": "rag",
            "reason": route_info.get("reason", "") + " [SQL engine not ready → RAG only]",
        }

    route_decision = RouteDecision(
        route=requested_route,
        confidence=str(route_info.get("confidence", "")),
        reason=str(route_info.get("reason", "")),
        signals=dict(route_info.get("signals") or {}),
        heuristic_reason=route_info.get("heuristic_reason"),
    )

    # ---- 2. Run SQL path (if applicable) ----
    raw_sql: dict | None = None
    agent_outcome: dict | None = None
    restricted_preflight: list[str] = []
    if requested_route in ("sql", "hybrid") and sql_engine is not None:
        restricted_preflight = required_restricted_tables(req.query, effective_role)
        if restricted_preflight:
            raw_sql = {
                "ok": False,
                "error": (
                    "Question requires restricted table(s): "
                    + ", ".join(restricted_preflight)
                ),
                "attempts": [],
            }
        elif cfg.sql_agent_enabled:
            agent = SQLAgent(
                sql_engine=sql_engine,
                retriever=retriever,
                store=store,
                embedder=request.app.state.embedder,
            )
            agent_outcome = await agent.answer(req.query, effective_role)
            # Surface the agent's last run_sql result in sql_result so the UI
            # renders a table; the final narrative comes from agent_outcome.answer.
            sqls = agent_outcome.get("sql_results") or []
            if sqls:
                last = sqls[-1]
                raw_sql = {
                    "ok": True,
                    "sql": last.get("sql"),
                    "columns": last.get("columns") or [],
                    "rows": last.get("rows") or [],
                    "row_count": last.get("row_count") or 0,
                    "truncated": False,
                    "attempts": [],
                }
            else:
                raw_sql = {
                    "ok": False,
                    "error": agent_outcome.get("error") or "Agent completed without SQL",
                    "attempts": [],
                }
        else:
            raw_sql = await sql_engine.answer(req.query, effective_role)

    # ---- 3. Run RAG path (always, unless pure SQL and it succeeded) ----
    chunks: list[dict] = []
    stats: dict = {}
    access_denied = False
    access_denied_message: str | None = None

    run_rag = requested_route in ("rag", "hybrid") or not (raw_sql and raw_sql.get("ok"))

    if run_rag:
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
            rresult = retriever.retrieve(
                query=req.query,
                top_k=req.top_k,
                top_k_retrieval=cfg.top_k_retrieval,
                rrf_k=cfg.rrf_k,
            )
            chunks = rresult["chunks"]
            stats = rresult["stats"]
            stats["mode"] = "open"
            stats["role"] = None

    stats.setdefault("mode", "secure" if req.mode == "secure" else "open")
    stats.setdefault("role", req.role)
    stats["route"] = route_decision.route
    stats["route_reason"] = route_decision.reason
    stats["route_confidence"] = route_decision.confidence
    if raw_sql is not None:
        stats["sql_ok"] = bool(raw_sql.get("ok"))
        stats["sql_rows"] = int(raw_sql.get("row_count") or 0)
        if raw_sql.get("error"):
            stats["sql_error"] = raw_sql["error"]

    # Preflight: question topically requires a restricted table. Don't let
    # the LLM silently substitute an accessible table — surface access-denied.
    if restricted_preflight and not access_denied:
        access_denied = True
        tbl_list = ", ".join(restricted_preflight)
        access_denied_message = (
            f"This question requires data from restricted table(s): {tbl_list}. "
            "Contact your department head for access."
        )
        stats["restricted_tables"] = restricted_preflight

    # ---- 4. Access-denied short-circuit (RAG-side) ----
    if access_denied:
        answer = (
            "I don't have access to that information at your current clearance level. "
            + (access_denied_message or "")
        ).strip()
        chat_store.schedule_save(
            session_id=session_id,
            mode=req.mode,
            role=req.role,
            user_query=req.query,
            assistant_answer=answer,
            sources=[],
            retrieval_stats=stats,
            access_denied=True,
            access_denied_message=access_denied_message,
        )
        chat_store.schedule_query_run(
            query=req.query,
            mode=req.mode,
            role=req.role,
            top_k=req.top_k,
            stats=stats,
            top_chunks=[],
            llm_used=False,
            access_denied=True,
        )
        return QueryResponse(
            answer=answer,
            sources=[],
            prompt_assembled="",
            retrieval_stats=stats,
            access_denied=True,
            access_denied_message=access_denied_message,
            session_id=session_id,
            route=route_decision,
            sql_result=_to_sql_result(raw_sql) if raw_sql else None,
        )

    # ---- 5. Synthesize answer ----
    source_results = [_to_chunk_result(c) for c in chunks]

    if agent_outcome and agent_outcome.get("ok") and agent_outcome.get("answer"):
        # Agent has already composed a final grounded answer using tools
        # (SQL + retrieve + calculator). Skip the single-shot synthesizer.
        answer = agent_outcome["answer"]
        prompt = f"[Agent] {len(agent_outcome.get('trace', []))} tool calls"
    elif route_decision.route == "sql" and raw_sql and raw_sql.get("ok"):
        answer = await _sql_only_answer(req.query, raw_sql)
        prompt = f"[SQL] {raw_sql.get('sql', '')}"
    elif route_decision.route == "hybrid" and raw_sql and raw_sql.get("ok"):
        answer = await _synthesize_hybrid(req.query, raw_sql, chunks)
        prompt = assemble_prompt(req.query, chunks)
    else:
        answer, prompt = await generate_answer(req.query, chunks)
        if not prompt:
            prompt = assemble_prompt(req.query, chunks)

    agent_trace_out: AgentTrace | None = None
    if agent_outcome is not None:
        agent_trace_out = AgentTrace(
            used=True,
            iterations=int(agent_outcome.get("iterations") or 0),
            exceeded=bool(agent_outcome.get("exceeded", False)),
            total_elapsed_ms=agent_outcome.get("total_elapsed_ms"),
            steps=[
                AgentStep(
                    step=int(s.get("step", 0)),
                    tool=str(s.get("tool", "")),
                    args=dict(s.get("args") or {}),
                    result_preview=str(s.get("result_preview", ""))[:400],
                )
                for s in agent_outcome.get("trace", [])
            ],
        )
        stats["agent_used"] = True
        stats["agent_iterations"] = agent_trace_out.iterations

    chat_store.schedule_save(
        session_id=session_id,
        mode=req.mode,
        role=req.role,
        user_query=req.query,
        assistant_answer=answer,
        sources=[s.model_dump() for s in source_results],
        retrieval_stats=stats,
        access_denied=False,
        access_denied_message=None,
    )
    chat_store.schedule_query_run(
        query=req.query,
        mode=req.mode,
        role=req.role,
        top_k=req.top_k,
        stats=stats,
        top_chunks=[
            {"chunk_id": s.chunk_id, "score": s.score, "doc_name": s.doc_name}
            for s in source_results
        ],
        llm_used=bool(cfg.openai_api_key),
        access_denied=False,
    )

    return QueryResponse(
        answer=answer,
        sources=source_results,
        prompt_assembled=prompt,
        retrieval_stats=stats,
        access_denied=False,
        access_denied_message=None,
        session_id=session_id,
        route=route_decision,
        sql_result=_to_sql_result(raw_sql) if raw_sql else None,
        agent_trace=agent_trace_out,
    )
