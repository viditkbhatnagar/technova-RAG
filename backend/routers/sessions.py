"""Chat session endpoints — list, fetch, delete."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from backend.models import SessionDetail, SessionSummary, StoredMessage
from backend.services.db import chat_store

router = APIRouter()


@router.get("/api/sessions", response_model=list[SessionSummary])
async def list_sessions(
    mode: Literal["open", "secure"] | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SessionSummary]:
    if not chat_store.enabled:
        return []
    rows = await chat_store.list_sessions(mode=mode, limit=limit)
    return [SessionSummary(**r) for r in rows]


@router.get("/api/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: UUID) -> SessionDetail:
    if not chat_store.enabled:
        raise HTTPException(
            status_code=503,
            detail="Chat history is not configured (DATABASE_URL missing).",
        )
    data = await chat_store.get_session(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    messages = [StoredMessage(**m) for m in data.pop("messages", [])]
    return SessionDetail(**data, messages=messages, message_count=len(messages))


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: UUID) -> dict:
    if not chat_store.enabled:
        raise HTTPException(
            status_code=503,
            detail="Chat history is not configured (DATABASE_URL missing).",
        )
    deleted = await chat_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"deleted": True}
