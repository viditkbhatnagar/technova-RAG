# API_CONTRACT.md — FastAPI ↔ Next.js Interface

> **This is the contract between backend and frontend.** Both sides must respect these schemas exactly. If you change an endpoint on one side, update this doc and the other side.

**Base URL:** `http://localhost:8000` (dev) | Set via `NEXT_PUBLIC_API_URL` (prod)

---

## POST /api/ingest

Ingest all PDFs from the `docs/` directory into Qdrant + BM25 index.

### Request
```json
{
  "docs_path": "docs/",           // Optional, defaults to "docs/"
  "force_reingest": false          // If true, drops existing collection first
}
```

### Response (200)
```json
{
  "status": "success",
  "documents_processed": 11,
  "total_chunks": 247,
  "collection_name": "technova_docs",
  "details": [
    {
      "file_name": "TechNova_HR_Policy_Handbook.pdf",
      "pages": 9,
      "chunks": 42,
      "security_level": "INTERNAL"
    }
  ]
}
```

### Response (500)
```json
{
  "detail": "Qdrant connection failed. Is Docker running? Check localhost:6333"
}
```

---

## POST /api/query

The main endpoint. Handles both Project A (open) and Project B (secure) modes.

### Request
```json
{
  "query": "How many days of maternity leave am I entitled to?",
  "mode": "open",                    // "open" | "secure"
  "role": null,                      // Required when mode="secure": "employee" | "manager" | "admin"
  "top_k": 5                         // Optional, default 5
}
```

### Response (200) — Successful retrieval
```json
{
  "answer": "Female employees who have completed at least 80 days of service are entitled to 26 weeks (182 days) of paid maternity leave for the first two surviving children. For employees with two or more surviving children, the entitlement is 12 weeks (84 days). [Source 1]",
  "sources": [
    {
      "chunk_id": "technova_hr_handbook_c005",
      "text": "Female employees who have completed at least 80 days of service in the 12 months preceding...",
      "score": 0.892,
      "doc_name": "TechNova HR Policy Handbook",
      "page_number": 3,
      "security_level": 1,
      "retrieval_method": "hybrid"
    },
    {
      "chunk_id": "technova_hr_handbook_c006",
      "text": "Maternity leave may be taken up to 8 weeks before the expected date of delivery...",
      "score": 0.847,
      "doc_name": "TechNova HR Policy Handbook",
      "page_number": 3,
      "security_level": 1,
      "retrieval_method": "dense"
    }
  ],
  "prompt_assembled": "SYSTEM INSTRUCTION:\nYou are a helpful assistant for TechNova Inc...\n\nCONTEXT:\n[Source 1]...\n\nQUESTION:\nHow many days of maternity leave...",
  "retrieval_stats": {
    "dense_results": 10,
    "bm25_results": 10,
    "rrf_merged": 10,
    "reranked_final": 5,
    "overlap_count": 3,
    "avg_rerank_score": 0.72,
    "retrieval_time_ms": 145,
    "mode": "open",
    "role": null
  },
  "access_denied": false,
  "access_denied_message": null
}
```

### Response (200) — Access Denied (Project B, restricted content)
```json
{
  "answer": "I don't have access to salary band information at your current clearance level. This information is classified as RESTRICTED. Please contact your HR department or request elevated access.",
  "sources": [],
  "prompt_assembled": "",
  "retrieval_stats": {
    "dense_results": 0,
    "bm25_results": 0,
    "rrf_merged": 0,
    "reranked_final": 0,
    "overlap_count": 0,
    "avg_rerank_score": 0.0,
    "retrieval_time_ms": 23,
    "mode": "secure",
    "role": "employee",
    "restricted_docs_exist": true,
    "restricted_doc_count": 1
  },
  "access_denied": true,
  "access_denied_message": "Relevant information exists in 1 document(s) that require higher clearance. Contact your department head for access."
}
```

### Response (400)
```json
{
  "detail": "Role is required when mode is 'secure'. Use 'employee', 'manager', or 'admin'."
}
```

### Response (404)
```json
{
  "detail": "No documents ingested. Call POST /api/ingest first."
}
```

---

## GET /api/graph

Returns the full knowledge graph structure for 3D visualization.

### Response (200)
```json
{
  "nodes": [
    {
      "id": "doc_hr_handbook",
      "label": "HR Policy Handbook",
      "type": "document",
      "security_level": 1,
      "security_label": "INTERNAL",
      "domain": "HR",
      "metadata": {
        "pages": 9,
        "chunks": 42,
        "file_name": "TechNova_HR_Policy_Handbook.pdf"
      }
    },
    {
      "id": "chunk_hr_handbook_c005",
      "label": "Maternity Leave Policy",
      "type": "chunk",
      "parent_doc": "doc_hr_handbook",
      "page_number": 3,
      "text_preview": "Female employees who have completed at least 80 days..."
    },
    {
      "id": "entity_maternity_leave",
      "label": "Maternity Leave",
      "type": "entity",
      "entity_type": "POLICY",
      "mentions": 4
    },
    {
      "id": "entity_26_weeks",
      "label": "26 weeks",
      "type": "entity",
      "entity_type": "DURATION"
    }
  ],
  "edges": [
    {
      "source": "doc_hr_handbook",
      "target": "chunk_hr_handbook_c005",
      "type": "contains",
      "label": "contains"
    },
    {
      "source": "chunk_hr_handbook_c005",
      "target": "entity_maternity_leave",
      "type": "mentions",
      "label": "mentions"
    },
    {
      "source": "entity_maternity_leave",
      "target": "entity_26_weeks",
      "type": "has_duration",
      "label": "entitles"
    }
  ],
  "stats": {
    "total_documents": 11,
    "total_chunks": 247,
    "total_entities": 189,
    "total_relationships": 312,
    "entity_types": {
      "PERSON": 23,
      "ORG": 8,
      "POLICY": 34,
      "AMOUNT": 45,
      "DURATION": 28,
      "DATE": 19,
      "ROLE": 32
    }
  }
}
```

---

## GET /api/status

Health check and collection stats.

### Response (200)
```json
{
  "status": "healthy",
  "qdrant_connected": true,
  "collection_exists": true,
  "collection_stats": {
    "name": "technova_docs",
    "vectors_count": 247,
    "points_count": 247,
    "segments_count": 4
  },
  "bm25_index_loaded": true,
  "embedding_model": "BAAI/bge-base-en-v1.5",
  "embedding_device": "mps",
  "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
  "llm_configured": true,
  "documents_ingested": 11
}
```

### Response (200) — Not initialized
```json
{
  "status": "not_initialized",
  "qdrant_connected": true,
  "collection_exists": false,
  "message": "No documents ingested. Call POST /api/ingest to initialize."
}
```

### Response (503)
```json
{
  "status": "unhealthy",
  "qdrant_connected": false,
  "message": "Cannot connect to Qdrant. Ensure Docker is running: docker run -d --name qdrant -p 6333:6333 qdrant/qdrant"
}
```

---

## CORS Configuration

Backend must allow frontend origin:

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Error Code Summary

| Code | Meaning | When |
|------|---------|------|
| 200 | Success | Normal response (including access_denied — it's a valid response, not an error) |
| 400 | Bad Request | Missing required field (e.g., role in secure mode) |
| 404 | Not Found | Collection doesn't exist (haven't ingested yet) |
| 500 | Server Error | Qdrant down, model loading failed, etc. |
| 503 | Service Unavailable | Qdrant unreachable |
