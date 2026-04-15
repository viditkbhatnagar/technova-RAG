"""Role-based security filter + self-correcting retrieval loop."""

from backend.config import ROLE_CLEARANCE
from backend.services.retriever import HybridRetriever
from backend.services.store import QdrantStore


_SYNONYMS: dict[str, list[str]] = {
    "salary": ["compensation", "pay", "remuneration"],
    "bonus": ["incentive", "variable pay"],
    "leave": ["time off", "vacation"],
    "policy": ["guideline", "rule"],
    "incident": ["breach", "event"],
    "roadmap": ["plan", "strategy"],
}


def get_security_filter(role: str) -> dict:
    """Return a pre-filter dict for the given role (security_level <= clearance)."""
    if role not in ROLE_CLEARANCE:
        raise ValueError(f"Unknown role: {role}")
    return {"security_level": {"$lte": ROLE_CLEARANCE[role]}}


def get_allowed_chunk_ids(store: QdrantStore, role: str) -> set[str]:
    """All chunk_ids visible to this role. Used to filter BM25."""
    flt = get_security_filter(role)
    points = store.scroll_all(security_filter=flt)
    return {p["chunk_id"] for p in points if "chunk_id" in p}


def _expand_query(query: str) -> str:
    q_lower = query.lower()
    extras: list[str] = []
    for key, syns in _SYNONYMS.items():
        if key in q_lower:
            extras.extend(syns)
    if not extras:
        return query
    return f"{query} {' '.join(extras)}"


def self_correcting_retrieve(
    retriever: HybridRetriever,
    store: QdrantStore,
    query: str,
    role: str,
    top_k: int = 5,
    top_k_retrieval: int = 10,
    rrf_k: int = 60,
    weak_top1_threshold: float = 0.0,
    restricted_cosine_threshold: float = 0.55,
) -> dict:
    """Secure retrieval with a self-correcting loop.

    - Always applies security pre-filter by role clearance.
    - If the top-1 accessible chunk has a weak cross-encoder score, try an
      expanded query with a wider retrieval window.
    - Never relaxes the security clearance.
    - Deny access only when accessible retrieval is clearly weak AND the
      restricted space has a strong semantic match the user can't reach.
    """
    security_filter = get_security_filter(role)
    allowed_ids = get_allowed_chunk_ids(store, role)

    result = retriever.retrieve(
        query=query,
        top_k=top_k,
        top_k_retrieval=top_k_retrieval,
        rrf_k=rrf_k,
        security_filter=security_filter,
        allowed_chunk_ids=allowed_ids,
    )
    stats = result["stats"]
    stats["self_correction_applied"] = False

    def _top1(r: dict) -> float:
        chunks = r.get("chunks") or []
        if not chunks:
            return float("-inf")
        return float(chunks[0].get("rerank_score", 0.0))

    # Probe restricted space (informational only, never returned as content)
    query_vec = retriever.embedder.embed_query(query)
    restricted_hits = store.search(
        query_embedding=query_vec,
        top_k=10,
        security_filter={"security_level": {"$gt": ROLE_CLEARANCE[role]}},
    )
    strong_restricted = [
        h for h in restricted_hits if h.get("score", 0.0) >= restricted_cosine_threshold
    ]
    restricted_exists = len(strong_restricted) > 0
    restricted_count = len({h.get("doc_slug") for h in strong_restricted if h.get("doc_slug")})
    top_restricted_cosine = max((h.get("score", 0.0) for h in restricted_hits), default=0.0)
    stats["restricted_docs_exist"] = restricted_exists
    stats["restricted_doc_count"] = restricted_count
    stats["top_restricted_cosine"] = round(float(top_restricted_cosine), 4)

    # Weak accessible retrieval → try expanded query with wider top_k
    if _top1(result) < weak_top1_threshold:
        expanded = _expand_query(query)
        if expanded != query:
            wider = retriever.retrieve(
                query=expanded,
                top_k=top_k,
                top_k_retrieval=max(15, top_k_retrieval + 5),
                rrf_k=rrf_k,
                security_filter=security_filter,
                allowed_chunk_ids=allowed_ids,
            )
            if _top1(wider) > _top1(result):
                result = wider
                stats = result["stats"]
                stats["self_correction_applied"] = True
                stats["expanded_query"] = expanded
                stats["restricted_docs_exist"] = restricted_exists
                stats["restricted_doc_count"] = restricted_count
                stats["top_restricted_cosine"] = round(float(top_restricted_cosine), 4)
            else:
                stats["self_correction_applied"] = True
                stats["expanded_query"] = expanded

    # Access-denied heuristic: only when accessible retrieval is clearly weak
    # AND restricted space has a strong match the user can't reach.
    # - top-1 rerank < 0 means the cross-encoder considers even the best
    #   accessible chunk to be off-topic for this query.
    # - top restricted cosine >= restricted_cosine_threshold means the
    #   restricted corpus has a genuinely relevant doc.
    access_denied = False
    access_denied_message = None
    top1_accessible = _top1(result)
    if not result["chunks"] and restricted_exists:
        access_denied = True
    elif restricted_exists and top1_accessible < weak_top1_threshold:
        access_denied = True

    if access_denied:
        access_denied_message = (
            f"Relevant information exists in {restricted_count} document(s) "
            "that require higher clearance. Contact your department head for access."
        )

    return {
        "chunks": result["chunks"] if not access_denied else [],
        "stats": stats,
        "access_denied": access_denied,
        "access_denied_message": access_denied_message,
    }
