# PHASE_1_BACKEND_CORE.md — Build the RAG Pipeline

> **Claude Code Chat 1.** Read MASTER_CONTEXT.md and CONVENTIONS.md first, then follow this.

---

## Objective

Build the complete FastAPI backend with the full RAG ingestion and retrieval pipeline. By the end of this phase, you should be able to:
1. Run `docker-compose up` and have Qdrant running
2. Hit `POST /api/ingest` and see 11 PDFs chunked, embedded, and stored in Qdrant
3. Hit `POST /api/query` with a question and get back ranked results with sources
4. Hit `GET /api/status` and see collection health

---

## Step-by-Step Build Order

### 1. Project Scaffolding

Create the folder structure from MASTER_CONTEXT.md. Initialize:
- `backend/requirements.txt`
- `backend/config.py` (Settings class with all env vars)
- `backend/.env` with `OPENAI_API_KEY` placeholder
- `docker-compose.yml` with Qdrant service
- `.gitignore`

**requirements.txt:**
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic-settings==2.5.0
python-dotenv==1.0.1
pypdf==4.3.0
langchain-text-splitters==0.3.0
sentence-transformers==3.1.0
qdrant-client==1.12.0
rank-bm25==0.2.2
openai==1.50.0
spacy==3.8.0
torch>=2.0.0
numpy>=1.26.0
```

**docker-compose.yml:**
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

volumes:
  qdrant_data:
```

### 2. PDF Loader (`backend/services/loader.py`)

```python
def load_pdf(file_path: str) -> list[dict]:
    """
    Extract text from a PDF, page by page.
    
    Returns:
        list of {"page_number": int, "text": str}
    """
```

- Use `pypdf.PdfReader`
- Return list of dicts, one per page, with page_number (1-indexed) and extracted text
- Skip pages with no text (scanned images)
- Strip excessive whitespace

### 3. Chunker (`backend/services/chunker.py`)

```python
def chunk_document(
    pages: list[dict],
    file_name: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[dict]:
    """
    Split document pages into chunks with metadata.
    
    Uses RecursiveCharacterTextSplitter from langchain.
    Each chunk gets full metadata payload (see CONVENTIONS.md).
    SHA-256 deduplication: skip chunks with duplicate content_hash.
    
    Returns:
        list of chunk dicts with all metadata fields
    """
```

- Use `RecursiveCharacterTextSplitter` with separators: `["\n\n", "\n", ". ", " ", ""]`
- Maintain page_number tracking (when a chunk spans pages, use the starting page)
- Look up doc metadata from `DOCUMENT_METADATA` dict in CONVENTIONS.md
- Generate `chunk_id` as `{org}_{doc_slug}_c{index:03d}`
- Generate `content_hash` using SHA-256 of the chunk text
- Deduplicate: if two chunks have the same hash, keep only the first

### 4. Embedder (`backend/services/embedder.py`)

```python
class EmbeddingService:
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
        """Load model on MPS or CPU."""
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns list of 768-dim vectors."""
    
    def embed_query(self, query: str) -> list[float]:
        """Embed a single query. BGE expects 'Represent this sentence: ' prefix for queries."""
```

- Device selection: MPS > CPU (see CONVENTIONS.md pattern)
- BGE-specific: prepend `"Represent this sentence: "` to queries for better retrieval
- Batch encode documents WITHOUT the prefix
- Return Python lists (not numpy arrays) for Qdrant compatibility
- Log: model name, device, embedding dimension on init

### 5. Qdrant Store (`backend/services/store.py`)

```python
class QdrantStore:
    def __init__(self, host: str, port: int, collection_name: str):
        """Connect to Qdrant and optionally create collection."""
    
    def create_collection(self, vector_size: int = 768):
        """Create collection if it doesn't exist. Cosine distance."""
    
    def upsert_chunks(self, chunks: list[dict], embeddings: list[list[float]]):
        """Store chunks with embeddings and metadata payload."""
    
    def search(
        self, 
        query_embedding: list[float], 
        top_k: int = 10,
        security_filter: dict | None = None,
    ) -> list[dict]:
        """
        Dense KNN search with optional metadata filtering.
        
        security_filter example: {"security_level": {"$lte": 1}}
        Returns list of {chunk_id, text, score, ...metadata}
        """
    
    def get_collection_info(self) -> dict:
        """Return collection stats."""
    
    def collection_exists(self) -> bool:
        """Check if collection exists."""
    
    def delete_collection(self):
        """Drop collection for re-ingestion."""
```

- Use `qdrant_client.QdrantClient` with http connection
- Collection config: cosine distance, 768-dim vectors
- Point IDs: use integer hash of chunk_id for deterministic IDs
- Payload: all metadata fields from CONVENTIONS.md
- Filter syntax: use Qdrant's `models.Filter` with `FieldCondition`

### 6. BM25 Index (`backend/services/bm25_index.py`)

```python
class BM25Index:
    def __init__(self):
        self.index: BM25Okapi | None = None
        self.chunk_ids: list[str] = []
        self.chunk_texts: list[str] = []
        self.chunk_metadata: list[dict] = []
    
    def build(self, chunks: list[dict]):
        """Build BM25 index from chunk dicts. Tokenize by lowercase split."""
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        allowed_chunk_ids: set[str] | None = None,
    ) -> list[dict]:
        """
        BM25 keyword search.
        
        allowed_chunk_ids: if provided, only score these chunks (for security filtering).
        Returns list of {chunk_id, text, score, ...metadata}
        """
    
    def save(self, path: str):
        """Persist index to disk (pickle)."""
    
    def load(self, path: str):
        """Load index from disk."""
```

- Tokenization: `text.lower().split()` (simple but effective)
- The `allowed_chunk_ids` parameter enables security filtering for Project B:
  first get the set of chunk_ids that pass security filter from Qdrant, then
  only score those in BM25
- Persist with pickle so we don't rebuild on every restart

### 7. Retriever (`backend/services/retriever.py`)

This is the core. It orchestrates the full hybrid pipeline.

```python
class HybridRetriever:
    def __init__(
        self,
        store: QdrantStore,
        bm25: BM25Index,
        embedder: EmbeddingService,
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ):
        """Load reranker model."""
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        security_filter: dict | None = None,
        allowed_chunk_ids: set[str] | None = None,
    ) -> RetrievalResult:
        """
        Full hybrid retrieval pipeline:
        1. Dense search (Qdrant KNN, top_k=10)
        2. BM25 search (top_k=10, filtered if security)
        3. RRF fusion (merge + deduplicate)
        4. Cross-encoder reranking (top 10 → top_k)
        
        Returns RetrievalResult with ranked chunks + stats
        """
    
    def _rrf_fusion(
        self,
        dense_results: list[dict],
        bm25_results: list[dict],
        k: int = 60,
    ) -> list[dict]:
        """Reciprocal Rank Fusion. score = sum(1 / (k + rank))"""
    
    def _rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """Cross-encoder reranking. Score (query, chunk) pairs."""
```

**RRF Fusion pseudocode:**
```python
def _rrf_fusion(self, dense_results, bm25_results, k=60):
    scores = {}  # chunk_id -> rrf_score
    metadata = {}  # chunk_id -> chunk_dict
    
    for rank, result in enumerate(dense_results):
        cid = result["chunk_id"]
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        metadata[cid] = result
        metadata[cid]["retrieval_method"] = "dense"
    
    for rank, result in enumerate(bm25_results):
        cid = result["chunk_id"]
        if cid in scores:
            metadata[cid]["retrieval_method"] = "hybrid"  # found by both
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        if cid not in metadata:
            metadata[cid] = result
            metadata[cid]["retrieval_method"] = "bm25"
    
    # Sort by fused score, descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    results = []
    for cid, score in ranked:
        entry = metadata[cid].copy()
        entry["rrf_score"] = score
        results.append(entry)
    
    return results
```

**Cross-encoder reranking pseudocode:**
```python
def _rerank(self, query, candidates, top_k=5):
    pairs = [(query, c["text"]) for c in candidates]
    scores = self.reranker.predict(pairs)
    
    for i, score in enumerate(scores):
        candidates[i]["rerank_score"] = float(score)
    
    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    return candidates[:top_k]
```

### 8. Security Service (`backend/services/security.py`)

```python
ROLE_CLEARANCE = {
    "employee": 1,
    "manager": 2,
    "admin": 3,
}

def get_security_filter(role: str) -> dict:
    """Return Qdrant filter dict for the given role."""
    level = ROLE_CLEARANCE[role]
    return {"security_level": {"$lte": level}}

def get_allowed_chunk_ids(store: QdrantStore, role: str) -> set[str]:
    """Query Qdrant to get all chunk_ids visible to this role.
    Used to filter BM25 results."""

def check_restricted_docs_exist(store: QdrantStore, query_embedding, role: str) -> tuple[bool, int]:
    """Check if there are relevant docs at a HIGHER clearance than the user's role.
    Returns (exists: bool, count: int)"""
    
def self_correcting_retrieve(
    retriever: HybridRetriever,
    query: str,
    role: str,
    store: QdrantStore,
    top_k: int = 5,
    min_relevance: float = 0.3,
) -> dict:
    """
    Self-correcting loop:
    1. Normal retrieve with security filter
    2. If avg relevance < threshold, expand query + increase top_k
    3. NEVER relax security clearance
    4. Check if restricted docs exist → set access_denied flag
    """
```

### 9. Generator (`backend/services/generator.py`)

```python
SYSTEM_PROMPT = """You are a helpful assistant for TechNova Inc. Answer the employee's question
using ONLY the information provided in the Context below.

Rules:
- Only use information from the provided context
- Cite which source number [Source X] your answer comes from
- Be specific with numbers, dates, and amounts
- If the context doesn't contain enough information, say so clearly
- Never make up information not in the context"""

def assemble_prompt(query: str, chunks: list[dict]) -> str:
    """Build the full RAG prompt from retrieved chunks."""

async def generate_answer(query: str, chunks: list[dict]) -> tuple[str, str]:
    """
    Assemble prompt and send to OpenAI gpt-4o-mini.
    
    Returns: (answer: str, assembled_prompt: str)
    
    If OPENAI_API_KEY is not set, return the assembled prompt as the answer
    with a note that no LLM is configured.
    """
```

- Always return both the answer AND the assembled prompt (for transparency)
- If no API key: graceful fallback — return the raw prompt, don't crash

### 10. FastAPI App + Routers

**`backend/main.py`:**
```python
# Create FastAPI app
# Add CORS middleware (see API_CONTRACT.md)
# Include routers from routers/
# On startup: load embedding model, reranker, connect to Qdrant
# Store services in app.state for dependency injection
```

**`backend/routers/ingest.py`:**
- `POST /api/ingest` — load all PDFs from docs/, chunk, embed, store in Qdrant, build BM25 index
- Return stats per document

**`backend/routers/query.py`:**
- `POST /api/query` — validate request, route to open or secure mode, return response
- See API_CONTRACT.md for exact request/response schemas

**`backend/routers/status.py`:**
- `GET /api/status` — check Qdrant connection, collection stats, model status

**`backend/models.py`:**
- All Pydantic models from API_CONTRACT.md

---

## Acceptance Criteria

This phase is DONE when:

- [ ] `docker-compose up -d` starts Qdrant successfully
- [ ] `uvicorn backend.main:app --reload --port 8000` starts FastAPI
- [ ] `POST /api/ingest` processes all 11 PDFs and returns chunk counts
- [ ] `GET /api/status` shows collection with ~200-300 vectors
- [ ] `POST /api/query {"query": "maternity leave", "mode": "open"}` returns relevant chunks with scores
- [ ] `POST /api/query {"query": "salary bands", "mode": "secure", "role": "employee"}` returns access_denied
- [ ] `POST /api/query {"query": "salary bands", "mode": "secure", "role": "admin"}` returns actual salary data
- [ ] Cross-encoder reranking changes the order of top results (visible in scores)
- [ ] Assembled prompt is always returned in the response

---

## Files Created in This Phase

```
backend/
├── requirements.txt
├── Dockerfile
├── .env
├── main.py
├── config.py
├── models.py
├── services/
│   ├── __init__.py
│   ├── loader.py
│   ├── chunker.py
│   ├── embedder.py
│   ├── store.py
│   ├── bm25_index.py
│   ├── retriever.py
│   ├── security.py
│   └── generator.py
└── routers/
    ├── __init__.py
    ├── ingest.py
    ├── query.py
    └── status.py

docker-compose.yml
.env.example
.gitignore
```
