"""Pydantic request/response schemas for the TechNova RAG API."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ---------- /api/ingest ----------

class IngestRequest(BaseModel):
    docs_path: str | None = None
    force_reingest: bool = False


class IngestDocDetail(BaseModel):
    file_name: str
    pages: int
    chunks: int
    security_level: str


class StructuredTableSummary(BaseModel):
    name: str
    rows: int
    security: str


class StructuredIngestSummary(BaseModel):
    sqlite_path: str
    schema_registry_path: str
    tables: list[StructuredTableSummary]


class IngestResponse(BaseModel):
    status: str
    documents_processed: int
    total_chunks: int
    collection_name: str
    details: list[IngestDocDetail]
    structured: StructuredIngestSummary | None = None


# ---------- /api/query ----------

class QueryRequest(BaseModel):
    query: str
    mode: Literal["open", "secure"] = "open"
    role: Literal["employee", "manager", "admin"] | None = None
    top_k: int = 5
    session_id: UUID | None = None


class ChunkResult(BaseModel):
    chunk_id: str
    text: str
    score: float
    doc_name: str
    page_number: int
    security_level: int
    retrieval_method: str


class SqlAttempt(BaseModel):
    sql: str
    error: str | None = None


class SqlResult(BaseModel):
    ok: bool
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    elapsed_ms: int | None = None
    total_elapsed_ms: int | None = None
    error: str | None = None
    attempts: list[SqlAttempt] = Field(default_factory=list)


class RouteDecision(BaseModel):
    route: Literal["sql", "rag", "hybrid"]
    confidence: str
    reason: str
    signals: dict[str, Any] = Field(default_factory=dict)
    heuristic_reason: str | None = None


class AgentStep(BaseModel):
    step: int
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    result_preview: str = ""


class AgentTrace(BaseModel):
    used: bool = False
    iterations: int = 0
    exceeded: bool = False
    total_elapsed_ms: int | None = None
    steps: list[AgentStep] = Field(default_factory=list)


class QueryResponse(BaseModel):
    answer: str
    sources: list[ChunkResult]
    prompt_assembled: str
    retrieval_stats: dict[str, Any]
    access_denied: bool = False
    access_denied_message: str | None = None
    session_id: UUID | None = None
    route: RouteDecision | None = None
    sql_result: SqlResult | None = None
    agent_trace: AgentTrace | None = None


# ---------- /api/sessions ----------

class SessionSummary(BaseModel):
    id: UUID
    mode: str
    role: str | None = None
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class StoredMessage(BaseModel):
    id: UUID
    role: str
    content: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_stats: dict[str, Any] = Field(default_factory=dict)
    access_denied: bool = False
    access_denied_message: str | None = None
    created_at: datetime


class SessionDetail(SessionSummary):
    messages: list[StoredMessage] = Field(default_factory=list)


# ---------- /api/status ----------

class CollectionStats(BaseModel):
    name: str
    vectors_count: int
    points_count: int
    segments_count: int


class StatusResponse(BaseModel):
    status: str
    qdrant_connected: bool
    collection_exists: bool
    collection_stats: CollectionStats | None = None
    bm25_index_loaded: bool = False
    embedding_model: str | None = None
    embedding_device: str | None = None
    reranker_model: str | None = None
    llm_configured: bool = False
    documents_ingested: int = 0
    message: str | None = None


# ---------- /api/documents ----------

class DocumentSummary(BaseModel):
    doc_slug: str
    doc_name: str
    file_name: str
    domain: str
    security_level: int
    security_label: str
    page_count: int
    chunk_count: int
    char_count: int
    ingested_at: datetime


class ChunkRecord(BaseModel):
    chunk_id: str
    doc_slug: str
    text: str
    page_number: int
    chunk_index: int
    char_count: int
    content_hash: str
    security_level: int
    security_label: str
    domain: str
    created_at: datetime | None = None


class ChunkPage(BaseModel):
    items: list[ChunkRecord]
    total: int
    limit: int
    offset: int


class DocumentDetail(DocumentSummary):
    sample_chunks: list[ChunkRecord] = Field(default_factory=list)


class SyncResponse(BaseModel):
    status: str
    documents_written: int
    chunks_written: int
    message: str | None = None


# ---------- /api/pipeline ----------

class PipelineStageInfo(BaseModel):
    id: str
    label: str
    description: str
    role: str
    model: str | None = None
    color: str
    runs_locally: bool = True


class PipelineArchitectureResponse(BaseModel):
    stages: list[PipelineStageInfo]
    edges: list[dict[str, str]]


class PipelineTraceRequest(BaseModel):
    query: str
    mode: Literal["open", "secure"] = "open"
    role: Literal["employee", "manager", "admin"] | None = None
    top_k: int = 5
    run_llm: bool = True


class PipelineTraceResponse(BaseModel):
    query: str
    mode: str
    role: str | None = None
    stages: dict[str, Any]
    stats: dict[str, Any]
    total_elapsed_ms: int
    access_denied: bool = False
    access_denied_message: str | None = None


# ---------- Internal ----------

class RetrievalResult(BaseModel):
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
