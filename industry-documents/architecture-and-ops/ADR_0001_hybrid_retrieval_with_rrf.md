# ADR_0001 — Hybrid dense + BM25 retrieval with Reciprocal Rank Fusion

**Status:** Accepted 2026-02-26

**Deciders:** Platform Engineering Lead, Retrieval Systems, Security Engineering

**Date:** 2026-02-26

---

## Context

TechNova RAG serves an 11-PDF internal corpus that spans very different query styles. Analysis of pilot traffic and interviews with target users identified two distinct query shapes that a single retrieval strategy handles poorly:

1. **Semantic / paraphrased queries.** Example: "what is our onboarding flow?" — where the authoritative chunk uses "new-hire orientation process", and no shared terms exist. Dense embedding retrieval handles this cleanly because BGE-base places the two phrasings near each other in vector space.

2. **Exact-token / keyword queries.** Example: "CVE-2024-3094", specific product model numbers like "TN-4312", or internal acronyms like "SRE-P1". These are rare tokens that the embedder may not have seen at pretraining scale, and whose semantic vector is close to many unrelated specific-identifier chunks. BM25 handles these cleanly because rare tokens get high IDF.

Empirically, on a curated 30-query evaluation set built from actual user traffic:

| Strategy | Top-1 correct | MRR@5 |
|---|---|---|
| Dense only (BGE-base, Qdrant, top-10) | 19 / 30 (63%) | 0.71 |
| BM25 only (rank_bm25, top-10) | 17 / 30 (57%) | 0.64 |
| Dense + BM25, RRF fused, rerank to 5 | 27 / 30 (90%) | 0.89 |

The failure modes were complementary: dense-only missed six keyword queries; BM25-only missed seven paraphrase queries. Only two queries were missed by both, and those were later traced to chunk-boundary issues unrelated to the retrieval strategy.

Additional forces:

- **Project B security invariant.** The platform enforces role-based access at the retrieval layer (see `backend/services/security.py`). Any retrieval strategy must support pre-filtering by `security_level`, at both dense and lexical stages, so that restricted chunks never enter the scoring pool. Post-hoc filtering is unacceptable because it leaks the existence of restricted content via the scoring pool.
- **Latency budget.** Total query latency (excluding OpenAI) must stay under 900 ms p50; the retrieval stack must account for < 400 ms of that.
- **Operational cost.** The team is small; the retrieval strategy must be tractable to maintain by one engineer without specialized IR knowledge.
- **Reranker quality floor.** A cross-encoder reranker can correct a merely-good candidate list, but it cannot recover the correct answer if the top-10 dense and top-10 BM25 candidate pool does not include it. Recall, not precision, is the constraint at the retrieval stage.

Relevant code paths at the time of the decision:

- `backend/services/retriever.py::HybridRetriever.retrieve`
- `backend/services/retriever.py::_rrf_fusion`
- `backend/services/retriever.py::_rerank`
- `backend/services/security.py::get_security_filter`
- `backend/services/security.py::get_allowed_chunk_ids`

---

## Decision

TechNova RAG uses a **hybrid retrieval pipeline** composed of:

1. **Dense retrieval.** BGE-base-en-v1.5 embeddings (768-dim) over Qdrant HNSW, `top_k = 10`, cosine distance, with a payload filter on `security_level` derived from the caller's role via `ROLE_CLEARANCE`.

2. **Lexical retrieval.** rank_bm25 over the same chunks, with the candidate pool pre-restricted to the set of `chunk_id`s allowed for the caller's role (obtained via `store.scroll_all` filtered by the same role-derived security filter), `top_k = 10`.

3. **Reciprocal Rank Fusion.** The two ranked lists are fused by RRF with `k = 60`, using the canonical formula `score = 1 / (k + rank + 1)`. The fused list is deduplicated by `chunk_id`, and the `retrieval_method` field is set on each result:
   - `dense` if the chunk appeared only in the dense list,
   - `bm25` if only in the BM25 list,
   - `hybrid` if in both.
   The frontend distinguishes these exact strings for its provenance UI.

4. **Cross-encoder rerank.** The fused top-N is reranked by `cross-encoder/ms-marco-MiniLM-L-6-v2`, and the top 5 are returned as the context for generation.

### Parameter values

| Parameter | Value | Rationale |
|---|---|---|
| Embedder | `BAAI/bge-base-en-v1.5` (768-dim) | Strong English retrieval quality at modest model size; MPS-compatible. |
| Dense `top_k` | 10 | Empirically sufficient given the reranker does the final selection; larger `top_k` increased BM25 competition without improving MRR. |
| BM25 `top_k` | 10 | Matched to dense for balanced fusion. |
| RRF `k` | 60 | Canonical value from Cormack et al.; tested 40 and 80, no material change. |
| Rerank model | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Small (~90 MB), strong on passage ranking. |
| Rerank `top_k` | 5 | Limits OpenAI context size; 5 chunks × ~200 tokens fits comfortably inside the prompt budget. |

### Security invariant — dual pre-filter

The security contract requires that filtering happen at BOTH the dense and lexical stages. `backend/services/security.py::get_security_filter` is passed to Qdrant's payload-filter argument; `get_allowed_chunk_ids` returns the set of chunk ids that BM25 is allowed to score. This is not an implementation detail — it is a correctness requirement called out separately because a future refactor that moves filtering to a post-retrieval step would silently break Project B.

---

## Consequences

### Positive

- **Recall improvement** of ~27 percentage points over the strongest single strategy on the evaluation set.
- **Provenance signal** — the `retrieval_method` field is visible to users in the frontend and is a useful debug signal for retrieval quality engineering.
- **RRF is parameter-light** — no score calibration is required across the two scoring scales (cosine similarity vs. BM25 score), because only ranks are used. This is operationally important because corpus changes would otherwise require recalibrating weighted-sum hyperparameters.
- **Graceful degradation** — if the BM25 pickle is unavailable, the retriever falls back to dense-only with a metric event (`technova_bm25_fallback_total`). Users still get answers.
- **Clear primitive mapping** — each stage is one subroutine, one unit test, one dashboard panel. The pipeline is legible.

### Negative

- **Dual pipeline increases latency.** Dense (~80 ms) and BM25 (~20 ms) run in parallel, but RRF merge and dedup add ~5 ms and rerank adds ~80 ms. End-to-end retrieval budget is tight at ~200–300 ms; at Medium-tier load and without dedicated rerank hardware, this pushes p95 close to the SLO.
- **Operational burden of BM25 pickle.** `backend/bm25_index.pkl` must be kept in sync with the Qdrant collection. A partial ingest that updates one without the other creates silent quality regression. Runbook R-05 (full re-ingest) and R-07 (pickle corruption) address this; a future migration to a backed index store (Elasticsearch, v1.3 roadmap) would remove this class of issue.
- **Dual pre-filter requirement** — every retrieval code path must remember to filter at both stages. This has already caused one near-miss PR that added a new retrieval experiment without the BM25 filter. We mitigate this with a lint rule (v1.1) and with the access-denied correctness probe (SLO-8).
- **Two indices, two memory footprints.** Qdrant holds vectors; BM25 pickle duplicates the chunk tokens in its data structure. At 11 docs this is negligible (~5 MB total); at 1M chunks the BM25 pickle becomes infeasible and drives the v1.3 migration.

### Neutral

- **Tuning surface.** `top_k`, `k`, and rerank `top_k` are exposed as configuration. Changes to these require re-running the evaluation set; a regression is likely if tuned without measurement.
- **Reranker as quality gate.** The reranker corrects for mediocre candidate sets, but it cannot repair a candidate set that simply does not contain the correct chunk. Recall at the retrieval stage is what matters; rerank is precision polish.

---

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| **Dense-only with larger `top_k`** (e.g. top-30) | Reranker could not recover exact-token queries because the correct chunk was often not in the top-30 dense hits at all. Larger `top_k` also degraded rerank latency proportionally. |
| **Hybrid via weighted sum** (`α · cosine + (1−α) · BM25`) | Requires calibration of `α` against a labeled set; calibration is corpus-specific and would need re-tuning after every material corpus change. RRF sidesteps calibration entirely by using only ranks. |
| **ColBERT late-interaction** | Strong quality but requires maintaining per-token contextual embeddings, which multiplies storage ~100x and requires a custom serving path (no off-the-shelf Qdrant integration at the time of decision). Infra cost not justified for an 11-doc corpus. |
| **SPLADE (learned sparse)** | Appealing quality/cost profile but adds a model dependency (SPLADE encoder at both index and query time) and complicates the security pre-filter story. Revisit at v1.2 if BM25 proves inadequate. |
| **Qdrant native sparse vectors + dense fused server-side** | Qdrant 1.12 supports sparse vectors; however, the role-based pre-filter implementation would require duplicating the `get_allowed_chunk_ids` logic server-side. Defer until the feature matures and until we have a concrete throughput need (v1.2 roadmap). |
| **LLM-based retrieval (let the LLM do retrieval via tool calls)** | Unbounded OpenAI cost per query, worse latency, no straightforward way to enforce the Project B security invariant. Rejected on cost and security. |

---

## References

- Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). *Reciprocal Rank Fusion outperforms Condorcet and individual rank learning methods*. SIGIR '09.
- Xiong, L. et al. *BGE: Baidu General Embeddings* (https://huggingface.co/BAAI/bge-base-en-v1.5).
- `backend/services/retriever.py` — `HybridRetriever.retrieve`, `_rrf_fusion`, `_rerank`.
- `backend/services/security.py` — `get_security_filter`, `get_allowed_chunk_ids`, `self_correcting_retrieve`.
- `backend/config.py` — `SECURITY_LEVELS`, `ROLE_CLEARANCE`, `DOCUMENT_METADATA` (single source of truth for role-to-clearance mapping).
- `CONVENTIONS.md` — chunk payload schema and `chunk_id` format `technova_{doc_slug}_c{index}`.
- `MASTER_CONTEXT.md` — end-to-end design, including the reason Project B pre-filters at both stages.
- Internal evaluation set and results — ticket TR-204.

---

## Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-02-26 | TechNova Platform Engineering | Initial acceptance |
