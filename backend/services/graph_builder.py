"""Knowledge graph builder: spaCy NER + custom patterns + relationship extraction.

Builds a JSON graph of {documents, chunks, entities, relationships} for the
3D explorer. View-only — does NOT power Project A/B retrieval.
"""

import json
import re
from collections import defaultdict

import spacy
from openai import OpenAIError, OpenAI

from backend.config import DOCUMENT_METADATA, settings


SPACY_LABEL_TO_TYPE: dict[str, str] = {
    "PERSON": "PERSON",
    "ORG": "ORG",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "FAC": "LOCATION",
    "NORP": "GROUP",
    "MONEY": "AMOUNT",
    "PERCENT": "AMOUNT",
    "DATE": "DATE",
    "TIME": "DURATION",
    "CARDINAL": "NUMBER",
    "ORDINAL": "NUMBER",
    "PRODUCT": "PRODUCT",
    "EVENT": "EVENT",
    "LAW": "LAW",
    "WORK_OF_ART": "WORK",
    "LANGUAGE": "LANGUAGE",
}

CUSTOM_PATTERNS: dict[str, re.Pattern] = {
    "POLICY": re.compile(
        r"\b(?:[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})\s+"
        r"(?:Leave|Policy|Allowance|Benefit|Insurance|Program)\b"
    ),
    "ROLE_LEVEL": re.compile(r"\bL[1-8](?:\s*[-\u2013]\s*L[1-8])?\b"),
    "AMOUNT_INR": re.compile(
        r"\bINR\s*[\d,]+(?:\.\d+)?(?:\s*(?:lakhs?|crores?))?\b",
        re.IGNORECASE,
    ),
    "DEPARTMENT": re.compile(
        r"\b(?:HR|IT|Finance|Engineering|Product|Legal|Procurement|Security|Executive)\b"
    ),
    "SYSTEM_URL": re.compile(r"\b[\w-]+\.technova\.internal[\w/.-]*"),
}

ENTITY_LABELS_FROM_SPACY: set[str] = set(SPACY_LABEL_TO_TYPE.keys())

RELATIONSHIP_EXTRACTION_PROMPT = """Extract relationship triples from the text below.
Return ONLY a JSON array of triples. Each triple has: subject, predicate, object.
The predicate should be a short snake_case verb phrase (e.g. duration_is, eligible_for, reports_to, governs).
Limit to at most 8 triples. Skip generic/uninformative pairs.

Example output:
[
  {"subject": "Maternity Leave", "predicate": "duration_is", "object": "26 weeks"},
  {"subject": "L5 employees", "predicate": "eligible_for", "object": "ESOPs"}
]

Text:
{chunk_text}

Return ONLY the JSON array, nothing else."""


_MAX_LLM_CHUNKS = 80
_LLM_CHARS_PER_BATCH = 4000


class GraphBuilder:
    """Builds a knowledge graph of documents → chunks → entities → relationships."""

    def __init__(self) -> None:
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError as exc:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' not installed. "
                "Run: python -m spacy download en_core_web_sm"
            ) from exc

        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self._entity_registry: dict[str, dict] = {}
        self._chunk_entities: dict[str, list[str]] = defaultdict(list)
        self._node_ids: set[str] = set()
        self._edge_keys: set[tuple[str, str, str]] = set()

    # ---------- normalization & helpers ----------

    def _normalize_entity(self, text: str, label: str) -> str:
        normalized = text.strip().lower()
        normalized = re.sub(r"[\s_]+", " ", normalized)
        normalized = re.sub(r"[\.,;:!?\"'`]+$", "", normalized)
        normalized = re.sub(r"^[\.,;:!?\"'`]+", "", normalized)
        if label in {"AMOUNT", "MONEY"}:
            normalized = re.sub(r"[,\s]", "", normalized)
        return normalized

    def _entity_id(self, normalized: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
        slug = slug[:64] if slug else "unknown"
        return f"entity_{slug}"

    def _doc_id(self, doc_slug: str) -> str:
        return f"doc_{doc_slug}"

    def _chunk_node_id(self, chunk: dict) -> str:
        return f"chunk_{chunk['doc_slug']}_c{chunk['chunk_index']:03d}"

    def _add_node(self, node: dict) -> None:
        if node["id"] in self._node_ids:
            return
        self._node_ids.add(node["id"])
        self.nodes.append(node)

    def _add_edge(self, source: str, target: str, edge_type: str, label: str | None = None) -> None:
        key = (source, target, edge_type)
        if key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append({
            "source": source,
            "target": target,
            "type": edge_type,
            "label": label or edge_type,
        })

    # ---------- node construction ----------

    def build_document_and_chunk_nodes(self, all_chunks: list[dict]) -> None:
        """Create document nodes (one per file) and chunk nodes; link doc→chunk."""
        doc_chunks: dict[str, list[dict]] = defaultdict(list)
        for chunk in all_chunks:
            doc_chunks[chunk["file_name"]].append(chunk)

        for file_name, chunks in doc_chunks.items():
            meta = DOCUMENT_METADATA.get(file_name)
            if meta is None:
                continue
            doc_node_id = self._doc_id(meta["doc_slug"])
            pages = max((c["page_number"] for c in chunks), default=0)
            self._add_node({
                "id": doc_node_id,
                "label": meta["doc_name"],
                "type": "document",
                "security_level": meta["security_level"],
                "security_label": meta["security_label"],
                "domain": meta["domain"],
                "metadata": {
                    "pages": pages,
                    "chunks": len(chunks),
                    "file_name": file_name,
                },
            })

            for chunk in chunks:
                chunk_node_id = self._chunk_node_id(chunk)
                preview = chunk["text"][:120].replace("\n", " ").strip()
                if len(chunk["text"]) > 120:
                    preview += "..."
                self._add_node({
                    "id": chunk_node_id,
                    "label": f"{meta['doc_slug']} c{chunk['chunk_index']:03d} (p{chunk['page_number']})",
                    "type": "chunk",
                    "parent_doc": doc_node_id,
                    "page_number": chunk["page_number"],
                    "text_preview": preview,
                    "chunk_id": chunk["chunk_id"],
                })
                self._add_edge(doc_node_id, chunk_node_id, "contains", "contains")

    # ---------- entity extraction ----------

    def extract_entities_from_chunk(self, chunk: dict) -> list[dict]:
        """Run spaCy NER + custom regex patterns on a chunk. Returns entity records."""
        text = chunk["text"]
        found: list[tuple[str, str]] = []  # (raw_text, type)

        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ not in ENTITY_LABELS_FROM_SPACY:
                continue
            entity_type = SPACY_LABEL_TO_TYPE[ent.label_]
            ent_text = ent.text.strip()
            if len(ent_text) < 2 or len(ent_text) > 80:
                continue
            found.append((ent_text, entity_type))

        for entity_type, pattern in CUSTOM_PATTERNS.items():
            for match in pattern.finditer(text):
                raw = match.group(0).strip()
                if 2 <= len(raw) <= 80:
                    found.append((raw, entity_type))

        records: list[dict] = []
        seen_in_chunk: set[str] = set()
        for raw_text, entity_type in found:
            normalized = self._normalize_entity(raw_text, entity_type)
            if not normalized or len(normalized) < 2:
                continue
            entity_id = self._entity_id(normalized)
            if entity_id in seen_in_chunk:
                continue
            seen_in_chunk.add(entity_id)
            records.append({
                "id": entity_id,
                "label": raw_text,
                "normalized": normalized,
                "entity_type": entity_type,
            })
        return records

    def extract_all_entities(self, all_chunks: list[dict]) -> None:
        """Run entity extraction on every chunk and dedupe across all chunks."""
        for chunk in all_chunks:
            chunk_node_id = self._chunk_node_id(chunk)
            entities = self.extract_entities_from_chunk(chunk)
            for ent in entities:
                eid = ent["id"]
                if eid not in self._entity_registry:
                    node = {
                        "id": eid,
                        "label": ent["label"],
                        "type": "entity",
                        "entity_type": ent["entity_type"],
                        "mentions": 0,
                        "source_chunks": [],
                    }
                    self._entity_registry[eid] = node
                    self._add_node(node)
                node = self._entity_registry[eid]
                node["mentions"] += 1
                if chunk_node_id not in node["source_chunks"]:
                    node["source_chunks"].append(chunk_node_id)
                self._chunk_entities[chunk["chunk_id"]].append(eid)
                self._add_edge(chunk_node_id, eid, "mentions", "mentions")

    # ---------- relationship extraction ----------

    def _cooccurrence_relationships(self, all_chunks: list[dict]) -> None:
        """Fallback: entities co-occurring in the same chunk get a co_occurs_with edge."""
        pair_weights: dict[tuple[str, str], int] = defaultdict(int)
        for chunk in all_chunks:
            ents = list(dict.fromkeys(self._chunk_entities.get(chunk["chunk_id"], [])))
            for i in range(len(ents)):
                for j in range(i + 1, len(ents)):
                    a, b = sorted((ents[i], ents[j]))
                    pair_weights[(a, b)] += 1

        for (a, b), weight in pair_weights.items():
            if weight < 1:
                continue
            key = (a, b, "co_occurs_with")
            if key in self._edge_keys:
                continue
            self._edge_keys.add(key)
            self.edges.append({
                "source": a,
                "target": b,
                "type": "co_occurs_with",
                "label": "co-occurs",
                "weight": weight,
            })

    def _llm_relationships(self, all_chunks: list[dict]) -> int:
        """Use gpt-4o-mini to extract subject-predicate-object triples. Returns edge count."""
        if not settings.openai_api_key:
            return 0

        candidates = [c for c in all_chunks if self._chunk_entities.get(c["chunk_id"])]
        candidates.sort(
            key=lambda c: len(self._chunk_entities.get(c["chunk_id"], [])),
            reverse=True,
        )
        candidates = candidates[:_MAX_LLM_CHUNKS]
        if not candidates:
            return 0

        client = OpenAI(api_key=settings.openai_api_key)
        triples: list[dict] = []

        batch: list[dict] = []
        batch_chars = 0
        for chunk in candidates:
            text_len = len(chunk["text"])
            if batch and batch_chars + text_len > _LLM_CHARS_PER_BATCH:
                triples.extend(self._call_llm_for_batch(client, batch))
                batch = []
                batch_chars = 0
            batch.append(chunk)
            batch_chars += text_len
        if batch:
            triples.extend(self._call_llm_for_batch(client, batch))

        added = 0
        for triple in triples:
            subj_norm = self._normalize_entity(triple["subject"], "")
            obj_norm = self._normalize_entity(triple["object"], "")
            if not subj_norm or not obj_norm:
                continue
            subj_id = self._entity_id(subj_norm)
            obj_id = self._entity_id(obj_norm)

            if subj_id not in self._entity_registry:
                node = {
                    "id": subj_id,
                    "label": triple["subject"].strip(),
                    "type": "entity",
                    "entity_type": "CONCEPT",
                    "mentions": 0,
                    "source_chunks": [],
                }
                self._entity_registry[subj_id] = node
                self._add_node(node)
            if obj_id not in self._entity_registry:
                node = {
                    "id": obj_id,
                    "label": triple["object"].strip(),
                    "type": "entity",
                    "entity_type": "CONCEPT",
                    "mentions": 0,
                    "source_chunks": [],
                }
                self._entity_registry[obj_id] = node
                self._add_node(node)

            predicate = re.sub(r"[^a-z0-9_]+", "_", triple["predicate"].strip().lower()).strip("_")
            predicate = predicate or "related_to"
            key = (subj_id, obj_id, predicate)
            if key in self._edge_keys:
                continue
            self._edge_keys.add(key)
            self.edges.append({
                "source": subj_id,
                "target": obj_id,
                "type": predicate,
                "label": predicate.replace("_", " "),
            })
            added += 1
        return added

    def _call_llm_for_batch(self, client: OpenAI, batch: list[dict]) -> list[dict]:
        merged = "\n\n---\n\n".join(c["text"] for c in batch)
        prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(chunk_text=merged)
        try:
            resp = client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=600,
            )
            content = (resp.choices[0].message.content or "").strip()
        except OpenAIError as exc:
            print(f"[graph_builder] LLM call failed, skipping batch: {exc}")
            return []

        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?", "", content).strip()
            content = re.sub(r"```$", "", content).strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if not match:
                return []
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return []

        if not isinstance(parsed, list):
            return []
        valid: list[dict] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            if not all(k in item and isinstance(item[k], str) for k in ("subject", "predicate", "object")):
                continue
            valid.append(item)
        return valid

    def extract_relationships(self, all_chunks: list[dict], use_llm: bool = True) -> None:
        """Build entity↔entity edges via LLM (preferred) or co-occurrence (fallback)."""
        added = 0
        if use_llm and settings.openai_api_key:
            try:
                added = self._llm_relationships(all_chunks)
                print(f"[graph_builder] LLM extracted {added} relationship edges")
            except Exception as exc:
                print(f"[graph_builder] LLM extraction failed: {exc}; using co-occurrence")
                added = 0
        if added == 0:
            self._cooccurrence_relationships(all_chunks)
            print(f"[graph_builder] co-occurrence fallback applied")

    # ---------- main ----------

    def build_full_graph(self, all_chunks: list[dict], use_llm: bool = True) -> dict:
        """Build the complete graph and return the JSON-serializable dict."""
        self.nodes.clear()
        self.edges.clear()
        self._entity_registry.clear()
        self._chunk_entities.clear()
        self._node_ids.clear()
        self._edge_keys.clear()

        self.build_document_and_chunk_nodes(all_chunks)
        self.extract_all_entities(all_chunks)
        self.extract_relationships(all_chunks, use_llm=use_llm)
        return self.get_graph_json()

    def get_graph_json(self) -> dict:
        """Return the assembled graph as a JSON-serializable dict."""
        entity_type_counts: dict[str, int] = defaultdict(int)
        for node in self.nodes:
            if node["type"] == "entity":
                entity_type_counts[node.get("entity_type", "UNKNOWN")] += 1

        relationship_count = sum(
            1 for e in self.edges if e["type"] not in {"contains", "mentions"}
        )

        stats = {
            "total_documents": sum(1 for n in self.nodes if n["type"] == "document"),
            "total_chunks": sum(1 for n in self.nodes if n["type"] == "chunk"),
            "total_entities": sum(1 for n in self.nodes if n["type"] == "entity"),
            "total_relationships": relationship_count,
            "entity_types": dict(entity_type_counts),
        }
        return {"nodes": self.nodes, "edges": self.edges, "stats": stats}
