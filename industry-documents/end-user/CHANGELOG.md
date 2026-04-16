# Changelog

Audience: TechNova RAG administrators, integrators, and end users tracking platform changes | Version: 1.0 | Last Updated: 2026-04-16

All notable changes to TechNova RAG are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See `VERSIONING_POLICY.md` for the policy specifics, including how API, data-schema, and model changes are versioned.

## [Unreleased]

Target: v1.1.0 — operational hardening for production rollouts.

### Added
- SSO and SCIM integration per `access-and-identity/SSO_SCIM_PLAN.md`. The role will be derived from the authenticated principal rather than accepted from the request body; the existing `role` field becomes ignored under SSO-mode.
- Prometheus metrics (`rag_query_total`, `rag_query_latency_seconds`, `rag_access_denied_total`, `rag_ingest_duration_seconds`) exposed on `/metrics`.
- OpenTelemetry traces covering the retrieval pipeline: role filter, dense search, BM25, RRF fusion, reranker, prompt assembly, and generator call. Spans export to the configured OTLP collector.
- Automated evaluation harness: nightly run against a golden query set, per role, scored on retrieval recall@5 and answer-similarity to reference. Results land in a weekly report.
- Audit log table (`audit_events`) in Postgres capturing classification changes, role assignments, session deletions, and ingest triggers, with actor, IP, and timestamp.

### Changed
- API routes begin the migration to URL-versioned paths. `/api/v1/*` becomes canonical; unversioned `/api/*` routes alias to `/api/v1/*` for 90 days.

### Deprecated
- Unversioned `/api/*` routes. Sunset date will be set in the v1.1.0 release notes.
- Accepting `role` in the `/api/query` body when SSO-mode is enabled.

## [1.0.0] — 2026-04-15

First general-availability release. Corpus mirror to Postgres, full documents browser, and the 3D pipeline visualizer round out the product surfaces for production pilots.

### Added
- Corpus mirror to Postgres. Ingest now writes `documents` and `chunks` tables alongside the Qdrant vector store and the BM25 pickle, giving admins a SQL-queryable view of the corpus.
- `/documents` corpus browser in the frontend. Lists every ingested document with its security label, chunk count, and ingest timestamp. Clicking a document paginates through chunks.
- `GET /api/documents`, `GET /api/documents/{slug}`, and `GET /api/documents/{slug}/chunks` endpoints. Require `DATABASE_URL`; return 503 when unset.
- `/pipeline` 3D retrieval visualizer. `GET /api/pipeline/architecture` returns the static pipeline topology; `POST /api/pipeline/trace` runs a query and returns per-stage timings and hit lists for the animation.
- Onboarding documentation: `CLAUDE.md` and `RUNNING.md` at the repository root.

### Changed
- Frontend navigation updated to expose `/documents` and `/pipeline`.
- Ingest response payload now includes `documents_mirrored` and `chunks_mirrored` counts when `DATABASE_URL` is set.

### Security
- Documents browser honours the role-based access model. Users only see documents and chunks whose `security_level <= role_clearance`.

## [0.5.0] — 2026-04-05

Chat history persistence.

### Added
- Neon Postgres persistence for chat history. Every user turn and assistant response is written to the `sessions` and `messages` tables with retrieved chunk IDs.
- Sessions sidebar in the frontend. Lists recent sessions, supports resuming a past session with full context, and exposes a delete action.
- `GET /api/sessions`, `GET /api/sessions/{id}`, and `DELETE /api/sessions/{id}` endpoints. Require `DATABASE_URL`.
- `session_id` field on `POST /api/query`. When provided, the response is persisted under that session; when absent, a fresh session is created server-side and returned.

### Changed
- Frontend chat components now store messages against a session ID rather than in-memory only.

## [0.4.0] — 2026-03-22

Phase 4: integration, Dockerisation, and the access-denied refinement.

### Added
- Full-stack Docker Compose (`qdrant` + `backend` + `frontend`). One-command start for environments without MPS requirements.
- Backend `Dockerfile` with the spaCy model baked in to avoid runtime downloads.
- `architecture-and-ops/` reference documentation for production topologies.

### Changed
- Self-correcting retrieval loop now decides access-denied by comparing the best accessible-space rerank score against the best restricted-space cosine. Thresholds: `weak_top1_threshold=0.0`, `restricted_cosine_threshold=0.55`. Prevents false-positive access-denied responses when accessible retrieval is genuinely strong.

### Fixed
- Bumped `openai>=1.55.3` for compatibility with `httpx` 0.28. Previously pinned versions failed on fresh installs.

## [0.3.0] — 2026-03-08

Phase 3: Next.js frontend.

### Added
- Next.js 16 + React 19 frontend with App Router pages.
- `/` landing page with product overview and entry points.
- `/project-a` open chat surface.
- `/project-b` secure chat with role selector (employee / manager / admin).
- `/knowledge-graph` 3D force-directed visualizer via `react-force-graph-3d`. Nodes are entities; edges are chunk co-occurrences.
- Retrieved-sources panel showing the chunks that fed each answer, with `hybrid` / `dense` / `bm25` method tags.
- Shared API client in `frontend/lib/api.ts` and shared types in `frontend/lib/types.ts`, mirroring `backend/models.py`.

### Changed
- CORS configuration on the backend now allows `http://localhost:3000` and `*.vercel.app`.

### Fixed
- Retrieved-sources panel now scrolls when results exceed the viewport; previously clipped on shorter screens.
- Edge click in the 3D graph now shows relationship info: the two entities, the source document, and the chunk that justifies the edge.

## [0.2.0] — 2026-03-01

Phase 2: knowledge graph.

### Added
- Knowledge graph builder. spaCy NER extracts entities from every chunk; edges are computed from chunk co-occurrence with a configurable minimum shared-chunk threshold.
- `GET /api/graph` endpoint returning nodes and edges with their source-chunk provenance.
- Graph persistence to `backend/graph_data.json` so `/api/graph` survives backend restarts without re-running NER.

### Changed
- Ingest pipeline now builds the graph as a final step after chunking and embedding.

### Fixed
- Graph no longer rebuilds on every backend start; the cached JSON is loaded into `app.state.graph_data`.

## [0.1.0] — 2026-02-26

Phase 1: initial backend release. Retrieval-ready, no UI.

### Added
- FastAPI backend with a `lifespan` context loading the BGE embedder, the Qdrant client, the BM25 pickle (if present), the graph JSON (if present), and the retriever singleton onto `app.state`.
- Hybrid retrieval pipeline: dense (BGE + Qdrant) + BM25 (rank_bm25), fused with Reciprocal Rank Fusion (k=60), reranked with a cross-encoder, top-5 chunks passed to `gpt-4o-mini` for generation.
- Security pre-filter at both retrieval stages. Qdrant uses a payload filter on `security_level`; BM25 is scored only over allowed chunk IDs sourced from `store.scroll_all`. Restricted chunks never enter the scoring pool.
- Role model with three roles (`employee`, `manager`, `admin`) and four classification levels (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`).
- `POST /api/ingest` — PDF load, chunking (500 chars / 100 overlap), embedding, Qdrant upsert, BM25 build. Accepts `{"force_reingest": bool}`.
- `POST /api/query` — runs the retrieval pipeline and returns the answer, retrieved chunks, and method tags. Accepts `{"query", "mode": "open"|"secure", "role"?, "session_id"?}`. Returns the assembled prompt and chunks if `OPENAI_API_KEY` is unset (graceful degrade).
- `GET /api/status` — ingest state, chunk count, graph stats.
- `DOCUMENT_METADATA` in `backend/config.py` as the single source of truth for which PDFs are ingested and at what classification.
- Payload schema convention: `chunk_id = {org}_{doc_slug}_c{index}`, stable across Qdrant, BM25, and the knowledge graph.

## Release notes cross-reference

| Version | Date | Notes |
|---|---|---|
| Unreleased (v1.1.0) | TBD | SSO/SCIM, observability, eval harness, audit log |
| 1.0.0 | 2026-04-15 | Corpus mirror, `/documents`, `/pipeline` |
| 0.5.0 | 2026-04-05 | Chat history persistence |
| 0.4.0 | 2026-03-22 | Docker Compose, Dockerfile, access-denied fix |
| 0.3.0 | 2026-03-08 | Next.js frontend |
| 0.2.0 | 2026-03-01 | Knowledge graph |
| 0.1.0 | 2026-02-26 | Initial backend |

## Revision history

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Documentation | Initial release |
