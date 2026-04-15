"""Pydantic request/response schemas for the TechNova RAG API."""

from typing import Any, Literal

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


class IngestResponse(BaseModel):
    status: str
    documents_processed: int
    total_chunks: int
    collection_name: str
    details: list[IngestDocDetail]


# ---------- /api/query ----------

class QueryRequest(BaseModel):
    query: str
    mode: Literal["open", "secure"] = "open"
    role: Literal["employee", "manager", "admin"] | None = None
    top_k: int = 5


class ChunkResult(BaseModel):
    chunk_id: str
    text: str
    score: float
    doc_name: str
    page_number: int
    security_level: int
    retrieval_method: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[ChunkResult]
    prompt_assembled: str
    retrieval_stats: dict[str, Any]
    access_denied: bool = False
    access_denied_message: str | None = None


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


# ---------- Internal ----------

class RetrievalResult(BaseModel):
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
