# PHASE_4_INTEGRATION.md — Wire Everything Together + Polish

> **Claude Code Chat 4.** Read MASTER_CONTEXT.md first. This phase assumes Phase 1, 2, and 3 are complete.

---

## Objective

Connect frontend to backend, containerize everything, test end-to-end, and prepare for deployment.

---

## Tasks

### 1. Docker-Compose Full Stack

Update `docker-compose.yml` to run both Qdrant and the FastAPI backend:

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    env_file:
      - ./backend/.env
    depends_on:
      qdrant:
        condition: service_healthy
    volumes:
      - ./docs:/app/docs
    restart: unless-stopped

volumes:
  qdrant_data:
```

**Backend Dockerfile (`backend/Dockerfile`):**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Startup Flow

When the backend starts:
1. Connect to Qdrant (retry with backoff if not ready)
2. Check if collection exists
3. If collection exists → load BM25 index from disk, load models
4. If collection doesn't exist → wait for `/api/ingest` call
5. Models (embedder, reranker) loaded lazily on first use or eagerly on startup

### 3. End-to-End Testing Checklist

Test these exact scenarios:

**Project A tests:**
- [ ] "What is the maternity leave policy?" → should cite HR Handbook, page 3
- [ ] "DPDP Act 2023" → BM25 should outperform dense (keyword match)
- [ ] "How much time off for new mothers?" → Dense should outperform BM25 (semantic)
- [ ] "What is the hotel reimbursement for senior employees?" → should cite Travel policy
- [ ] "Tell me about YubiKey" → should find Information Security section

**Project B tests (employee role):**
- [ ] "What are the salary bands?" → ACCESS DENIED (Salary Structure is RESTRICTED)
- [ ] "What happened in the board meeting?" → ACCESS DENIED (Board Minutes is RESTRICTED)
- [ ] "What is the maternity leave policy?" → NORMAL ANSWER (HR Handbook is INTERNAL)
- [ ] "What training is required?" → NORMAL ANSWER (Training Compliance is PUBLIC)

**Project B tests (manager role):**
- [ ] "What are the salary bands?" → ACCESS DENIED (still RESTRICTED)
- [ ] "What is the Q4 revenue?" → NORMAL ANSWER (Financial Report is CONFIDENTIAL, manager can see)
- [ ] "What vendors does TechNova use?" → NORMAL ANSWER (Vendor Contracts is CONFIDENTIAL)

**Project B tests (admin role):**
- [ ] "What are the salary bands?" → NORMAL ANSWER (admin sees RESTRICTED)
- [ ] "What happened in the security incident?" → NORMAL ANSWER (admin sees everything)

**Knowledge Graph tests:**
- [ ] Graph loads with 11 document nodes
- [ ] Entities visible and clickable
- [ ] Cross-document connections visible (e.g., "L5" appears in both Salary and Performance docs)

### 4. README.md

Create a root-level README with:

```markdown
# TechNova RAG Platform

Multi-document RAG system with hybrid retrieval, role-based access control, 
and interactive knowledge graph visualization.

## Features
- **Open RAG** — Chat with all 11 TechNova documents
- **Secure RAG** — Role-based access control (employee/manager/admin)  
- **Knowledge Graph** — 3D visualization of entities and relationships

## Tech Stack
[table from MASTER_CONTEXT.md]

## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.12+
- Node.js 18+
- OpenAI API key (optional — system works without it)

### Run

# 1. Start Qdrant
docker-compose up -d qdrant

# 2. Start backend
cd backend
cp .env.example .env  # Add your OPENAI_API_KEY if you have one
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn main:app --reload --port 8000

# 3. Ingest documents
curl -X POST http://localhost:8000/api/ingest

# 4. Start frontend
cd frontend
npm install
npm run dev

# 5. Open http://localhost:3000

## Architecture
[diagram from MASTER_CONTEXT.md]

## Retrieval Pipeline
[pipeline from MASTER_CONTEXT.md]
```

### 5. Environment Files

**`.env.example` (root):**
```
# Backend
OPENAI_API_KEY=sk-your-key-here
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**`.gitignore`:**
```
# Dependencies
node_modules/
__pycache__/
*.pyc
.venv/

# Environment
.env
.env.local

# Build
.next/
dist/
build/

# Data
qdrant_data/
*.pkl
*.pickle

# IDE
.vscode/
.idea/
*.swp
```

---

## Acceptance Criteria

- [ ] `docker-compose up` starts Qdrant + backend
- [ ] Frontend connects to backend, all 3 pages functional
- [ ] All test scenarios from section 3 pass
- [ ] README is clear enough for someone to clone and run in 5 minutes
- [ ] No hardcoded API keys anywhere in code
- [ ] Graceful error handling: Qdrant down, no API key, no documents ingested

---

## Files Created/Modified

```
docker-compose.yml                  # UPDATED (add backend service)
backend/Dockerfile                  # NEW
README.md                           # NEW
.env.example                        # NEW
.gitignore                          # NEW
```
