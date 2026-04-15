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


def check_restricted_docs_exist(
    store: QdrantStore,
    query_embedding: list[float],
    role: str,
    probe_top_k: int = 10,
    relevance_threshold: float = 0.35,
) -> tuple[bool, int]:
    """Peek above the user's clearance to see if restricted docs would have matched.

    Used ONLY to inform the access-denied message — never to leak content.
    Returns (exists, distinct_doc_count).
    """
    user_level = ROLE_CLEARANCE[role]
    above_filter = {"security_level": {"$gt": user_level}}
    hits = store.search(
        query_embedding=query_embedding,
        top_k=probe_top_k,
        security_filter=above_filter,
    )
    relevant = [h for h in hits if h.get("score", 0.0) >= relevance_threshold]
    distinct_docs = {h.get("doc_slug") for h in relevant if h.get("doc_slug")}
    return (len(relevant) > 0, len(distinct_docs))


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
    min_relevance: float = 0.3,
) -> dict:
    """Secure retrieval with a self-correcting loop.

    - Always applies security pre-filter by role clearance.
    - If average rerank score < min_relevance, expand query + widen top_k and retry.
    - Never relaxes the security clearance.
    - Checks whether restricted docs above the user's clearance would match;
      if retrieval was weak and restricted matches exist, flag access_denied.
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

    avg_score = stats.get("avg_rerank_score", 0.0)

    # Probe restricted space (informational only, never returned as content)
    query_vec = retriever.embedder.embed_query(query)
    restricted_exists, restricted_count = check_restricted_docs_exist(
        store=store, query_embedding=query_vec, role=role
    )
    stats["restricted_docs_exist"] = restricted_exists
    stats["restricted_doc_count"] = restricted_count

    # Weak retrieval → try expanded query with wider top_k
    if avg_score < min_relevance:
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
            stats["self_correction_applied"] = True
            stats["expanded_query"] = expanded
            if wider["stats"].get("avg_rerank_score", 0.0) > avg_score:
                result = wider
                stats = result["stats"]
                stats["self_correction_applied"] = True
                stats["expanded_query"] = expanded
                stats["restricted_docs_exist"] = restricted_exists
                stats["restricted_doc_count"] = restricted_count

    # Access-denied heuristic: no accessible chunks, OR weak retrieval while
    # restricted docs clearly match the query.
    access_denied = False
    access_denied_message = None
    if not result["chunks"] and restricted_exists:
        access_denied = True
    elif restricted_exists and stats.get("avg_rerank_score", 0.0) < min_relevance:
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
