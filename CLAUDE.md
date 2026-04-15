# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

TechNova RAG — a multi-document RAG platform over 11 fixed internal PDFs in [docs/](docs/). Two product surfaces share one pipeline: **Project A** (open chat over all docs) and **Project B** (role-gated secure chat). A third surface is an interactive 3D knowledge graph.

See [MASTER_CONTEXT.md](MASTER_CONTEXT.md), [API_CONTRACT.md](API_CONTRACT.md), and [CONVENTIONS.md](CONVENTIONS.md) for deep design/contract/style detail — prefer those over re-deriving.

## Common commands

### Backend (FastAPI, Python 3.12)
```bash
# Recommended: Qdrant in Docker, backend native (MPS acceleration on Apple Silicon)
docker compose up -d qdrant
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
python -m spacy download en_core_web_sm

uvicorn backend.main:app --reload --port 8000

# Ingest must be run once before /api/query will work:
curl -X POST http://localhost:8000/api/ingest -H 'content-type: application/json' -d '{}'
# Force full re-ingest (drops Qdrant collection + rebuilds BM25 + graph):
curl -X POST http://localhost:8000/api/ingest -H 'content-type: application/json' -d '{"force_reingest": true}'

# Full stack in Docker (no MPS):
docker compose up -d
```
Env is read from `./.env` or `backend/.env` (see [.env.example](.env.example)). `OPENAI_API_KEY` is optional — without it, `/api/query` returns the assembled prompt + retrieved chunks and the graph falls back to co-occurrence edges. There is no test suite.

### Frontend (Next.js 16 + React 19)
```bash
cd frontend
npm install
npm run dev     # http://localhost:3000
npm run build
npm run lint    # eslint
```
Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` (defaults to `http://localhost:8000`).

**Important — Next.js version**: [frontend/AGENTS.md](frontend/AGENTS.md) flags that this repo is on Next.js 16 with breaking changes vs. training data; consult `node_modules/next/dist/docs/` before writing frontend code.

## Architecture

### Backend layout
- [backend/main.py](backend/main.py) — FastAPI app; a `lifespan` context loads shared singletons into `app.state`: `embedder`, `store`, `bm25`, `retriever`, `graph_data`. Routers pull these via `request.app.state` — do not instantiate models per-request.
- [backend/config.py](backend/config.py) — `Settings` (pydantic-settings), plus three critical constants that are the single source of truth for the access model: `SECURITY_LEVELS`, `ROLE_CLEARANCE`, and `DOCUMENT_METADATA` (filename → doc_slug/domain/security). Ingestion skips any PDF not in `DOCUMENT_METADATA`.
- [backend/routers/](backend/routers/) — `ingest.py`, `query.py`, `status.py`, `graph.py`. Thin; real work lives in services.
- [backend/services/](backend/services/) — `loader` (pypdf), `chunker` (langchain splitter, 500/100), `embedder` (BGE via sentence-transformers on MPS/CPU), `store` (Qdrant wrapper with payload-indexed fields), `bm25_index` (rank_bm25, pickled to `backend/bm25_index.pkl`), `retriever` (see below), `security` (role filter + self-correcting loop), `generator` (OpenAI prompt assembly), `graph_builder` (spaCy NER + entity graph).
- [backend/models.py](backend/models.py) — all Pydantic request/response schemas.

### Retrieval pipeline
`Query → (optional role pre-filter) → Dense (BGE+Qdrant) + BM25 → RRF fusion (k=60) → Cross-Encoder rerank → top-5 → prompt → gpt-4o-mini`.
Implemented in [backend/services/retriever.py](backend/services/retriever.py) (`HybridRetriever.retrieve`). RRF is `1/(k+rank+1)`; dense-only hits become `retrieval_method=dense`, BM25-only become `bm25`, overlaps become `hybrid` — frontend depends on these exact strings.

### Security model (Project B)
[backend/services/security.py](backend/services/security.py) implements two mechanisms that must stay in sync:
1. **Pre-filter at both stages**: `get_security_filter(role)` on Qdrant dense search, and `get_allowed_chunk_ids(role)` (from `store.scroll_all`) passed into BM25. Restricted chunks never enter the scoring pool — this is the core invariant of Project B.
2. **Self-correcting retrieve** (`self_correcting_retrieve`): if top-1 rerank is weak, re-runs with synonym expansion (`_SYNONYMS`) and wider `top_k_retrieval`. Separately probes the restricted space (informational only, never returned) to decide whether to surface an access-denied message when accessible retrieval is weak but a strong restricted match exists. Thresholds: `weak_top1_threshold=0.0`, `restricted_cosine_threshold=0.55`.

### Chunk payload contract
Every Qdrant point carries the payload in [CONVENTIONS.md](CONVENTIONS.md) ("Metadata Schema"). `chunk_id` format is `{org}_{doc_slug}_c{index}` and is used as a stable key across Qdrant, BM25, and the knowledge graph. Changing the schema requires re-ingest.

### Frontend layout
App Router pages in [frontend/app/](frontend/app/): `/` (landing), `/project-a` (open chat), `/project-b` (secure chat with role selector), `/knowledge-graph` (3D force-directed via `react-force-graph-3d`). All backend calls go through [frontend/lib/api.ts](frontend/lib/api.ts); shared types live in [frontend/lib/types.ts](frontend/lib/types.ts) and must mirror `backend/models.py`.

## Conventions that bite

- **CORS** is pinned to `http://localhost:3000` + `*.vercel.app` in [backend/main.py](backend/main.py); add any new origin there.
- **Singletons on `app.state`** — embedder/reranker/Qdrant client are loaded once at startup. Reusing them from `request.app.state` (not re-instantiating) is what keeps query latency acceptable.
- **MPS is unavailable inside Docker.** For Apple Silicon dev, run Qdrant in Docker but the backend natively.
- **`.env` lookup order**: `./.env` first, then `backend/.env`. Docker Compose injects its own env; don't commit a populated `.env`.
- **No test suite exists.** Do not claim "ran tests" — exercise endpoints via curl or the frontend.
- **Don't add files to `docs/` without also updating `DOCUMENT_METADATA`** — the loader will silently skip unmapped PDFs.
- Commit style: `feat:` / `fix:` / `docs:` / `refactor:` / `chore:` (see [CONVENTIONS.md](CONVENTIONS.md)).
