# Running TechNova RAG

Quick reference for starting and stopping the project locally.

## First-time setup

Already done on this machine. Skip to [Daily startup](#daily-startup) unless you're on a fresh clone.

```bash
cd /Users/viditkbhatnagar/codes/technova-rag

# 1. Qdrant
docker compose up -d qdrant

# 2. Python backend
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
python -m spacy download en_core_web_sm

# 3. Env file (add OPENAI_API_KEY here, optional)
cp .env.example backend/.env

# 4. Backend (in this terminal)
uvicorn backend.main:app --reload --port 8000

# 5. First ingest — new terminal, ~1–3 min
curl -X POST http://localhost:8000/api/ingest \
  -H 'content-type: application/json' -d '{}'

# 6. Frontend — new terminal
cd frontend
npm install
npm run dev
```

## Daily startup

Three terminals, all in `/Users/viditkbhatnagar/codes/technova-rag`.

### Terminal 1 — Qdrant
```bash
docker compose up -d qdrant
```

### Terminal 2 — Backend
```bash
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```
Wait for `[startup] ready.`

### Terminal 3 — Frontend
```bash
cd frontend
npm run dev
```

Open **http://localhost:3000**.

## Shutdown

- `Ctrl+C` in the backend and frontend terminals.
- Stop Qdrant to free RAM: `docker compose stop qdrant` (data persists).

## Verify everything works

```bash
curl http://localhost:8000/api/status
```

Expect:
- `qdrant_connected: true`
- `collection_exists: true`
- `points_count: 121` (or more if you added docs)
- `llm_configured: true` (false if OPENAI_API_KEY is blank — pipeline still runs, just no generated answer)
- `embedding_device: "mps"` on Apple Silicon

## Smoke tests

| URL | What to try |
|-----|-------------|
| `/project-a` | "What is TechNova's leave policy?" → answer with citations |
| `/project-b` (role `employee`) | "What is the CEO's salary?" → access-denied |
| `/project-b` (role `admin`) | Same question → answers from Salary Structure / Board Minutes |
| `/knowledge-graph` | 3D graph renders (heaviest page, give it a few seconds) |

## What you do NOT need to repeat

- `python3 -m venv venv` — venv exists
- `pip install -r backend/requirements.txt` — installed
- `python -m spacy download en_core_web_sm` — downloaded
- `npm install` in `frontend/` — node_modules exists
- `/api/ingest` — Qdrant volume + `backend/bm25_index.pkl` persist

## When to re-ingest

Only if you:
- Add / remove / rename PDFs in [docs/](docs/)
- Edit `DOCUMENT_METADATA` in [backend/config.py](backend/config.py)
- Change `CHUNK_SIZE`, `CHUNK_OVERLAP`, or `EMBEDDING_MODEL` in [backend/.env](backend/.env)

Then:
```bash
curl -X POST http://localhost:8000/api/ingest \
  -H 'content-type: application/json' -d '{"force_reingest": true}'
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `qdrant_connected: false` | `docker compose up -d qdrant` |
| `llm_configured: false` | Add `OPENAI_API_KEY=sk-...` to [backend/.env](backend/.env), restart uvicorn |
| `points_count: 0` | Run `/api/ingest` (see above) |
| `404 No documents ingested` on `/api/query` | Same — run `/api/ingest` first |
| Frontend can't reach backend | Backend not running on `:8000`, or `NEXT_PUBLIC_API_URL` in `frontend/.env.local` is wrong |
| MPS not used | You're inside Docker. Run the backend natively (Terminal 2 above), not via `docker compose up backend` |
| First query is slow | Models load lazily on first call after startup; subsequent queries are fast |

## Optional — one-liner alias

Add to `~/.zshrc`:
```bash
alias technova='cd /Users/viditkbhatnagar/codes/technova-rag && docker compose up -d qdrant && source venv/bin/activate && uvicorn backend.main:app --reload --port 8000'
```
Then `technova` in one terminal and `cd /Users/viditkbhatnagar/codes/technova-rag/frontend && npm run dev` in another.
