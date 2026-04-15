# MASTER_CONTEXT.md — Single Source of Truth

> **Read this file first in every Claude Code chat.** It describes the entire project, architecture, and how pieces connect. Do NOT start coding without reading this.

---

## Project Overview

**Name:** TechNova RAG Platform
**What it is:** A full-stack RAG (Retrieval-Augmented Generation) system with three features accessible from a single landing page:

1. **Project A — Open RAG:** Chat with all 11 TechNova internal documents. No access control. Hybrid retrieval (Dense + BM25 + RRF + Cross-Encoder reranking). LLM generates grounded answers.

2. **Project B — Secure RAG:** Same RAG pipeline but with role-based access control. Three roles (employee/manager/admin) see different document subsets based on security clearance. Restricted documents are never leaked — the system responds with "access restricted" messaging.

3. **Knowledge Graph Explorer:** Interactive 3D visualization of all 11 documents showing chunks, entities, and relationships as an interconnected graph. Built with react-force-graph-3d. View-only — does NOT power retrieval for Projects A/B.

---

## Tech Stack

| Layer | Technology | Version/Notes |
|-------|-----------|---------------|
| Frontend | Next.js (React + TypeScript) | App Router, Tailwind CSS, shadcn/ui |
| Backend | FastAPI (Python) | Python 3.12.2, uvicorn |
| Vector DB | Qdrant | Docker container, port 6333 |
| Embeddings | BAAI/bge-base-en-v1.5 | 768-dim, runs locally on MPS (Apple M3) |
| BM25 | rank_bm25 | BM25Okapi, in-memory |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | Local, reranks top 10 → top 5 |
| NER | spaCy (en_core_web_sm) | Entity extraction for knowledge graph |
| LLM | OpenAI gpt-4o-mini | Last-mile generation only, via openai SDK |
| Containerization | Docker + docker-compose | Qdrant + FastAPI backend |

### Hardware Target
- MacBook Pro M3 (Apple Silicon)
- No NVIDIA GPU — use MPS (Metal Performance Shaders) for PyTorch
- Device selection: `"mps" if torch.backends.mps.is_available() else "cpu"`

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│              Next.js Frontend (Vercel)                │
│                                                       │
│  Landing Page ──┬── /project-a  (Open RAG chat)      │
│                 ├── /project-b  (Secure RAG chat)    │
│                 └── /knowledge-graph (3D explorer)   │
└────────────────────────┬─────────────────────────────┘
                         │  HTTP (fetch / axios)
                         ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Backend (Python)                  │
│                                                       │
│  POST /api/ingest     ← Ingest PDFs into pipeline    │
│  POST /api/query      ← Query with mode + role       │
│  GET  /api/graph      ← Knowledge graph data (JSON)  │
│  GET  /api/status     ← Health check + stats         │
│                                                       │
│  Internal modules:                                    │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐            │
│  │ loader   │ │ chunker  │ │ embedder  │            │
│  └────┬─────┘ └────┬─────┘ └─────┬─────┘            │
│       └─────────────┼─────────────┘                   │
│                     ▼                                 │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐            │
│  │ store    │ │retriever │ │ generator │            │
│  │ (qdrant) │ │(hybrid)  │ │ (openai)  │            │
│  └──────────┘ └──────────┘ └───────────┘            │
│  ┌──────────┐ ┌──────────┐                           │
│  │ security │ │ graph    │                           │
│  │ (roles)  │ │(spacy+gpt│                           │
│  └──────────┘ └──────────┘                           │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              Qdrant (Docker)                          │
│              Port 6333 (REST) / 6334 (gRPC)          │
│              Collection: "technova_docs"              │
│              768-dim vectors + metadata payload       │
└─────────────────────────────────────────────────────┘
```

---

## Document Corpus (11 PDFs)

All documents are from TechNova Inc. Each has a built-in security classification.

| Document | File Name | Classification | Level | Domain |
|----------|-----------|---------------|-------|--------|
| HR Policy Handbook | TechNova_HR_Policy_Handbook.pdf | INTERNAL | 1 | HR |
| Training & Compliance | TechNova_Training_Compliance.pdf | PUBLIC | 0 | HR |
| IT Asset Policy | TechNova_IT_Asset_Policy.pdf | INTERNAL | 1 | IT |
| Platform Architecture | TechNova_Platform_Architecture.pdf | INTERNAL | 1 | Engineering |
| OnCall Runbook | TechNova_OnCall_Runbook.pdf | INTERNAL | 1 | Engineering |
| Q4 Financial Report | TechNova_Q4_Financial_Report.pdf | CONFIDENTIAL | 2 | Finance |
| Product Roadmap 2026 | TechNova_Product_Roadmap_2026.pdf | CONFIDENTIAL | 2 | Product |
| Vendor Contracts | TechNova_Vendor_Contracts.pdf | CONFIDENTIAL | 2 | Procurement |
| Salary Structure | TechNova_Salary_Structure.pdf | RESTRICTED | 3 | HR |
| Board Minutes Q4 | TechNova_Board_Minutes_Q4.pdf | RESTRICTED | 3 | Executive |
| Security Incident Report | TechNova_Security_Incident_Report.pdf | RESTRICTED | 3 | Security |

### Role → Document Access Mapping

| Role | Clearance Level | Sees | Doc Count |
|------|----------------|------|-----------|
| employee | 1 | PUBLIC + INTERNAL | 5 docs |
| manager | 2 | PUBLIC + INTERNAL + CONFIDENTIAL | 8 docs |
| admin | 3 | Everything including RESTRICTED | 11 docs |

---

## Retrieval Pipeline (Core Logic)

This is the heart of the system. It runs 100% locally — the OpenAI API is only used at the final generation step.

```
User Query
    │
    ▼
┌─ Step 1: Security Pre-Filter (Project B only) ─────────────┐
│  Qdrant metadata filter: security_level <= user_clearance   │
│  AND org_id == "technova"                                    │
│  Project A: skip this step (no filtering)                    │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─ Step 2: Dense Retrieval (Qdrant KNN) ──────────────────────┐
│  Embed query with BGE → cosine similarity → top 10          │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─ Step 3: BM25 Retrieval ────────────────────────────────────┐
│  Tokenize query → BM25Okapi scores → top 10                 │
│  (filtered to same security-eligible chunk IDs if Project B) │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─ Step 4: RRF Fusion ────────────────────────────────────────┐
│  Reciprocal Rank Fusion: score = Σ 1/(k + rank)            │
│  k = 60 (standard), merge dense + BM25 rankings             │
│  Deduplicate, sort by fused score → top 10 candidates        │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─ Step 5: Cross-Encoder Reranking ───────────────────────────┐
│  Model: cross-encoder/ms-marco-MiniLM-L-6-v2               │
│  Input: (query, chunk) pairs for top 10                      │
│  Output: relevance scores → re-sort → take top 5            │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─ Step 6: Self-Correcting Loop (Project B only) ─────────────┐
│  IF avg relevance < 0.3 AND top_5 seems weak:               │
│    → Expand query with synonyms                              │
│    → Increase retrieval to top_k=15                          │
│    → Re-run Steps 2-5                                        │
│    → NEVER relax security clearance                          │
│  IF restricted docs exist but user can't access:             │
│    → Flag: "Additional info may require higher clearance"    │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─ Step 7: Prompt Assembly ───────────────────────────────────┐
│  System instruction + retrieved chunks with citations        │
│  + user question → assembled prompt (printed/logged)         │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─ Step 8: LLM Generation (OpenAI, last mile) ───────────────┐
│  gpt-4o-mini → grounded natural language response            │
│  If no API key: return assembled prompt + raw chunks         │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
technova-rag/
├── MASTER_CONTEXT.md              # This file
├── CONVENTIONS.md                 # Coding standards
├── API_CONTRACT.md                # FastAPI ↔ Next.js interface
├── memory.md                      # Decision log
├── docker-compose.yml             # Qdrant + FastAPI
├── .env.example                   # Environment variables template
│
├── docs/                          # PDF corpus (11 files)
│   ├── TechNova_HR_Policy_Handbook.pdf
│   ├── TechNova_Training_Compliance.pdf
│   ├── TechNova_IT_Asset_Policy.pdf
│   ├── TechNova_Platform_Architecture.pdf
│   ├── TechNova_OnCall_Runbook.pdf
│   ├── TechNova_Q4_Financial_Report.pdf
│   ├── TechNova_Product_Roadmap_2026.pdf
│   ├── TechNova_Vendor_Contracts.pdf
│   ├── TechNova_Salary_Structure.pdf
│   ├── TechNova_Board_Minutes_Q4.pdf
│   └── TechNova_Security_Incident_Report.pdf
│
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Settings, constants, env vars
│   ├── models.py                  # Pydantic request/response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── loader.py              # PDF text extraction
│   │   ├── chunker.py             # Text splitting + metadata
│   │   ├── embedder.py            # BGE embedding (MPS)
│   │   ├── store.py               # Qdrant client wrapper
│   │   ├── bm25_index.py          # BM25 index management
│   │   ├── retriever.py           # Hybrid retrieval + RRF + reranking
│   │   ├── security.py            # Role-based filtering + self-correcting loop
│   │   ├── generator.py           # OpenAI prompt assembly + generation
│   │   └── graph_builder.py       # spaCy NER + relationship extraction
│   └── routers/
│       ├── __init__.py
│       ├── ingest.py              # POST /api/ingest
│       ├── query.py               # POST /api/query
│       ├── graph.py               # GET /api/graph
│       └── status.py              # GET /api/status
│
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── .env.local                 # NEXT_PUBLIC_API_URL
    ├── app/
    │   ├── layout.tsx             # Root layout
    │   ├── page.tsx               # Landing page (3 cards)
    │   ├── project-a/
    │   │   └── page.tsx           # Open RAG chat
    │   ├── project-b/
    │   │   └── page.tsx           # Secure RAG chat
    │   └── knowledge-graph/
    │       └── page.tsx           # 3D graph explorer
    ├── components/
    │   ├── ChatInterface.tsx      # Shared chat component
    │   ├── SourcePanel.tsx        # Retrieved chunks display
    │   ├── RoleSelector.tsx       # Project B role picker
    │   ├── AccessDenied.tsx       # Restricted content messaging
    │   ├── GraphViewer.tsx        # 3D force graph wrapper
    │   └── LandingCard.tsx        # Landing page card component
    └── lib/
        ├── api.ts                 # API client functions
        └── types.ts               # TypeScript interfaces
```

---

## Environment Variables

```bash
# .env (backend)
OPENAI_API_KEY=sk-...
QDRANT_HOST=localhost
QDRANT_PORT=6333
EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
COLLECTION_NAME=technova_docs
CHUNK_SIZE=500
CHUNK_OVERLAP=100
TOP_K_RETRIEVAL=10
TOP_K_FINAL=5
RRF_K=60
LLM_MODEL=gpt-4o-mini

# .env.local (frontend)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Key Design Principles

1. **Pipeline-first:** The retrieval pipeline (BM25 + Dense + RRF + Reranker) runs 100% locally. The LLM is the last mile — a replaceable component. If you remove the API key, the system still works (returns assembled prompt + raw chunks).

2. **Security as pre-filter, not post-filter:** In Project B, restricted documents are excluded BEFORE retrieval, not after. The system never retrieves a restricted chunk and then hides it — it never sees it in the first place.

3. **One backend, two modes:** The `/api/query` endpoint accepts a `mode` parameter (`open` or `secure`). The same retrieval pipeline runs in both — the only difference is whether the security pre-filter is applied.

4. **Knowledge graph is view-only:** The 3D graph exists for exploration and understanding. It does NOT power retrieval for Projects A/B. This may change in a future version (GraphRAG), but not now.

5. **Graceful degradation:** No OpenAI key? Returns prompt + chunks. Qdrant down? Returns error with instructions. No MPS? Falls back to CPU.
