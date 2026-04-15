# technova-RAG

Multi-document RAG platform for TechNova Inc. — open RAG, role-based secure RAG, and a 3D knowledge graph explorer.

## Stack
- **Backend:** FastAPI + Python 3.12
- **Vector DB:** Qdrant (Docker)
- **Embeddings:** BAAI/bge-base-en-v1.5 (768-dim, MPS/CPU)
- **Retrieval:** Dense + BM25 + RRF fusion + ms-marco-MiniLM-L-6-v2 cross-encoder reranking
- **LLM:** OpenAI gpt-4o-mini (last-mile only; pipeline runs without an API key)
- **Frontend:** Next.js + Tailwind + shadcn/ui (Phase 3)

## Quick start

```bash
docker compose up -d                               # Qdrant on :6333
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example backend/.env                       # add your OPENAI_API_KEY (optional)
uvicorn backend.main:app --reload --port 8000
curl -X POST http://localhost:8000/api/ingest -H 'content-type: application/json' -d '{}'
```

## Endpoints
- `POST /api/ingest` — chunk, embed, store all PDFs in `docs/`
- `POST /api/query` — hybrid retrieval, with `mode: open | secure` and `role: employee | manager | admin`
- `GET /api/graph` — knowledge graph (nodes + edges)
- `GET /api/status` — health + collection stats

See `API_CONTRACT.md` for request/response schemas and `MASTER_CONTEXT.md` for architecture.
