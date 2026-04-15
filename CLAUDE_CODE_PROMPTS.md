# CLAUDE_CODE_PROMPTS.md — Copy-Paste Prompts for Each Chat Session

> These are ready-to-use first messages for each Claude Code session. Copy the entire prompt block and paste it as your first message. Each prompt tells Claude Code exactly what to read, what to build, and what "done" looks like.

---

## Chat 1: Backend Core (RAG Pipeline + FastAPI)

**Estimated time: 60-90 minutes**

Copy and paste this:

```
Read these files in order before writing any code:
1. MASTER_CONTEXT.md — project overview and architecture
2. CONVENTIONS.md — coding standards, naming, metadata schemas
3. API_CONTRACT.md — exact request/response schemas for all endpoints
4. PHASE_1_BACKEND_CORE.md — step-by-step build instructions for this chat

Now build the complete FastAPI backend for the TechNova RAG Platform. This is a multi-document RAG system with hybrid retrieval. Here's what you're building:

1. Project scaffolding: backend/ folder with config.py, models.py, services/, routers/
2. docker-compose.yml with Qdrant
3. PDF loader (pypdf) — reads all 11 PDFs from docs/ folder
4. Chunker — RecursiveCharacterTextSplitter, 500 chars, 100 overlap, with full metadata tagging per chunk (see CONVENTIONS.md for exact schema)
5. Embedder — BAAI/bge-base-en-v1.5, 768-dim, runs on MPS (Apple M3 Mac) or CPU fallback
6. Qdrant store — create collection, upsert chunks with embeddings + metadata payload
7. BM25 index — BM25Okapi on tokenized chunks, with security filtering support
8. Hybrid retriever — Dense (Qdrant KNN) + BM25 + RRF fusion (k=60) + Cross-encoder reranking (ms-marco-MiniLM-L-6-v2, top 10 → top 5)
9. Security service — role-based filtering (employee/manager/admin), self-correcting loop, access-denied detection
10. Generator — prompt assembly + OpenAI gpt-4o-mini (graceful fallback if no API key)
11. FastAPI routers: POST /api/ingest, POST /api/query, GET /api/status
12. CORS configured for localhost:3000 and *.vercel.app

The PDFs are in the docs/ folder. The metadata mapping for each PDF (security_level, domain, etc.) is in CONVENTIONS.md — use it exactly.

Device for PyTorch: MPS if available (Apple Silicon), else CPU. Never assume CUDA.

Start with scaffolding, then build services bottom-up (loader → chunker → embedder → store → bm25 → retriever → security → generator), then wire up the FastAPI routers.

This phase is done when:
- docker-compose up starts Qdrant
- POST /api/ingest processes all 11 PDFs
- POST /api/query with mode=open returns ranked results
- POST /api/query with mode=secure and role=employee returns access_denied for salary questions
- Cross-encoder reranking visibly changes result ordering
```

---

## Chat 2: Knowledge Graph Extraction

**Estimated time: 30-45 minutes**

Copy and paste this:

```
Read these files in order before writing any code:
1. MASTER_CONTEXT.md — project overview
2. CONVENTIONS.md — coding standards
3. API_CONTRACT.md — the /api/graph endpoint response schema
4. PHASE_2_KNOWLEDGE_GRAPH.md — step-by-step build instructions

The backend from Phase 1 is already built and working. Now add knowledge graph extraction.

Build backend/services/graph_builder.py that:
1. Creates document-level nodes (11 docs) with security_level, domain, page count
2. Creates chunk-level nodes connected to their parent doc via "contains" edges
3. Runs spaCy NER (en_core_web_sm) on every chunk to extract entities (PERSON, ORG, MONEY, DATE, etc.)
4. Adds custom regex patterns for domain entities: policy names (X Leave, X Policy), role levels (L1-L8), INR amounts, department names, TechNova system URLs
5. Deduplicates entities by normalized name
6. Extracts relationships between entities — use GPT-4o-mini if OPENAI_API_KEY exists, otherwise fall back to co-occurrence heuristic (entities in same chunk → related)
7. Returns {"nodes": [...], "edges": [...], "stats": {...}} matching API_CONTRACT.md schema

Also:
- Create backend/routers/graph.py with GET /api/graph endpoint
- Modify backend/routers/ingest.py to build the graph after ingestion
- Store graph data in app.state.graph_data (cached in memory)

Node types: document (large), chunk (medium), entity (small)
Edge types: contains (doc→chunk), mentions (chunk→entity), relationship (entity→entity)

The graph is VIEW-ONLY — it does NOT power retrieval. It's a separate exploration tool.
```

---

## Chat 3: Next.js Frontend (All 3 Pages)

**Estimated time: 60-90 minutes**

Copy and paste this:

```
Read these files in order before writing any code:
1. MASTER_CONTEXT.md — project overview and file structure
2. CONVENTIONS.md — TypeScript naming conventions, component patterns
3. API_CONTRACT.md — exact API schemas the frontend consumes
4. PHASE_3_FRONTEND.md — detailed page-by-page specification

Build the Next.js frontend for the TechNova RAG Platform. The FastAPI backend is already running at http://localhost:8000.

Setup:
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir=false --import-alias="@/*"
cd frontend
npx shadcn@latest init
npx shadcn@latest add button card input badge separator scroll-area select dialog
npm install react-force-graph-3d three @types/three

Build these pages:

1. Landing Page (app/page.tsx):
   - Three cards: Open RAG, Secure RAG, Knowledge Graph
   - Dark theme, clean, professional
   - Each card links to its route

2. Project A (app/project-a/page.tsx):
   - Two-panel: chat (60%) + source panel (40%)
   - Chat interface with message history
   - Source panel shows retrieved chunks with: doc name badge, page number, security level badge (color-coded), relevance score, retrieval method badge (Dense/BM25/Hybrid), expandable text
   - Calls POST /api/query with mode="open"

3. Project B (app/project-b/page.tsx):
   - Same layout as Project A
   - Role selector at top: Employee (clearance 1, 5 docs) / Manager (clearance 2, 8 docs) / Admin (clearance 3, 11 docs)
   - Must select role before chatting
   - When access_denied=true in response: show warning banner with amber styling
   - Calls POST /api/query with mode="secure" and role=selectedRole

4. Knowledge Graph (app/knowledge-graph/page.tsx):
   - Full-screen react-force-graph-3d
   - Fetches from GET /api/graph
   - Node colors: documents by security level (green/blue/orange/red), entities by type (purple/teal/gold/cyan/pink)
   - Click node → floating info panel with details
   - Stats bar at bottom

Shared code:
- lib/api.ts — all API client functions (see PHASE_3_FRONTEND.md for exact code)
- lib/types.ts — TypeScript interfaces
- components/ — ChatInterface, SourcePanel, RoleSelector, AccessDenied, GraphViewer, LandingCard

The API_CONTRACT.md has exact response shapes — match your TypeScript interfaces to those.

NEXT_PUBLIC_API_URL=http://localhost:8000 in .env.local
```

---

## Chat 4: Integration + Polish

**Estimated time: 30-45 minutes**

Copy and paste this:

```
Read these files:
1. MASTER_CONTEXT.md
2. PHASE_4_INTEGRATION.md — integration tasks and test scenarios

The backend (Phase 1 + 2) and frontend (Phase 3) are built. Now wire everything together and polish.

Tasks:
1. Update docker-compose.yml to include the backend service (see PHASE_4_INTEGRATION.md for the exact config)
2. Create backend/Dockerfile
3. Test these exact scenarios and fix any issues:

   Project A tests:
   - "What is the maternity leave policy?" → cite HR Handbook page 3
   - "DPDP Act 2023" → BM25 should perform well (keyword)
   - "How much time off for new mothers?" → Dense should perform well (semantic)
   
   Project B tests (employee):
   - "What are the salary bands?" → ACCESS DENIED
   - "What training is required?" → NORMAL ANSWER
   
   Project B tests (admin):
   - "What are the salary bands?" → NORMAL ANSWER with actual data
   - "Security incident details?" → NORMAL ANSWER
   
   Knowledge Graph:
   - Graph loads with 11 doc nodes, entities, relationships
   - Cross-doc connections visible

4. Create README.md with quick start instructions
5. Create .env.example and .gitignore
6. Verify: system works with NO OpenAI key (returns assembled prompt instead of LLM answer)
7. Verify: all error states handled gracefully (Qdrant down, no docs ingested, bad role)

Fix any bugs found during testing. The goal is: someone clones this repo, runs docker-compose up + npm run dev, and everything works.
```

---

## Emergency / Fix Chat

If something breaks between phases or you need to fix a specific issue, use this prompt template:

```
Read MASTER_CONTEXT.md and CONVENTIONS.md for project context.

The TechNova RAG Platform has a bug / issue:

[Describe the exact problem — paste error messages, describe expected vs actual behavior]

The relevant files are:
[List the files involved]

The backend runs on FastAPI (Python 3.12) at localhost:8000.
The frontend runs on Next.js at localhost:3000.
Qdrant runs in Docker at localhost:6333.

Fix this issue. Don't refactor unrelated code — surgical fix only.
```

---

## Notes for Vidit

1. **Always start each chat by telling Claude Code to read the docs.** The first line matters — if it doesn't read MASTER_CONTEXT.md, it'll make wrong assumptions.

2. **One phase per chat.** Don't try to do Phase 1 + 2 in the same chat. Context windows fill up, and Claude Code starts forgetting earlier instructions.

3. **Test between phases.** Before starting Chat 2, verify Chat 1's output actually works. Run the test scenarios from PHASE_4_INTEGRATION.md as you go.

4. **If Claude Code asks "should I use X or Y?"** — point it to the relevant doc. The answer is almost always in CONVENTIONS.md or MASTER_CONTEXT.md.

5. **Copy the PDFs to `docs/` folder before starting Chat 1.** The backend expects them there.

6. **The order matters:** Chat 1 → Chat 2 → Chat 3 → Chat 4. Frontend (Chat 3) can technically start in parallel with Chat 2, but it's safer to go sequential.
