# TechNova RAG Administrator Guide

Audience: Platform administrators, DevOps, and Solutions Engineers operating TechNova RAG | Version: 1.0 | Last Updated: 2026-04-16

This guide walks you through installing, configuring, and operating TechNova RAG — the multi-document RAG platform that answers questions over the 11 fixed internal PDFs in `docs/`. It covers the first install, day-two operations (ingest, role management, chat history, backups), and the most common failure modes.

If you are new to the codebase, read this front-to-back. If you are only here to fix something, jump to the **Troubleshooting** section.

## 1. Audience and prerequisites

You are expected to be comfortable with:

- A POSIX shell (macOS Terminal, Linux bash, or zsh).
- Docker Desktop or Docker Engine 24+.
- Python 3.12 and `venv`.
- Node.js 20+ and npm (for the frontend).
- Basic familiarity with FastAPI, Qdrant, and Postgres.

You will need:

| Requirement | Why |
|---|---|
| Shell access to the host | Running the backend and managing the venv |
| Docker + Docker Compose | Runs Qdrant (and optionally the full stack) |
| `OPENAI_API_KEY` | Optional — without it `/api/query` returns the assembled prompt and retrieved chunks but no generated answer |
| `DATABASE_URL` (Neon Postgres recommended) | Optional — enables chat history, the `/documents` corpus browser, and session resume |
| Network egress to `api.openai.com` | Only required if you set `OPENAI_API_KEY` |

TechNova RAG runs fine on a developer laptop (Apple Silicon uses Metal Performance Shaders for embeddings) and on a single Linux VM for pilots. Anything beyond a pilot should follow the production runbook in `architecture-and-ops/`.

## 2. Initial setup

The recommended developer topology runs **Qdrant in Docker** and the **backend natively**, because MPS acceleration is not available inside Docker on Apple Silicon. For production, use full Docker Compose.

### 2.1 Clone and configure

```bash
git clone <your-fork-url> technova-rag
cd technova-rag
cp .env.example .env
```

Open `.env` and set at least:

```bash
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=sk-...           # optional
DATABASE_URL=postgres://...     # optional, enables history + /documents
```

The backend reads `./.env` first, then `backend/.env`. Do not commit a populated `.env` — Docker Compose injects its own env at runtime.

### 2.2 Start Qdrant

```bash
docker compose up -d qdrant
```

Qdrant now listens on `localhost:6333`. Verify with `curl http://localhost:6333/readyz`.

### 2.3 Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
python -m spacy download en_core_web_sm
```

The spaCy model powers the knowledge-graph NER pipeline. Skipping it will fail graph construction at ingest time.

### 2.4 Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

On first boot you should see the shared singletons load: the BGE embedder, the cross-encoder reranker, the Qdrant client, and (if present) the BM25 pickle and graph JSON. Watch for lines like `"loaded bm25 index"` and `"loaded graph data"`. On a fresh install they will be absent until you run ingest.

### 2.5 Start the frontend

```bash
cd frontend
cp .env.local.example .env.local  # if present; otherwise create it
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm install
npm run dev
```

The UI is now at `http://localhost:3000`.

### 2.6 Full Docker alternative

```bash
docker compose up -d
```

This brings up Qdrant + backend + frontend together. You lose MPS acceleration, so ingest and query latency will be higher on Apple Silicon, but the topology is closer to production.

## 3. First ingest

The backend refuses to answer queries until ingest has run at least once. Trigger it explicitly:

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H 'content-type: application/json' \
  -d '{}'
```

Expected response shape:

```json
{
  "status": "ok",
  "documents_ingested": 11,
  "chunks_created": 742,
  "graph_nodes": 389,
  "graph_edges": 1104,
  "duration_seconds": 42.7
}
```

On a modern laptop, expect **30–60 seconds for the full 11-document corpus**. The pipeline:

1. Reads each PDF in `docs/` that matches `DOCUMENT_METADATA` in `backend/config.py`.
2. Splits each document into 500-character chunks with 100-character overlap.
3. Embeds chunks with the BGE model (MPS on Apple Silicon, CPU elsewhere).
4. Upserts into Qdrant collection `technova_docs` with payload-indexed fields for role filtering.
5. Builds the BM25 index and pickles it to `backend/bm25_index.pkl`.
6. Runs spaCy NER on every chunk, computes co-occurrence edges, and writes `backend/graph_data.json`.
7. Mirrors documents and chunks to Postgres if `DATABASE_URL` is set.

To force a full rebuild (drop the Qdrant collection, rebuild BM25 and graph):

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H 'content-type: application/json' \
  -d '{"force_reingest": true}'
```

Re-ingest is required any time you change `DOCUMENT_METADATA`, chunk size, embedder, or the chunk payload schema.

## 4. Verifying a healthy install

Run these four checks in order. All four should pass before you hand the environment to users.

### 4.1 Status endpoint

```bash
curl http://localhost:8000/api/status
```

You want `ingest_complete: true`, a non-zero `chunk_count`, and `graph.nodes > 0`.

### 4.2 Project A test query

Open `http://localhost:3000/project-a`, ask *"What is TechNova's PTO policy?"*, and confirm you get an answer with at least one citation linking back to `TechNova_HR_Policy_Handbook.pdf`. The retrieved-sources panel should show chunks tagged `hybrid`, `dense`, or `bm25`.

### 4.3 Knowledge graph

Open `http://localhost:3000/knowledge-graph`. The 3D force-directed graph should render within a second or two. Click a node; the side panel should show the entity label and the chunks it appears in. Click an edge; the relationship source chunk should appear.

### 4.4 Documents browser (only if `DATABASE_URL` is set)

Open `http://localhost:3000/documents`. You should see all 11 documents listed with their security label. Click one and page through chunks. If this page 503s, `DATABASE_URL` is unset or the Postgres mirror did not run during ingest.

## 5. Configuring the corpus

The single source of truth for which PDFs are ingested is `DOCUMENT_METADATA` in `backend/config.py`. Each entry declares:

| Field | Example | Purpose |
|---|---|---|
| `doc_name` | `TechNova_HR_Policy_Handbook.pdf` | Exact filename in `docs/` |
| `doc_slug` | `hr-policy-handbook` | Stable URL-safe identifier used in `chunk_id` |
| `domain` | `hr` | Coarse topic grouping used by the graph |
| `security_level` | `1` | Integer 0–3; gates access |
| `security_label` | `INTERNAL` | Human-readable label shown in the UI |

> **Warning:** the loader silently skips any PDF in `docs/` that is not listed in `DOCUMENT_METADATA`. If your new document "does not show up," this is almost certainly why.

To add a document:

1. Drop the PDF in `docs/`.
2. Add an entry to `DOCUMENT_METADATA` with a unique `doc_slug`.
3. Run `POST /api/ingest` with `force_reingest: true`.
4. Confirm the new document appears in `/documents` and in `/api/status`.

Changing the `doc_slug` of an existing document is a breaking change — it invalidates every `chunk_id` and every stored citation. Avoid it after go-live.

## 6. Managing classifications

TechNova RAG ships with four access levels and three roles:

| Level | Label | Clearance required |
|---|---|---|
| 0 | PUBLIC | employee (1), manager (2), admin (3) |
| 1 | INTERNAL | employee, manager, admin |
| 2 | CONFIDENTIAL | manager, admin |
| 3 | RESTRICTED | admin |

A role sees every chunk whose `security_level <= role_clearance`. The pre-filter is applied at both the dense (Qdrant payload filter) and BM25 (allowed-id list) stages, so restricted content cannot leak into the scoring pool.

Changing a classification is a governance action, not a technical one. Use the approval workflow below for any change:

1. **Request**: the document owner files a request (ticket or email) citing the proposed change and business justification.
2. **Review**: the data-governance owner (usually CISO delegate) signs off.
3. **Apply**: an admin updates `security_level` and `security_label` in `DOCUMENT_METADATA` and merges the change via PR.
4. **Re-ingest**: run `POST /api/ingest` with `force_reingest: true`. Old chunks inherit the new level because payload is rewritten.
5. **Audit**: record the change in the data-governance log. The v1.1 audit-log table (see CHANGELOG) will automate this.

## 7. Role management

Version 1.0 is **demo-grade for auth**: the role is passed in the request body at `/api/query` (`role: "employee" | "manager" | "admin"`). There is no login; the frontend's Project B role selector is a trust-the-client switch.

This is deliberate for the pilot phase. Production deployments must front the API with SSO (Okta, Entra, or Google Workspace) using the plan in `access-and-identity/SSO_SCIM_PLAN.md`. Once SSO is in place, the role is derived from the authenticated subject and the request body field becomes ignored.

Until SSO is deployed:

- Do not expose Project B publicly.
- Keep the backend behind a VPN, SSO-proxy (e.g. Cloudflare Access), or private network.
- Treat the role selector as a UX convenience, not a security boundary.

## 8. Monitoring and logs

v1.0 logging is `print`-based and streamed to stdout. Docker Compose surfaces this via `docker compose logs -f backend`. For native runs, uvicorn writes to the terminal.

Key log lines to grep for:

| Pattern | Meaning |
|---|---|
| `"loaded bm25 index"` | BM25 pickle loaded at startup |
| `"loaded graph data"` | Knowledge graph JSON loaded |
| `"ingest complete"` | Ingest finished successfully |
| `"retrieve top_k=…"` | Per-query retrieval summary |
| `"access-denied"` | Self-correcting loop surfaced an access-denied response |

Production observability is planned for v1.1: Prometheus counters (`rag_query_total`, `rag_query_latency_seconds`, `rag_access_denied_total`), OpenTelemetry traces per retrieval stage, and structured JSON logs. Track the rollout in `CHANGELOG.md` and `architecture-and-ops/OBSERVABILITY.md`.

## 9. Chat history and sessions

When `DATABASE_URL` is set, every user turn is persisted to Postgres with the session ID, role, query, answer, and retrieved chunk IDs.

Admin operations:

```bash
# List recent sessions
curl http://localhost:8000/api/sessions

# Inspect a single session (messages + citations)
curl http://localhost:8000/api/sessions/<session_id>

# Delete a session (GDPR erasure, user self-service, etc.)
curl -X DELETE http://localhost:8000/api/sessions/<session_id>
```

Retention defaults to keeping sessions indefinitely. For production, schedule a nightly delete of sessions older than `CHAT_RETENTION_DAYS` (env var; default unset). A scheduled task is not yet bundled in v1.0 — run the delete from your orchestrator of choice (cron, Airflow, Temporal).

## 10. /documents corpus browser

Prerequisite: `DATABASE_URL` must be set and the most recent ingest must have populated the `documents` and `chunks` tables.

What it shows:

- Document list with security label, chunk count, and ingest timestamp.
- Per-document chunk view with pagination (default 50 chunks per page).
- Raw chunk text plus the payload fields used by retrieval.

Use `/documents` to:

- Spot-check that a newly added PDF actually chunked cleanly.
- Diagnose "why didn't this query hit doc X" by confirming the expected chunk text exists.
- Audit the security label on every chunk after a classification change.

If the page is empty but ingest finished, verify Postgres connectivity with `psql "$DATABASE_URL" -c 'SELECT count(*) FROM chunks;'`.

## 11. Backup and restore

TechNova RAG has three state stores. Back them up independently.

| Store | What it holds | Backup strategy |
|---|---|---|
| Qdrant (`technova_docs`) | Vector embeddings + payload | Qdrant snapshots via `POST /collections/technova_docs/snapshots` |
| Postgres (Neon or self-hosted) | Chat history, documents, chunks mirror | Neon PITR; self-hosted use `pg_dump` |
| `docs/` + `backend/config.py` | Source PDFs and metadata | Git — the corpus is version-controlled |
| `backend/bm25_index.pkl`, `backend/graph_data.json` | Derived indexes | Not backed up — rebuilt by ingest |

Restore order for a full disaster:

1. Restore git checkout (source code + corpus + metadata).
2. Restore Postgres from PITR or dump.
3. Restore Qdrant snapshot — or skip and re-ingest, which takes a minute.
4. Start the backend; ingest will pick up where it left off.

The BM25 pickle and graph JSON are deterministic outputs of ingest. Never treat them as primary state.

## 12. Troubleshooting

### MPS unavailable in Docker
Symptom: `torch.backends.mps.is_available()` returns `False` in a containerised backend on Apple Silicon.
Fix: this is expected. Either accept CPU-only performance, or run the backend natively and keep Qdrant in Docker (the recommended dev topology).

### BM25 load failure at startup
Symptom: `FileNotFoundError: backend/bm25_index.pkl` or a pickle decode error.
Fix: run `/api/ingest`. If ingest fails, delete the stale pickle manually and retry with `force_reingest: true`.

### Qdrant connection error
Symptom: `ConnectionRefusedError` or repeated `httpx.ConnectError` at startup.
Fix: confirm `docker compose ps` shows `qdrant` as healthy, and that `QDRANT_URL` in `.env` matches (`http://localhost:6333` for native backend, `http://qdrant:6333` for in-compose backend).

### OPENAI_API_KEY missing
Symptom: `/api/query` returns a response with `answer: null` and `prompt: "..."` plus chunks.
Fix: this is graceful degrade, not an error. Set `OPENAI_API_KEY` in `.env` and restart the backend to enable generation. The retrieval layer continues to work either way.

### DATABASE_URL missing
Symptom: `/api/sessions` and `/api/documents` return 503 or empty lists; chat still works.
Fix: also graceful degrade. Set `DATABASE_URL` and re-ingest to populate the mirror; chat history will start persisting on the next turn.

### Access-denied surfaced for an admin role
Symptom: the admin role sees an access-denied response where it should have answered.
Fix: confirm `ROLE_CLEARANCE["admin"] == 3` in `backend/config.py` and that the queried chunks actually have `security_level <= 3`. The self-correcting loop only surfaces access-denied when restricted-space retrieval is strong (>0.55 cosine) and accessible-space retrieval is weak (top-1 < 0.0). Tuning these thresholds changes the behaviour; see `backend/services/security.py`.

### Ingest slower than 60 seconds
Symptom: ingest takes 3+ minutes on a laptop.
Fix: confirm MPS acceleration is active (native backend, not Docker). Check logs for `"device=mps"` during embedder load.

## 13. Upgrades

Routine upgrade procedure:

```bash
git pull origin main
source venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd -
```

Then decide whether you need to re-ingest:

| Change type | Re-ingest needed? |
|---|---|
| Frontend-only changes | No |
| Router or generator changes | No |
| Chunk size, overlap, or chunker change | Yes |
| Embedder model change | Yes (full `force_reingest: true`) |
| `DOCUMENT_METADATA` edits | Yes |
| Payload schema (`chunk_id` format, added fields) | Yes, MAJOR version bump |

Always read `CHANGELOG.md` before upgrading across a MINOR or MAJOR boundary.

## 14. Reference: API endpoints

All endpoints are relative to `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

```bash
# Root status
curl http://localhost:8000/

# Ingest
curl -X POST http://localhost:8000/api/ingest -H 'content-type: application/json' -d '{}'
curl -X POST http://localhost:8000/api/ingest -H 'content-type: application/json' -d '{"force_reingest": true}'

# Query (open mode)
curl -X POST http://localhost:8000/api/query -H 'content-type: application/json' \
  -d '{"query": "What is the PTO policy?", "mode": "open"}'

# Query (secure mode with role)
curl -X POST http://localhost:8000/api/query -H 'content-type: application/json' \
  -d '{"query": "Q4 revenue?", "mode": "secure", "role": "manager", "session_id": "abc-123"}'

# Status
curl http://localhost:8000/api/status

# Knowledge graph
curl http://localhost:8000/api/graph

# Sessions (requires DATABASE_URL)
curl http://localhost:8000/api/sessions
curl http://localhost:8000/api/sessions/<id>
curl -X DELETE http://localhost:8000/api/sessions/<id>

# Documents (requires DATABASE_URL)
curl http://localhost:8000/api/documents
curl http://localhost:8000/api/documents/<slug>
curl http://localhost:8000/api/documents/<slug>/chunks?offset=0&limit=50

# Pipeline visualizer
curl http://localhost:8000/api/pipeline/architecture
curl -X POST http://localhost:8000/api/pipeline/trace -H 'content-type: application/json' \
  -d '{"query": "What is the PTO policy?", "mode": "open"}'
```

## Revision history

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Documentation | Initial release |
