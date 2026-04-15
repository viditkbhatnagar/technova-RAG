# PHASE_2_KNOWLEDGE_GRAPH.md — Entity & Relationship Extraction

> **Claude Code Chat 2.** Read MASTER_CONTEXT.md and CONVENTIONS.md first, then follow this.
> **Depends on:** Phase 1 must be complete (ingestion pipeline working, chunks in Qdrant).

---

## Objective

Build the knowledge graph extraction pipeline and the `/api/graph` endpoint. By the end of this phase:
1. spaCy extracts entities from every chunk
2. GPT-4o-mini extracts relationship triples between entities
3. `GET /api/graph` returns a complete node + edge JSON structure
4. The data is ready for the frontend 3D visualization

---

## Important Context

The knowledge graph is **view-only** — it does NOT power retrieval for Projects A or B. It exists as a standalone exploration tool. The graph shows how documents, chunks, entities, and relationships connect across all 11 TechNova docs.

---

## Step-by-Step Build Order

### 1. Install spaCy model

Add to requirements.txt (already there) and in Dockerfile or setup:
```bash
python -m spacy download en_core_web_sm
```

### 2. Entity Extractor (`backend/services/graph_builder.py`)

```python
import spacy
from collections import defaultdict

class GraphBuilder:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self._entity_registry: dict[str, dict] = {}  # normalized_name -> node
    
    def extract_entities_from_chunk(self, chunk: dict) -> list[dict]:
        """
        Run spaCy NER on chunk text.
        
        Extract: PERSON, ORG, MONEY, DATE, TIME, PERCENT, CARDINAL, ORDINAL
        Also extract custom entities:
          - Policy names (pattern: "X Leave", "X Policy", "X Allowance")
          - Role levels (L1-L8 pattern)
          - Department names
        
        Returns list of entity dicts:
        {
            "id": "entity_{normalized_name}",
            "label": "26 weeks",
            "type": "entity",
            "entity_type": "DURATION",  # spaCy label or custom
            "mentions": 1,
            "source_chunks": ["chunk_id_1"]
        }
        """
    
    def _normalize_entity(self, text: str, label: str) -> str:
        """Normalize entity text for deduplication.
        e.g., 'INR 25,000' and 'INR 25000' should be the same entity."""
    
    def build_document_and_chunk_nodes(self, all_chunks: list[dict]) -> None:
        """
        Create document-level nodes (11) and chunk-level nodes.
        Create 'contains' edges from doc → chunk.
        """
    
    def extract_all_entities(self, all_chunks: list[dict]) -> None:
        """
        Run entity extraction on all chunks.
        Create entity nodes (deduplicated by normalized name).
        Create 'mentions' edges from chunk → entity.
        Track mention count per entity.
        """
    
    def extract_relationships(self, all_chunks: list[dict], use_llm: bool = True) -> None:
        """
        Extract relationship triples between entities.
        
        If use_llm=True: send chunks to GPT-4o-mini for triple extraction.
        If use_llm=False: use co-occurrence heuristic (entities in same chunk are related).
        
        Relationship format:
        {
            "source": "entity_maternity_leave",
            "target": "entity_26_weeks",
            "type": "has_duration",
            "label": "entitles"
        }
        """
    
    def build_full_graph(self, all_chunks: list[dict], use_llm: bool = True) -> dict:
        """
        Main entry point. Builds the complete graph:
        1. Document + chunk nodes
        2. Entity extraction (spaCy)
        3. Relationship extraction (LLM or heuristic)
        4. Return {"nodes": [...], "edges": [...], "stats": {...}}
        """
    
    def get_graph_json(self) -> dict:
        """Return the built graph as JSON-serializable dict."""
```

### 3. LLM-Based Relationship Extraction

For each chunk (or batch of related chunks), send to GPT-4o-mini:

```python
RELATIONSHIP_EXTRACTION_PROMPT = """Extract relationship triples from this text.
Return ONLY a JSON array of triples. Each triple has: subject, predicate, object.

Example:
[
  {"subject": "Maternity Leave", "predicate": "duration_is", "object": "26 weeks"},
  {"subject": "L5 employees", "predicate": "eligible_for", "object": "ESOPs"},
  {"subject": "Annual Review", "predicate": "determines", "object": "compensation adjustments"}
]

Text:
{chunk_text}

Return ONLY the JSON array, nothing else."""
```

- Batch chunks to reduce API calls (send 5-10 chunks per request)
- Parse JSON response, handle malformed responses gracefully
- Deduplicate triples across chunks
- If no API key: fall back to co-occurrence heuristic (entities appearing in the same chunk get a "co_occurs_with" edge)

### 4. Co-occurrence Heuristic (Fallback)

```python
def _cooccurrence_relationships(self, all_chunks: list[dict]) -> None:
    """
    For each chunk, find all entities mentioned in it.
    Create edges between entities that appear in the same chunk.
    Edge weight = number of chunks they co-occur in.
    """
```

### 5. Custom Entity Patterns

Beyond spaCy's default NER, add regex/pattern-based extraction for domain-specific entities:

```python
CUSTOM_PATTERNS = {
    "POLICY": r"(?:[\w\s]+(?:Leave|Policy|Allowance|Benefit|Insurance|Program))",
    "ROLE_LEVEL": r"L[1-8](?:\s*[-–]\s*L[1-8])?",
    "AMOUNT_INR": r"INR\s*[\d,]+(?:\.\d+)?(?:\s*(?:lakhs?|crores?))?",
    "DEPARTMENT": r"(?:HR|IT|Finance|Engineering|Product|Legal|Procurement|Security|Executive)",
    "SYSTEM_URL": r"(?:[\w]+\.technova\.internal[\w/]*)",
}
```

### 6. Graph API Endpoint (`backend/routers/graph.py`)

```python
@router.get("/api/graph")
async def get_knowledge_graph():
    """
    Return the full knowledge graph.
    
    If graph hasn't been built yet, return 404 with instructions.
    Graph is built during ingestion (POST /api/ingest) or can be
    triggered separately.
    """
```

- The graph can be built during ingestion (add to the ingest pipeline) or lazily on first request
- Cache the graph in memory — it doesn't change between ingestions
- See API_CONTRACT.md for exact response schema

### 7. Update Ingestion Pipeline

Modify `POST /api/ingest` (from Phase 1) to also build the knowledge graph after embedding:

```python
# In routers/ingest.py, after storing chunks in Qdrant:
graph_builder = GraphBuilder()
graph_data = graph_builder.build_full_graph(all_chunks, use_llm=bool(settings.openai_api_key))
app.state.graph_data = graph_data
```

---

## Acceptance Criteria

- [ ] spaCy extracts entities from all chunks (at least 100+ unique entities across 11 docs)
- [ ] Custom patterns catch policy names, role levels, INR amounts, department names
- [ ] Entities are deduplicated by normalized name
- [ ] Relationship triples extracted (via LLM or co-occurrence fallback)
- [ ] `GET /api/graph` returns valid JSON matching API_CONTRACT.md schema
- [ ] Graph has 4 node types: document, chunk, entity
- [ ] Graph has edge types: contains (doc→chunk), mentions (chunk→entity), and relationship edges (entity→entity)
- [ ] Cross-document entity connections visible (same entity appears in multiple docs)

---

## Files Created/Modified

```
backend/services/graph_builder.py   # NEW
backend/routers/graph.py            # NEW
backend/routers/ingest.py           # MODIFIED (add graph building)
backend/main.py                     # MODIFIED (include graph router)
```
