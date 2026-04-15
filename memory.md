# memory.md — Project Decision Log

## Two Independent Projects: Multi-Doc Enterprise RAG Systems
**Started:** 2026-04-15
**Student:** Vidit Bhatnagar (AS24DXB001, MAIB @ SP Jain)
**Context:** Advanced Generative AI — Session 2 concepts
**⚠️ CORRECTION:** Neither project is a homework submission. These are independent projects.

---

## Current Status: 🟢 ALL DECISIONS FINALIZED → BUILDING

---

## Decision Log

### [2026-04-15] Decision #1: Single App, Two Modes (Landing Page → Project A / Project B)
- **One codebase.** Next.js frontend + FastAPI backend + Qdrant (Docker)
- **Project A — Open RAG:** No login, all 11 docs accessible, hybrid retrieval, chat interface
- **Project B — Secure RAG:** Role selector (admin/manager/employee), metadata pre-filtering, access-denied UX
- **NOT homework.** These are independent projects applying Session 2 concepts.
- **Architecture:** Landing page with two buttons → each routes to its own page within the same Next.js app, both hit the same FastAPI backend with a `mode` parameter

### [2026-04-15] Decision #2: Qdrant (Docker) — Single Instance for Both Modes
- One Qdrant container serves both Project A and Project B
- Same collection, same embeddings — the only difference is whether metadata filtering is applied at query time
- Docker Desktop confirmed available on Vidit's machine

### [2026-04-15] Decision #3: BGE-base-en-v1.5 (768-dim) with MPS Acceleration
- **Lab used:** all-MiniLM-L6-v2 (384-dim)
- **We chose:** BAAI/bge-base-en-v1.5 (768-dim)
- **Hardware:** MacBook Pro M3 — Apple Silicon MPS acceleration (not CUDA)
- **Device logic:** `device = "mps" if torch.backends.mps.is_available() else "cpu"`
- **Rationale:** Better MTEB scores; 768-dim matches Vidit's spec; MPS gives near-GPU performance on M3

### [2026-04-15] Decision #4: Single Org (TechNova), 11 Existing Docs — No New PDFs Needed
- **Corpus:** 11 TechNova docs (1 HR handbook + 10 from uploaded zip)
- **NO new PDFs to generate** — existing docs have natural 4-tier security classification already baked in
- **Distribution:** PUBLIC (1), INTERNAL (4), CONFIDENTIAL (3), RESTRICTED (3)
- **Role mapping for Project 2:**
  - `employee` → PUBLIC + INTERNAL (5 docs)
  - `manager` → PUBLIC + INTERNAL + CONFIDENTIAL (8 docs)
  - `admin` → all docs including RESTRICTED (11 docs)

### [2026-04-15] Decision #5: Retrieval Strategy — RRF + Cross-Encoder
- **Dense:** Qdrant KNN with cosine similarity
- **Sparse:** BM25Okapi from rank_bm25
- **Fusion:** Reciprocal Rank Fusion (RRF) with k=60
- **Re-ranking:** cross-encoder/ms-marco-MiniLM-L-6-v2 on top-10 candidates → top-5 final
- **Rationale:** RRF is parameter-free and proven; cross-encoder adds semantic precision without heavy cost

### [2026-04-15] Decision #6: Self-Correcting Security Loop (Project 2 only)
- Query → pre-filter by role clearance → retrieve → score check
- If avg relevance < 0.3 → expand query, increase top_k → re-retrieve
- NEVER relax security clearance (hard boundary)
- If higher-clearance docs exist for query → inform user without leaking content
- **Rationale:** Demonstrates enterprise access control — e.g., employee asking about salary bands gets "access restricted" instead of hallucinated numbers

### [2026-04-15] Decision #7: OpenAI API for LLM Generation
- **Model:** `gpt-4o-mini` — cheap, fast, great for grounded Q&A
- **SDK:** `openai` Python package (Vidit has API key ready)
- **NOT using OpenRouter** — direct OpenAI is simpler, one less dependency
- **API key:** Stored in `.env`, never committed

### [2026-04-15] Decision #8: Next.js + FastAPI (Vercel-deployable)
- **Frontend:** Next.js (React/TypeScript) — landing page → Project A page / Project B page
- **Backend:** FastAPI (Python) — all RAG logic exposed as API endpoints
- **Deployment:** Frontend on Vercel, Backend on Railway/Render, Qdrant on Docker (local) or Qdrant Cloud (prod)
- **Why not Streamlit:** Vidit wants Vercel deployment + portfolio-grade UI
- **API endpoints:**
  - `POST /api/ingest` — load + chunk + embed + store PDFs + extract entities/relationships
  - `POST /api/query` — accepts query + mode (open/secure) + role → returns response + sources
  - `GET /api/graph` — returns full knowledge graph (nodes + edges JSON) for 3D visualization
  - `GET /api/status` — collection stats, doc count, health check

### [2026-04-15] Decision #9: RAG at Scale Production Patterns (from @techwithprateek reference)
- **Adopted for both projects:** SHA-256 chunk deduplication, citation metadata per chunk [source, page, section], semantic chunking on paragraph boundaries
- **Adopted for Project 2 only:** Partitioned index by role/tenant, MMR (Max Marginal Relevance) for chunk dedup before LLM, context compression for chunks > 300 tokens, semantic query caching
- **6-layer architecture validated:** Ingestion → Embedding → Hybrid Retrieval → Reranking → Context Assembly → Caching/Observability

### [2026-04-15] Decision #10: Pipeline-First Architecture — LLM Is Last Mile Only
- **Philosophy:** The retrieval pipeline does the thinking. The LLM does the talking.
- Everything from BM25 → Dense KNN → RRF fusion → Cross-encoder reranking → Security filtering → Prompt assembly runs **100% locally, no API key**
- The OpenAI API key is used ONLY at the final generation step to convert the grounded prompt into natural language
- If you remove the API key, the system still works — you just read the assembled prompt yourself
- **Rationale:** In production orgs, you don't hand raw documents to an LLM. The pipeline retrieves, ranks, filters, deduplicates, and grounds. The LLM is a replaceable component. The retrieval pipeline IS the product.

### [2026-04-15] Decision #11: 3D Knowledge Graph Visualization (Third Landing Page Button)
- **Scope:** All 11 TechNova docs in one interconnected graph
- **4-layer depth:**
  - Layer 1: Documents (11 large nodes, colored by security classification)
  - Layer 2: Chunks (connected to parent doc)
  - Layer 3: Entities (people, departments, policies, amounts, dates — extracted via spaCy NER)
  - Layer 4: Relationships (entity → predicate → entity triples — extracted via GPT-4o-mini, one-time ingestion cost)
- **Renderer:** `react-force-graph-3d` in Next.js — interactive, zoomable, rotatable
- **Node coloring:** by type (doc = blue, chunk = gray, entity = green, relationship edge = orange)
- **Click interaction:** click any node to see its content/metadata
- **Cross-doc relationships visible:** e.g., Salary Structure ↔ Performance Review share entities like "L5", "ESOP", "Rating 4"
- **Entity extraction approach:** spaCy NER locally (free) + GPT-4o-mini for relationship triples (one-time, few cents)
- **FastAPI endpoint:** `GET /api/graph` returns full node + edge JSON for the frontend to render

---

## Change History

| Date | Change | Reason |
|------|--------|--------|
| 2026-04-15 | Created ARCHITECTURE_PLAN.md | Initial system design |
| 2026-04-15 | Created memory.md | Decision tracking |
| 2026-04-15 | **CORRECTION: Neither project is homework** | Vidit clarified both are independent projects, not homework submissions |
| 2026-04-15 | Removed MediCore Health org | No new PDFs needed — using existing 11 TechNova docs only |
| 2026-04-15 | Added RAG at Scale production patterns | Reference PDF from @techwithprateek incorporated into architecture |
| 2026-04-15 | Updated Qdrant as primary DB for Project 1 | Docker is expected; Qdrant aligns with enterprise patterns |
| 2026-04-15 | **FINAL STACK: Next.js + FastAPI + Qdrant + OpenAI** | Vidit chose Vercel-deployable stack over Streamlit |
| 2026-04-15 | Single app, two modes (Project A / Project B) | Landing page routes to open RAG or secure RAG — same backend |
| 2026-04-15 | OpenAI replaces OpenRouter | Vidit has OpenAI API key; simpler, no middleman |
| 2026-04-15 | MPS replaces CUDA | MacBook Pro M3 — Apple Silicon, no NVIDIA GPU |
| 2026-04-15 | 24-hour timeline confirmed | All decisions locked, building starts now |
| 2026-04-15 | Pipeline-first architecture adopted | LLM is last mile only; entire RAG pipeline runs locally without API key |
| 2026-04-15 | 3D Knowledge Graph added as third feature | All 11 docs, 4-layer depth (doc → chunk → entity → relationship), react-force-graph-3d |
| 2026-04-15 | Landing page now has 3 buttons | Project A (Open RAG) / Project B (Secure RAG) / Knowledge Graph |
| 2026-04-15 | Knowledge graph is VIEW-ONLY | Does NOT power retrieval for A/B; standalone exploration tool |
| 2026-04-15 | Full documentation suite generated | MASTER_CONTEXT, CONVENTIONS, API_CONTRACT, 4 Phase docs, Claude Code prompts |

---

## TODO (Implementation Order)

### Phase 1 — Backend Core (FastAPI + RAG Pipeline)
- [ ] Project structure: `backend/` (FastAPI) + `frontend/` (Next.js)
- [ ] Docker: Qdrant container running on port 6333
- [ ] PDF loader + chunker with metadata tagging (domain, classification, page)
- [ ] SHA-256 chunk deduplication
- [ ] BGE-base-en-v1.5 embedding with MPS acceleration
- [ ] Qdrant collection with 768-dim vectors + metadata payload
- [ ] BM25 index on tokenized chunks
- [ ] Hybrid retrieval: Dense + BM25 + RRF fusion
- [ ] Cross-encoder reranking (top 10 → top 5)
- [ ] Grounded prompt assembly (local, no API key)
- [ ] OpenAI gpt-4o-mini generation (last mile only)
- [ ] FastAPI endpoints: `/api/ingest`, `/api/query`, `/api/status`

### Phase 2 — Project A Mode (Open RAG, no filtering)
- [ ] `/api/query` with `mode=open` → full corpus search, no clearance filter
- [ ] Returns: LLM response + source chunks with scores + retrieval comparison (dense vs BM25)

### Phase 3 — Project B Mode (Secure RAG, role-based)
- [ ] `/api/query` with `mode=secure&role=employee|manager|admin`
- [ ] Metadata pre-filter in Qdrant (security_clearance <= role_level)
- [ ] Self-correcting loop (expand query, never relax clearance)
- [ ] Access-denied response when restricted docs are relevant but inaccessible

### Phase 4 — Knowledge Graph Extraction + API
- [ ] spaCy NER on all chunks (entities: people, orgs, policies, amounts, dates)
- [ ] GPT-4o-mini relationship extraction (subject → predicate → object triples)
- [ ] Build graph data structure (nodes + edges with metadata)
- [ ] `GET /api/graph` endpoint returning full graph JSON

### Phase 5 — Next.js Frontend (3 pages)
- [ ] Landing page with THREE cards (Project A / Project B / Knowledge Graph)
- [ ] Project A page: chat interface + source panel + retrieval scores
- [ ] Project B page: role selector → chat interface + access-denied UX
- [ ] Knowledge Graph page: `react-force-graph-3d` rendering all 11 docs, interactive, zoomable, clickable nodes
- [ ] Responsive, clean design (Tailwind + shadcn/ui)

### Phase 6 — Polish
- [ ] README for both projects
- [ ] Docker-compose for full local setup (Qdrant + FastAPI)
- [ ] Screenshots
- [ ] Vercel deployment (frontend) + Railway/Render (backend)

---

## Open Questions
1. ~~CUDA availability?~~ → **RESOLVED: MacBook M3, using MPS acceleration**
2. ~~OpenRouter API key?~~ → **RESOLVED: Using OpenAI API directly (Vidit has key)**
3. ~~Qdrant vs ChromaDB?~~ → **RESOLVED: Qdrant (Docker) for both modes**
4. ~~Streamlit vs Gradio?~~ → **RESOLVED: Next.js + FastAPI for Vercel deployment**
5. Vercel backend deploy — Railway vs Render vs Fly.io? → **TBD, build locally first**
6. Qdrant Cloud for prod or keep Docker-only? → **TBD after local dev works**
