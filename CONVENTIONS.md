# CONVENTIONS.md — Coding Standards & Patterns

> **Read this alongside MASTER_CONTEXT.md in every Claude Code chat.** These conventions ensure code stays consistent across multiple sessions.

---

## Python (Backend)

### General
- Python 3.12.2
- Type hints on ALL function signatures
- Docstrings on all public functions (Google style)
- f-strings for string formatting (never .format() or %)
- Explicit `from __future__ import annotations` NOT needed (3.12+)

### Naming
```python
# Files: snake_case
loader.py, bm25_index.py, graph_builder.py

# Classes: PascalCase
class DocumentChunk:
class RetrievalResult:

# Functions/methods: snake_case
def load_pdf(file_path: str) -> list[str]:
def build_bm25_index(chunks: list[str]) -> BM25Okapi:

# Constants: UPPER_SNAKE_CASE
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
RRF_K = 60

# Private functions: leading underscore
def _normalize_scores(scores: list[float]) -> list[float]:
```

### Imports Order
```python
# 1. Standard library
import os
import hashlib
from pathlib import Path

# 2. Third-party
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# 3. Local
from services.loader import load_pdf
from services.chunker import chunk_document
from config import settings
```

### Pydantic Models
All API request/response bodies use Pydantic v2 models defined in `backend/models.py`:
```python
class QueryRequest(BaseModel):
    query: str
    mode: Literal["open", "secure"] = "open"
    role: Literal["employee", "manager", "admin"] | None = None
    top_k: int = 5

class ChunkResult(BaseModel):
    chunk_id: str
    text: str
    score: float
    doc_name: str
    page_number: int
    security_level: int
    retrieval_method: str  # "dense", "bm25", or "hybrid"

class QueryResponse(BaseModel):
    answer: str
    sources: list[ChunkResult]
    prompt_assembled: str  # The raw prompt (always returned)
    retrieval_stats: dict  # dense_count, bm25_count, overlap, etc.
    access_denied: bool = False
    access_denied_message: str | None = None
```

### Error Handling
```python
# Always use HTTPException with specific status codes
raise HTTPException(status_code=404, detail="Collection not found. Run /api/ingest first.")
raise HTTPException(status_code=400, detail="Role is required when mode is 'secure'")

# Service-level errors: use custom exceptions
class RetrievalError(Exception):
    pass

class IngestionError(Exception):
    pass
```

### Config Pattern
```python
# backend/config.py — single source for all settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str = ""
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    collection_name: str = "technova_docs"
    chunk_size: int = 500
    chunk_overlap: int = 100
    top_k_retrieval: int = 10
    top_k_final: int = 5
    rrf_k: int = 60
    llm_model: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"

settings = Settings()
```

### Device Selection (MPS / CPU)
```python
# Use this pattern everywhere models are loaded
import torch

def get_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
```

---

## TypeScript (Frontend)

### General
- Next.js 14+ with App Router
- TypeScript strict mode
- Tailwind CSS for styling (NO separate CSS files)
- shadcn/ui for UI components
- No `any` types — use proper interfaces

### Naming
```typescript
// Files: kebab-case for pages, PascalCase for components
app/project-a/page.tsx
components/ChatInterface.tsx
components/SourcePanel.tsx
lib/api.ts

// Interfaces: PascalCase with 'I' prefix NOT used (just PascalCase)
interface QueryResponse {
  answer: string;
  sources: ChunkResult[];
}

// Functions: camelCase
function sendQuery(query: string, mode: string): Promise<QueryResponse>

// Constants: UPPER_SNAKE_CASE
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
```

### API Client Pattern
```typescript
// lib/api.ts — all API calls go through here
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function queryRAG(params: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${API_URL}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
```

### Component Pattern
```typescript
// Functional components with explicit props interface
interface ChatInterfaceProps {
  mode: "open" | "secure";
  role?: "employee" | "manager" | "admin";
}

export function ChatInterface({ mode, role }: ChatInterfaceProps) {
  // ...
}
```

---

## Metadata Schema

Every chunk stored in Qdrant carries this payload:

```python
{
    "chunk_id": "technova_hr_handbook_c014",          # Unique: {org}_{doc_slug}_c{index}
    "text": "Female employees who have completed...",  # The actual chunk text
    "doc_name": "TechNova_HR_Policy_Handbook",         # Human-readable doc name
    "doc_slug": "hr_handbook",                         # URL-safe slug
    "file_name": "TechNova_HR_Policy_Handbook.pdf",    # Original file name
    "org_id": "technova",                              # Organization identifier
    "domain": "HR",                                    # Department/domain
    "security_level": 1,                               # 0=PUBLIC, 1=INTERNAL, 2=CONFIDENTIAL, 3=RESTRICTED
    "security_label": "INTERNAL",                      # Human-readable label
    "page_number": 3,                                  # Source page in PDF
    "chunk_index": 14,                                 # Position within document
    "total_chunks": 42,                                # Total chunks in this document
    "char_count": 487,                                 # Character count of chunk
    "content_hash": "a1b2c3d4e5f6...",                # SHA-256 for deduplication
}
```

---

## Document-to-Metadata Mapping

Use this exact mapping when ingesting documents:

```python
DOCUMENT_METADATA = {
    "TechNova_HR_Policy_Handbook.pdf": {
        "doc_name": "TechNova HR Policy Handbook",
        "doc_slug": "hr_handbook",
        "domain": "HR",
        "security_level": 1,
        "security_label": "INTERNAL",
    },
    "TechNova_Training_Compliance.pdf": {
        "doc_name": "TechNova Training & Compliance",
        "doc_slug": "training_compliance",
        "domain": "HR",
        "security_level": 0,
        "security_label": "PUBLIC",
    },
    "TechNova_IT_Asset_Policy.pdf": {
        "doc_name": "TechNova IT Asset Policy",
        "doc_slug": "it_asset_policy",
        "domain": "IT",
        "security_level": 1,
        "security_label": "INTERNAL",
    },
    "TechNova_Platform_Architecture.pdf": {
        "doc_name": "TechNova Platform Architecture",
        "doc_slug": "platform_architecture",
        "domain": "Engineering",
        "security_level": 1,
        "security_label": "INTERNAL",
    },
    "TechNova_OnCall_Runbook.pdf": {
        "doc_name": "TechNova OnCall Runbook",
        "doc_slug": "oncall_runbook",
        "domain": "Engineering",
        "security_level": 1,
        "security_label": "INTERNAL",
    },
    "TechNova_Q4_Financial_Report.pdf": {
        "doc_name": "TechNova Q4 Financial Report",
        "doc_slug": "q4_financial_report",
        "domain": "Finance",
        "security_level": 2,
        "security_label": "CONFIDENTIAL",
    },
    "TechNova_Product_Roadmap_2026.pdf": {
        "doc_name": "TechNova Product Roadmap 2026",
        "doc_slug": "product_roadmap_2026",
        "domain": "Product",
        "security_level": 2,
        "security_label": "CONFIDENTIAL",
    },
    "TechNova_Vendor_Contracts.pdf": {
        "doc_name": "TechNova Vendor Contracts",
        "doc_slug": "vendor_contracts",
        "domain": "Procurement",
        "security_level": 2,
        "security_label": "CONFIDENTIAL",
    },
    "TechNova_Salary_Structure.pdf": {
        "doc_name": "TechNova Salary Structure",
        "doc_slug": "salary_structure",
        "domain": "HR",
        "security_level": 3,
        "security_label": "RESTRICTED",
    },
    "TechNova_Board_Minutes_Q4.pdf": {
        "doc_name": "TechNova Board Minutes Q4",
        "doc_slug": "board_minutes_q4",
        "domain": "Executive",
        "security_level": 3,
        "security_label": "RESTRICTED",
    },
    "TechNova_Security_Incident_Report.pdf": {
        "doc_name": "TechNova Security Incident Report",
        "doc_slug": "security_incident_report",
        "domain": "Security",
        "security_level": 3,
        "security_label": "RESTRICTED",
    },
}
```

---

## Security Levels & Roles

```python
SECURITY_LEVELS = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "CONFIDENTIAL": 2,
    "RESTRICTED": 3,
}

ROLE_CLEARANCE = {
    "employee": 1,   # Sees PUBLIC (0) + INTERNAL (1)
    "manager": 2,    # Sees PUBLIC (0) + INTERNAL (1) + CONFIDENTIAL (2)
    "admin": 3,      # Sees everything including RESTRICTED (3)
}
```

---

## Git Conventions

- `.env` and `.env.local` are NEVER committed (in .gitignore)
- `.env.example` is committed with placeholder values
- Commit messages: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- No compiled/generated files committed (node_modules, __pycache__, .next)
