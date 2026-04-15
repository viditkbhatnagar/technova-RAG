"""Hybrid retriever: Dense + BM25 + RRF + Cross-Encoder reranking."""

import time

from sentence_transformers import CrossEncoder

from backend.services.bm25_index import BM25Index
from backend.services.embedder import EmbeddingService, get_device
from backend.services.store import QdrantStore


class RetrievalError(Exception):
    pass


class HybridRetriever:
    def __init__(
        self,
        store: QdrantStore,
        bm25: BM25Index,
        embedder: EmbeddingService,
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ):
        self.store = store
        self.bm25 = bm25
        self.embedder = embedder
        self.reranker_name = reranker_model
        self.reranker_device = get_device()
        self.reranker = CrossEncoder(reranker_model, device=self.reranker_device)
        print(
            f"[retriever] loaded reranker {reranker_model} on {self.reranker_device}"
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        top_k_retrieval: int = 10,
        rrf_k: int = 60,
        security_filter: dict | None = None,
        allowed_chunk_ids: set[str] | None = None,
    ) -> dict:
        """Run the full hybrid retrieval pipeline.

        Returns a dict with:
          - chunks: final reranked top_k chunks
          - stats: dense_results, bm25_results, rrf_merged, reranked_final,
                   overlap_count, avg_rerank_score, retrieval_time_ms
        """
        t0 = time.perf_counter()

        query_vec = self.embedder.embed_query(query)
        dense_results = self.store.search(
            query_embedding=query_vec,
            top_k=top_k_retrieval,
            security_filter=security_filter,
        )

        bm25_results = self.bm25.search(
            query=query,
            top_k=top_k_retrieval,
            allowed_chunk_ids=allowed_chunk_ids,
        )

        fused = self._rrf_fusion(dense_results, bm25_results, k=rrf_k)

        dense_ids = {r["chunk_id"] for r in dense_results}
        bm25_ids = {r["chunk_id"] for r in bm25_results}
        overlap = len(dense_ids & bm25_ids)

        rerank_pool = fused[: max(top_k_retrieval, top_k)]
        reranked = self._rerank(query, rerank_pool, top_k=top_k) if rerank_pool else []

        avg_rerank = (
            sum(c.get("rerank_score", 0.0) for c in reranked) / len(reranked)
            if reranked
            else 0.0
        )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        return {
            "chunks": reranked,
            "stats": {
                "dense_results": len(dense_results),
                "bm25_results": len(bm25_results),
                "rrf_merged": len(fused),
                "reranked_final": len(reranked),
                "overlap_count": overlap,
                "avg_rerank_score": round(float(avg_rerank), 4),
                "retrieval_time_ms": elapsed_ms,
            },
        }

    # ---------- fusion ----------

    def _rrf_fusion(
        self,
        dense_results: list[dict],
        bm25_results: list[dict],
        k: int = 60,
    ) -> list[dict]:
        scores: dict[str, float] = {}
        metadata: dict[str, dict] = {}

        for rank, result in enumerate(dense_results):
            cid = result["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            if cid not in metadata:
                entry = dict(result)
                entry["retrieval_method"] = "dense"
                metadata[cid] = entry

        for rank, result in enumerate(bm25_results):
            cid = result["chunk_id"]
            if cid in metadata:
                metadata[cid]["retrieval_method"] = "hybrid"
            else:
                entry = dict(result)
                entry["retrieval_method"] = "bm25"
                metadata[cid] = entry
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        fused: list[dict] = []
        for cid, score in ranked:
            entry = dict(metadata[cid])
            entry["rrf_score"] = float(score)
            fused.append(entry)
        return fused

    # ---------- reranking ----------

    def _rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        if not candidates:
            return []
        pairs = [(query, c["text"]) for c in candidates]
        scores = self.reranker.predict(pairs, show_progress_bar=False)
        scored = []
        for cand, score in zip(candidates, scores):
            entry = dict(cand)
            entry["rerank_score"] = float(score)
            scored.append(entry)
        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_k]
