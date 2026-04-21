const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Mode = "open" | "secure";
export type Role = "employee" | "manager" | "admin";

export interface QueryRequest {
  query: string;
  mode: Mode;
  role?: Role;
  top_k?: number;
  session_id?: string;
}

export interface ChunkResult {
  chunk_id: string;
  text: string;
  score: number;
  doc_name: string;
  page_number: number;
  security_level: number;
  retrieval_method: string;
}

export interface RetrievalStats {
  dense_results?: number;
  bm25_results?: number;
  rrf_merged?: number;
  reranked_final?: number;
  overlap_count?: number;
  avg_rerank_score?: number;
  retrieval_time_ms?: number;
  mode?: string;
  role?: string | null;
  restricted_docs_exist?: boolean;
  restricted_doc_count?: number;
  [key: string]: unknown;
}

export type QueryRoute = "sql" | "rag" | "hybrid";

export interface RouteDecision {
  route: QueryRoute;
  confidence: string;
  reason: string;
  signals?: Record<string, unknown>;
  heuristic_reason?: string | null;
}

export interface SqlAttempt {
  sql: string;
  error?: string | null;
}

export interface SqlResult {
  ok: boolean;
  sql?: string | null;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  truncated: boolean;
  elapsed_ms?: number | null;
  total_elapsed_ms?: number | null;
  error?: string | null;
  attempts?: SqlAttempt[];
}

export interface QueryResponse {
  answer: string;
  sources: ChunkResult[];
  prompt_assembled: string;
  retrieval_stats: RetrievalStats;
  access_denied: boolean;
  access_denied_message: string | null;
  session_id: string | null;
  route?: RouteDecision | null;
  sql_result?: SqlResult | null;
}

export interface SessionSummary {
  id: string;
  mode: Mode;
  role: Role | null;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface StoredMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: ChunkResult[];
  retrieval_stats: RetrievalStats;
  access_denied: boolean;
  access_denied_message: string | null;
  created_at: string;
}

export interface SessionDetail extends SessionSummary {
  messages: StoredMessage[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: "document" | "chunk" | "entity";
  security_level?: number;
  security_label?: string;
  domain?: string;
  entity_type?: string;
  parent_doc?: string;
  page_number?: number;
  text_preview?: string;
  mentions?: number;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  label: string;
}

export interface GraphStats {
  total_documents: number;
  total_chunks: number;
  total_entities: number;
  total_relationships: number;
  entity_types?: Record<string, number>;
  [key: string]: unknown;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: GraphStats;
}

export async function queryRAG(params: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${API_URL}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res
      .json()
      .catch(() => ({ detail: `API error: ${res.status}` }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function fetchGraph(): Promise<GraphData> {
  const res = await fetch(`${API_URL}/api/graph`);
  if (!res.ok) throw new Error("Failed to load knowledge graph");
  return res.json();
}

export async function fetchStatus(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_URL}/api/status`);
  return res.json();
}

export async function triggerIngest(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_URL}/api/ingest`, { method: "POST" });
  return res.json();
}

export async function listSessions(mode?: Mode, limit = 50): Promise<SessionSummary[]> {
  const params = new URLSearchParams();
  if (mode) params.set("mode", mode);
  params.set("limit", String(limit));
  const res = await fetch(`${API_URL}/api/sessions?${params.toString()}`);
  if (!res.ok) return [];
  return res.json();
}

export async function getSession(sessionId: string): Promise<SessionDetail | null> {
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}`);
  if (!res.ok) return null;
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<boolean> {
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}`, { method: "DELETE" });
  return res.ok;
}

// ---------- documents ----------

export interface DocumentSummary {
  doc_slug: string;
  doc_name: string;
  file_name: string;
  domain: string;
  security_level: number;
  security_label: string;
  page_count: number;
  chunk_count: number;
  char_count: number;
  ingested_at: string;
}

export interface ChunkRecord {
  chunk_id: string;
  doc_slug: string;
  text: string;
  page_number: number;
  chunk_index: number;
  char_count: number;
  content_hash: string;
  security_level: number;
  security_label: string;
  domain: string;
  created_at: string | null;
}

export interface DocumentDetail extends DocumentSummary {
  sample_chunks: ChunkRecord[];
}

export interface ChunkPage {
  items: ChunkRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface SyncResult {
  status: string;
  documents_written: number;
  chunks_written: number;
  message: string | null;
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res
      .json()
      .catch(() => ({ detail: `API error: ${res.status}` }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function fetchDocuments(): Promise<DocumentSummary[]> {
  const res = await fetch(`${API_URL}/api/documents`, { cache: "no-store" });
  return jsonOrThrow<DocumentSummary[]>(res);
}

export async function fetchDocument(slug: string): Promise<DocumentDetail> {
  const res = await fetch(`${API_URL}/api/documents/${slug}`, { cache: "no-store" });
  return jsonOrThrow<DocumentDetail>(res);
}

export async function fetchDocumentChunks(
  slug: string,
  opts: { limit?: number; offset?: number } = {},
): Promise<ChunkPage> {
  const params = new URLSearchParams();
  params.set("limit", String(opts.limit ?? 50));
  params.set("offset", String(opts.offset ?? 0));
  const res = await fetch(
    `${API_URL}/api/documents/${slug}/chunks?${params.toString()}`,
    { cache: "no-store" },
  );
  return jsonOrThrow<ChunkPage>(res);
}

export async function syncDocumentsToDb(): Promise<SyncResult> {
  const res = await fetch(`${API_URL}/api/documents/sync`, { method: "POST" });
  return jsonOrThrow<SyncResult>(res);
}

// ---------- pipeline ----------

export interface PipelineStage {
  id: string;
  label: string;
  description: string;
  role: string;
  model: string | null;
  color: string;
  runs_locally: boolean;
}

export interface PipelineEdge {
  source: string;
  target: string;
}

export interface PipelineArchitecture {
  stages: PipelineStage[];
  edges: PipelineEdge[];
}

export interface PipelineCandidate {
  chunk_id: string;
  doc_name: string;
  doc_slug: string;
  page_number: number;
  security_level: number;
  security_label: string;
  score: number;
  text_preview: string;
  retrieval_method?: string | null;
}

export interface PipelineTraceRequest {
  query: string;
  mode?: Mode;
  role?: Role;
  top_k?: number;
  run_llm?: boolean;
}

export interface PipelineTrace {
  query: string;
  mode: string;
  role: string | null;
  stages: {
    query: { text: string };
    route?: {
      route: QueryRoute;
      confidence: string;
      reason: string;
      signals: Record<string, unknown>;
      elapsed_ms: number;
    };
    sql_gen?: {
      used: boolean;
      route: QueryRoute | null;
      elapsed_ms: number;
      sql: string | null;
      error: string | null;
      attempts?: { sql: string; error: string | null }[];
    };
    sql_exec?: {
      used: boolean;
      elapsed_ms: number;
      columns: string[];
      rows: Record<string, unknown>[];
      row_count: number;
      truncated: boolean;
      error: string | null;
    };
    embed: { model: string; device: string; vector_dim: number; elapsed_ms: number };
    dense: { model: string; candidates: PipelineCandidate[]; elapsed_ms: number; security_filtered: boolean };
    bm25: { model: string; candidates: PipelineCandidate[]; elapsed_ms: number; security_filtered: boolean };
    rrf: { k: number; candidates: PipelineCandidate[]; elapsed_ms: number; overlap_count: number };
    rerank: { model: string; device: string; candidates: PipelineCandidate[]; elapsed_ms: number };
    final: { top_k: PipelineCandidate[]; count: number };
    llm: { used: boolean; model: string | null; answer: string; prompt_chars: number; elapsed_ms: number };
    security?: {
      active: boolean;
      role: string | null;
      clearance: number | null;
      allowed_chunk_count: number | null;
      restricted_probe: { count: number; top_cosine: number } | null;
    };
  };
  stats: RetrievalStats;
  total_elapsed_ms: number;
  access_denied: boolean;
  access_denied_message: string | null;
}

export async function fetchPipelineArchitecture(): Promise<PipelineArchitecture> {
  const res = await fetch(`${API_URL}/api/pipeline/architecture`, { cache: "no-store" });
  return jsonOrThrow<PipelineArchitecture>(res);
}

export async function tracePipeline(payload: PipelineTraceRequest): Promise<PipelineTrace> {
  const res = await fetch(`${API_URL}/api/pipeline/trace`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return jsonOrThrow<PipelineTrace>(res);
}
