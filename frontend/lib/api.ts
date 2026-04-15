const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Mode = "open" | "secure";
export type Role = "employee" | "manager" | "admin";

export interface QueryRequest {
  query: string;
  mode: Mode;
  role?: Role;
  top_k?: number;
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

export interface QueryResponse {
  answer: string;
  sources: ChunkResult[];
  prompt_assembled: string;
  retrieval_stats: RetrievalStats;
  access_denied: boolean;
  access_denied_message: string | null;
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
