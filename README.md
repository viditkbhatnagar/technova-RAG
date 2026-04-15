# TechNova RAG Platform

Multi-document RAG system with hybrid retrieval, role-based access control, and an interactive 3D knowledge graph — built for TechNova Inc.'s 11-document internal corpus.

## Features

- **Project A — Open RAG:** chat over all 11 TechNova documents. Hybrid retrieval (Dense + BM25 + RRF + Cross-Encoder reranking) with LLM-grounded answers and per-source citations.
- **Project B — Secure RAG:** same pipeline, plus role-based pre-filtering. Three roles (employee/manager/admin) see different document subsets; restricted content is never retrieved for lower clearances.
- **Knowledge Graph Explorer:** 3D force-directed view of documents, chunks, entities, and relationships across the corpus.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js (App Router) + TypeScript + Tailwind + shadcn/ui |
| Backend | FastAPI (Python 3.12) + uvicorn |
| Vector DB | Qdrant (Docker) |
| Embeddings | BAAI/bge-base-en-v1.5 (768-dim, MPS/CPU) |
| BM25 | rank_bm25 (in-memory, pickled to disk) |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| NER | spaCy `en_core_web_sm` |
| LLM | OpenAI `gpt-4o-mini` — optional; pipeline degrades gracefully without a key |

## Quick Start

### Prerequisites

- Docker Desktop (for Qdrant, and optionally the backend)
- Python 3.12+ (if running the backend natively for MPS acceleration)
- Node.js 18+
- OpenAI API key — **optional**. Without it, `/api/query` returns the assembled prompt + retrieved chunks; the graph falls back to co-occurrence edges.

### Option A — Everything in Docker

```bash
cp .env.example .env                      # optionally add OPENAI_API_KEY
docker compose up -d                      # Qdrant on :6333, backend on :8000
curl -X POST http://localhost:8000/api/ingest \
  -H 'content-type: application/json' -d '{}'

cd frontend && npm install && npm run dev # http://localhost:3000
```

### Option B — Qdrant in Docker, backend native (recommended on Apple Silicon for MPS)

```bash
docker compose up -d qdrant

python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
python -m spacy download en_core_web_sm

cp .env.example backend/.env              # optionally add OPENAI_API_KEY
uvicorn backend.main:app --reload --port 8000

curl -X POST http://localhost:8000/api/ingest \
  -H 'content-type: application/json' -d '{}'

cd frontend && npm install && npm run dev # http://localhost:3000
```

First ingest takes 1–3 minutes (downloads BGE + cross-encoder, extracts PDFs, builds BM25 + knowledge graph). Subsequent restarts reuse the persisted Qdrant collection and BM25 index.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/ingest` | Chunk, embed, store all PDFs in `docs/`; build BM25 + knowledge graph |
| `POST` | `/api/query` | Hybrid retrieval + generation; body supports `mode: open \| secure` and `role: employee \| manager \| admin` |
| `GET`  | `/api/graph` | Knowledge graph JSON (nodes + edges + stats) |
| `GET`  | `/api/status` | Qdrant connectivity, collection stats, model info, `llm_configured` |

Full request/response schemas: [API_CONTRACT.md](API_CONTRACT.md). Architecture + retrieval pipeline: [MASTER_CONTEXT.md](MASTER_CONTEXT.md).

## Document Corpus & Access Model

11 PDFs in `docs/`, each tagged with a security level:

| Level | Label | Example docs | Roles with access |
|-------|-------|--------------|-------------------|
| 0 | PUBLIC | Training & Compliance | all |
| 1 | INTERNAL | HR Handbook, IT Asset Policy, Platform Architecture, OnCall Runbook | employee, manager, admin |
| 2 | CONFIDENTIAL | Q4 Financial Report, Product Roadmap 2026, Vendor Contracts | manager, admin |
| 3 | RESTRICTED | Salary Structure, Board Minutes Q4, Security Incident Report | admin |

Project B applies the role's clearance as a Qdrant pre-filter before retrieval runs — restricted chunks are never scored for ineligible users. If a query would have matched a restricted doc, the system surfaces an access-denied message rather than leaking content.

## Retrieval Pipeline

```
Query → (optional security pre-filter) → Dense (BGE+Qdrant) → BM25 → RRF fusion
      → Cross-Encoder rerank top-10 → top-5 → prompt assembly → gpt-4o-mini
```

The pipeline runs 100 % locally; the LLM is a replaceable last mile. Without an API key the backend returns `assembled_prompt + sources` so you can still inspect retrieval quality.

## Troubleshooting

- **`/api/query` returns 404 "No documents ingested"** — call `POST /api/ingest` first.
- **`/api/status` shows `qdrant_connected: false`** — start Qdrant: `docker compose up -d qdrant`.
- **`llm_configured: false` in status** — intentional when `OPENAI_API_KEY` is blank; answers are returned as assembled prompts.
- **Slow first query** — models download on first use (~700 MB combined for BGE + cross-encoder).
- **MPS not used inside Docker** — MPS is unavailable from Linux containers. Run the backend natively (Option B) for Apple Silicon acceleration.

## Project Layout

```
technova-rag/
├── backend/              # FastAPI + retrieval pipeline
├── frontend/             # Next.js app (landing, project-a, project-b, knowledge-graph)
├── docs/                 # 11 TechNova PDFs
├── docker-compose.yml    # Qdrant + backend
├── MASTER_CONTEXT.md     # Architecture, pipeline, design principles
├── API_CONTRACT.md       # Request/response schemas
└── CONVENTIONS.md        # Coding standards
```
