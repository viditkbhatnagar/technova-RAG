# RBAC Design - As-Implemented and As-Planned

| Field | Value |
|---|---|
| Owner | TechNova Identity and Access |
| Classification | INTERNAL |
| Last Reviewed | 2026-04-16 |
| Next Review | 2026-10-16 |
| Version | 1.0 |

---

## 1. Design Goals

TechNova RAG must retrieve from a corpus that spans four sensitivity bands without ever leaking a chunk of a document the requesting user is not cleared for. The design is constrained by three goals, listed in priority order.

### 1.1 The invariant

For every query q and every user u with clearance level c(u), no chunk drawn from a document with `security_level > c(u)` appears in any of: the retrieval result set returned to the caller, the text passed to the generation model, the citations written to Postgres, or any intermediate logging surface visible to the caller. This property is the contract of Project B. Everything else in the design is in service of this invariant.

### 1.2 Fail-closed defaults

Any missing or malformed configuration resolves to the most restrictive interpretation. A document whose filename is not present in `DOCUMENT_METADATA` is not ingested. A request whose `role` is unrecognised in `ROLE_CLEARANCE` returns zero results rather than defaulting to employee. The Qdrant client, BM25 index, or reranker failing to initialise at startup aborts `/api/query` rather than falling back to unfiltered search.

### 1.3 Defense in depth

The invariant is enforced at two independent filtering points (dense and sparse), plus a classification of the returned chunks by the generator prompt, plus a Postgres-side write of the `access_denied` flag. Each layer assumes the others may fail, so each is capable of preventing disclosure on its own. The self-correcting loop adds a fourth layer that actively probes whether a denial response should be surfaced.

---

## 2. Current Implementation - Version 1.0

The enforcement surface area lives in `backend/services/security.py` and `backend/services/retriever.py`, both wired together by the `HybridRetriever.retrieve` method and its security-aware sibling `self_correcting_retrieve`.

### 2.1 Dual pre-filter architecture

Retrieval in v1.0 runs two scoring pipelines in parallel: dense (BGE embeddings stored in Qdrant) and sparse (BM25 over tokenised chunks, pickled to `backend/bm25_index.pkl`). The two pipelines are then fused via Reciprocal Rank Fusion with k=60 and reranked with a cross-encoder before the top five results are handed to the generator.

Because the two pipelines use different indices and different data structures, a single authorization filter cannot cover both. The design therefore applies a role-derived filter at each stage, using the same single source of truth:

```python
# backend/services/security.py  (representative excerpt)

def get_security_filter(role: str) -> models.Filter:
    """
    Construct a Qdrant payload filter that restricts dense search
    to chunks whose security_level is <= the role's clearance.
    """
    clearance = ROLE_CLEARANCE.get(role, 0)
    return models.Filter(
        must=[
            models.FieldCondition(
                key="security_level",
                range=models.Range(lte=clearance),
            )
        ]
    )


def get_allowed_chunk_ids(role: str, store) -> set[str]:
    """
    Enumerate every chunk_id in Qdrant whose security_level is <=
    the role's clearance. The result is intersected with BM25 hits
    before fusion to ensure BM25 cannot surface restricted content.
    """
    clearance = ROLE_CLEARANCE.get(role, 0)
    allowed: set[str] = set()
    for point in store.scroll_all():
        if point.payload["security_level"] <= clearance:
            allowed.add(point.payload["chunk_id"])
    return allowed
```

The Qdrant filter expresses the constraint declaratively and is pushed down into the vector index. The BM25 filter is materialised as a Python set because `rank_bm25` has no native filter concept; scoring is applied to the whole corpus and the result is filtered before it contributes to RRF. In both cases the clearance is derived the same way, from the same `ROLE_CLEARANCE` dictionary and the same per-chunk `security_level` payload. Config drift between the two enforcement points is impossible by construction because there is only one config.

### 2.2 Why dual pre-filter - invariant proof sketch

Let A be the set of chunk_ids accessible to role r, and R be the complement of A (restricted). The final fused, reranked list is a function of two candidate sets: D (dense top-k) and B (BM25 top-k).

- Qdrant filter ensures D subseteq A. [dense layer]
- BM25 allow-set ensures B subseteq A. [sparse layer]
- RRF operates over D union B; union of subsets of A is a subset of A.
- Reranker reorders but does not insert new chunks.
- Generator prompt is built from the reranked top five, which is a subset of A.

Thus the final prompt contains no member of R. Removing either layer breaks the invariant: omitting the Qdrant filter lets R-chunks enter D and hence the union; omitting the BM25 filter lets R-chunks enter B. The overlap classifier that tags results as `hybrid`, `dense`, or `bm25` is downstream and does not grant access, but it gives the audit trail a quick indicator of which stage surfaced each chunk.

### 2.3 Self-correcting loop - security posture

`self_correcting_retrieve` wraps the base retrieval and reacts to a weak top-one rerank score (`weak_top1_threshold = 0.0`). When the initial call returns weak hits, the query is expanded using the `_SYNONYMS` dictionary (for example, "compensation" -> {"salary", "pay", "wage"}), and retrieval is re-run with a wider `top_k_retrieval`. The role is never modified. The clearance is never relaxed. The Qdrant filter and BM25 allow-set are recomputed with the same role, so the second attempt operates within the same authorized scope as the first.

In parallel, the function runs a restricted-space probe: the same expanded query is embedded and matched against chunks with `security_level > clearance`, purely to compute a similarity score. Chunks from this probe are never returned to the caller and never enter the prompt. The probe exists so that the system can distinguish three conditions:

1. Weak accessible hits and no strong restricted match: the question is ambiguous or out of scope. Return best-effort accessible hits.
2. Weak accessible hits and strong restricted match (cosine >= `restricted_cosine_threshold = 0.55`): the user is asking about something that exists in the corpus but is above their clearance. Emit an explicit `access_denied` response.
3. Strong accessible hits: normal flow.

Condition two is what lets Project B explain itself honestly without leaking content. The tradeoff - that the existence of restricted material is revealed - is analysed in section 8.

### 2.4 End-to-end flow

```
Request (query, role)
  |
  v
role -> clearance (ROLE_CLEARANCE.get, default 0)
  |
  +--> Qdrant dense search with get_security_filter(role)    -> D
  +--> BM25 scoring intersected with get_allowed_chunk_ids(role) -> B
  |
  v
RRF(D, B, k=60)
  |
  v
Cross-encoder rerank
  |
  v
top-5
  |
  v
If top-1 rerank < weak_top1_threshold:
    run self-correcting loop with synonym expansion
    run restricted-space probe
    if restricted cosine >= 0.55 -> emit access_denied
  |
  v
Generator prompt (or access_denied response)
  |
  v
Persist to Postgres messages: sources, retrieval_stats, access_denied
```

---

## 3. Separation of Duties

The roles below operate different controls and must not be held by the same individual for the same calendar quarter.

| Function | Responsibility | Control surface |
|---|---|---|
| Engineering | Implement and modify `backend/config.py`, `backend/services/security.py`, `backend/services/retriever.py`. | Pull request author; code owner sign-off. |
| Data Governance | Approve classification of each document and changes to `DOCUMENT_METADATA`. | Classification ticket; reviewer on PR touching `DOCUMENT_METADATA`. |
| Operations | Execute `/api/ingest` including `force_reingest` after classification change. | On-call runbook task; logged as `INGEST_START` / `INGEST_COMPLETE`. |
| Compliance | Quarterly review of role assignments and matrix attestation. | Attestation workflow; downgrades stale assignments. |
| Security | Review adversarial test harness output, sign off release. | CI artefact review; release gate. |

No single PR can land a classification change: the `DOCUMENT_METADATA` touch requires a Data Governance approver in addition to Engineering code owner.

---

## 4. Roadmap - Version 1.1

The v1.1 release replaces the client-supplied role with an authenticated identity.

### 4.1 From request body to JWT claim

The `role` field in the Project B request schema is marked deprecated. The backend instead reads a bearer JWT issued by the tenant SSO provider, verifies the signature against the IdP's JWKS, validates `iss`, `aud`, `exp`, `nbf`, and extracts role from a configurable claim (default `technova_role`). Failure to verify returns HTTP 401; missing role returns HTTP 403. The role extracted from the JWT is then fed into the same `get_security_filter` and `get_allowed_chunk_ids` functions unchanged - the enforcement surface is stable.

### 4.2 SCIM group to role mapping

SCIM 2.0 groups maintained by HRIS are mapped to TechNova roles via a tenant-scoped table. The default mapping is `TN-Admins -> admin`, `TN-Managers -> manager`, `TN-Employees -> employee`. Users without any of these groups default to no access, not to employee.

### 4.3 Admin API for role grants

A new `/api/admin/roles` endpoint allows explicit grants with audit. Requests include requestor sub, target sub, desired role, ticket reference, and justification. The endpoint writes a `ROLE_GRANT` audit event and triggers a SCIM PATCH on the IdP. Revocations use DELETE with the same envelope.

Full details of the SSO and SCIM surfaces live in `SSO_SCIM_PLAN.md`.

---

## 5. Testing the Invariant

Because there is no unit test suite in v1.0, the invariant is tested through a dedicated adversarial harness that runs as part of the pre-release gate. The harness is designed around a single formal acceptance criterion.

### 5.1 Acceptance criterion

> For every pair (r, d) where r in {employee, manager, admin} and d is a document with `security_level > ROLE_CLEARANCE[r]`, N paraphrased queries targeting d must return zero chunk_ids whose `doc_slug` corresponds to d, across every field in the response (`sources`, prompt, Postgres `messages.sources`). The target N is 50 per pair.

For v1.0 the matrix of (role, restricted doc) pairs is:

| Role | Restricted documents to probe | Pairs |
|---|---|---|
| employee | Q4_Financial_Report, Product_Roadmap_2026, Vendor_Contracts, Salary_Structure, Board_Minutes_Q4, Security_Incident_Report | 6 |
| manager | Salary_Structure, Board_Minutes_Q4, Security_Incident_Report | 3 |
| admin | (none - admin has full clearance) | 0 |

Nine pairs times fifty queries yields four hundred and fifty adversarial queries per release. The harness is deterministic: the query set is checked into `tests/adversarial/` (Roadmap - v1.1 delivers a real test directory; v1.0 stores the corpus in a spreadsheet maintained by Security).

### 5.2 Query generation

Queries are generated with three techniques:

1. Manual authoring by a security engineer who has read the restricted document.
2. Paraphrase expansion via an offline model (temperature 0.7, five paraphrases per seed).
3. Synonym-walk using the `_SYNONYMS` dictionary (to ensure the self-correcting loop does not break the invariant).

### 5.3 Pass and fail

Pass: all four hundred and fifty queries return zero restricted chunks. Fail: any single query returns any restricted chunk. A single failure blocks release and is treated as a severity-1 security bug.

Partial credit is not accepted. The invariant is binary.

---

## 6. Known Limitations

The v1.0 RBAC surface has two documented limitations. Both are accepted risks for the demo-grade release and both are resolved in v1.1.

### 6.1 Role spoofing

In v1.0 the `role` field is client-supplied in the Project B request body. Nothing prevents a caller from sending `role: "admin"` and receiving admin-cleared results. This is the single largest security gap in the current deployment and is the primary driver of the v1.1 SSO plan. The gap is mitigated operationally by deploying v1.0 only inside the corporate network behind authenticated ingress, and by treating the public internet exposure as a demonstration, not a production, surface. The frontend (`frontend/app/project-b`) exposes the role selector explicitly to make this fact obvious; the application does not pretend to authenticate.

### 6.2 Access-denied message discloses existence

When the restricted-space probe finds a strong match, the response includes an `access_denied_message` indicating that material relevant to the query exists at a higher clearance. This message does not leak the content of the restricted document, but it does confirm its existence. For a user aware of the corpus structure, this gives a minor information channel: repeated probing could confirm or disconfirm topics.

The tradeoff was accepted because the alternative - silently returning weak accessible hits - would be worse user experience and would implicitly encourage users to rephrase queries indefinitely, potentially surfacing weak but still-leaky hints. A deliberate, honest denial is the preferred behaviour for an enterprise audience. The `restricted_cosine_threshold = 0.55` is calibrated to minimise false positives; v1.1 will add per-domain thresholds once operational data accumulates.

---

## 7. Revision History

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Identity & Access | Initial release |
