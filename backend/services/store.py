"""Qdrant vector store wrapper."""

import hashlib

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from backend.config import EMBEDDING_DIM, ORG_ID


_PAYLOAD_FIELDS = (
    "chunk_id",
    "text",
    "doc_name",
    "doc_slug",
    "file_name",
    "org_id",
    "domain",
    "security_level",
    "security_label",
    "page_number",
    "chunk_index",
    "total_chunks",
    "char_count",
    "content_hash",
    "source_type",
    "table",
    "row_id",
)


def _point_id(chunk_id: str) -> int:
    """Stable unsigned 63-bit int from a chunk_id."""
    digest = hashlib.sha1(chunk_id.encode("utf-8")).hexdigest()
    return int(digest[:15], 16)


class QdrantStore:
    def __init__(self, host: str, port: int, collection_name: str):
        self.client = QdrantClient(host=host, port=port, timeout=30.0)
        self.collection_name = collection_name

    # ---------- lifecycle ----------

    def collection_exists(self) -> bool:
        try:
            names = {c.name for c in self.client.get_collections().collections}
            return self.collection_name in names
        except Exception:
            return False

    def create_collection(self, vector_size: int = EMBEDDING_DIM) -> None:
        if self.collection_exists():
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=qmodels.VectorParams(
                size=vector_size,
                distance=qmodels.Distance.COSINE,
            ),
        )
        # Payload indexes for filtering
        for field, schema in (
            ("security_level", qmodels.PayloadSchemaType.INTEGER),
            ("org_id", qmodels.PayloadSchemaType.KEYWORD),
            ("domain", qmodels.PayloadSchemaType.KEYWORD),
            ("doc_slug", qmodels.PayloadSchemaType.KEYWORD),
        ):
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=schema,
                )
            except Exception:
                pass

    def delete_collection(self) -> None:
        if self.collection_exists():
            self.client.delete_collection(collection_name=self.collection_name)

    # ---------- writes ----------

    def upsert_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
        batch_size: int = 128,
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must be the same length")

        points: list[qmodels.PointStruct] = []
        for chunk, vec in zip(chunks, embeddings):
            payload = {field: chunk.get(field) for field in _PAYLOAD_FIELDS}
            points.append(
                qmodels.PointStruct(
                    id=_point_id(chunk["chunk_id"]),
                    vector=vec,
                    payload=payload,
                )
            )

        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection_name,
                points=points[i : i + batch_size],
                wait=True,
            )

    # ---------- reads ----------

    def _build_filter(
        self,
        security_filter: dict | None = None,
    ) -> qmodels.Filter | None:
        must: list[qmodels.FieldCondition] = [
            qmodels.FieldCondition(
                key="org_id",
                match=qmodels.MatchValue(value=ORG_ID),
            )
        ]

        if security_filter:
            sec = security_filter.get("security_level")
            if isinstance(sec, dict):
                lte = sec.get("$lte")
                gte = sec.get("$gte")
                gt = sec.get("$gt")
                rng = qmodels.Range(
                    lte=lte if lte is not None else None,
                    gte=gte if gte is not None else None,
                    gt=gt if gt is not None else None,
                )
                must.append(qmodels.FieldCondition(key="security_level", range=rng))
            elif isinstance(sec, int):
                must.append(
                    qmodels.FieldCondition(
                        key="security_level",
                        match=qmodels.MatchValue(value=sec),
                    )
                )

        return qmodels.Filter(must=must)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        security_filter: dict | None = None,
    ) -> list[dict]:
        flt = self._build_filter(security_filter)
        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=flt,
            limit=top_k,
            with_payload=True,
        )
        results: list[dict] = []
        for hit in hits:
            payload = hit.payload or {}
            results.append({**payload, "score": float(hit.score)})
        return results

    def scroll_all(
        self,
        security_filter: dict | None = None,
        batch_size: int = 512,
    ) -> list[dict]:
        flt = self._build_filter(security_filter)
        all_points: list[dict] = []
        next_page = None
        while True:
            points, next_page = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=flt,
                limit=batch_size,
                offset=next_page,
                with_payload=True,
                with_vectors=False,
            )
            for p in points:
                if p.payload:
                    all_points.append(dict(p.payload))
            if next_page is None:
                break
        return all_points

    def count_distinct_docs(self) -> int:
        seen: set[str] = set()
        for payload in self.scroll_all():
            slug = payload.get("doc_slug")
            if slug:
                seen.add(slug)
        return len(seen)

    def get_collection_info(self) -> dict:
        info = self.client.get_collection(collection_name=self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.points_count or 0,
            "points_count": info.points_count or 0,
            "segments_count": info.segments_count or 0,
        }
