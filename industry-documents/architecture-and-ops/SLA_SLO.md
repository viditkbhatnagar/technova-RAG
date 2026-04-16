# TechNova RAG — SLA and SLO Definition

**Owner:** TechNova Platform Engineering / SRE
**Classification:** INTERNAL
**Last Reviewed:** 2026-04-16
**Next Review:** 2026-10-16
**Version:** 1.0

---

## 1. Purpose

This document defines the service-level commitments that TechNova Platform Engineering makes to internal and external consumers of the TechNova RAG platform, and the internal objectives against which SRE operates. The SLA is contractual, external-facing, and subject to the credit matrix in section 7. The SLOs are internal and strictly tighter than the SLAs.

Scope covers the FastAPI backend, the hosted Next.js frontend, the Qdrant vector store, Neon Postgres chat history, and the end-to-end `/api/query` user journey. It explicitly excludes performance of user-provided networks and failures attributable to upstream OpenAI outages beyond the shared-dependency budget defined in section 5.

---

## 2. Service Tiers

| Tier | Availability SLA | Support | Query rate ceiling | Data residency |
|---|---|---|---|---|
| Free | 99.0% | Community, best effort | 1 rps / tenant | US default |
| Business | 99.5% | 8x5 business hours, 8h response | 10 rps / tenant | US or EU |
| Enterprise | 99.9% | 24x7 on-call, 1h response for Sev 1 | 50 rps / tenant, burst 100 | US, EU, or customer VPC |

Availability is measured at the `/api/query` endpoint over a rolling 30-day window, computed as `1 - (failed_requests / total_requests)` where a failed request is any 5xx response or a response whose end-to-end latency exceeds 10s. Requests explicitly returning 403 access-denied are counted as successful (correct behavior per Project B contract).

---

## 3. Service Level Indicators (SLIs)

The SLIs below are the ground truth for both internal SLOs and external SLA reporting. Each is emitted from the backend as a Prometheus time series.

| SLI ID | Name | Definition | Metric |
|---|---|---|---|
| SLI-1 | Query success rate | Fraction of `/api/query` requests returning 2xx within 10s | `technova_query_total{status="2xx"} / technova_query_total` |
| SLI-2 | Query latency (backend) | Server-side latency excluding OpenAI generation | `technova_retrieval_latency_seconds_bucket` |
| SLI-3 | Query latency (end-to-end) | Wall-clock including OpenAI | `technova_query_duration_seconds_bucket` |
| SLI-4 | Ingest success | Fraction of `/api/ingest` invocations completing without error | `technova_ingest_total{status}` |
| SLI-5 | Access-denied correctness | Fraction of Project B restricted probes that do NOT leak restricted content in sources | validated by hourly synthetic probe |
| SLI-6 | Graph availability | Fraction of `/api/graph` responses that return non-empty nodes | `technova_graph_response_total{empty}` |

---

## 4. Service Level Objectives (SLOs)

SLOs are the internal targets; they are tighter than the SLAs so that SRE action occurs before customer-visible breach.

| SLO ID | SLI | Target | Window | Alert threshold |
|---|---|---|---|---|
| SLO-1 | SLI-1 Query success | > 99.5% | 30d rolling | page at < 99.3% over 1h |
| SLO-2 | SLI-2 Backend latency p50 | < 900 ms | 24h rolling | ticket at > 900 ms for 15 min |
| SLO-3 | SLI-2 Backend latency p95 | < 2800 ms | 24h rolling | page at > 2800 ms for 10 min |
| SLO-4 | SLI-2 Backend latency p99 | < 5000 ms | 24h rolling | ticket at > 5000 ms for 30 min |
| SLO-5 | SLI-3 End-to-end p95 | < 4500 ms | 24h rolling | ticket at > 4500 ms for 30 min |
| SLO-6 | SLI-1 Error rate | < 1% | 30d rolling | page at > 1% for 5 min |
| SLO-7 | SLI-4 Ingest success | > 99% | 30d rolling | ticket on any failure, page at 2 consecutive |
| SLO-8 | SLI-5 Access-denied correctness | 100% | 7d rolling | page on any probe leak |
| SLO-9 | SLI-6 Graph availability | > 99% | 30d rolling | ticket at < 99% |

The latency targets are set against the current baseline of ~720 ms p50 and ~2100 ms p95 observed on an M2 Pro dev machine with MPS acceleration. Production replicas in Docker run CPU-only; the same SLOs are held, validated against shadow traffic before release gates.

### 4.1 Why p50, p95, p99 separately

The query path is bimodal: cache-warm retrieval on a small corpus averages well below 900 ms, while cross-encoder rerank on cold caches and Qdrant cold-start can spike above 2 s. Tracking only p95 hides the long-tail that affects power users who issue many queries per session.

---

## 5. Error Budget

### 5.1 Budget calculation

For an SLO of 99.5% availability over 30 days, the error budget is `0.5% × 30d × 24h = 3.6 hours` of unavailability per month. For Enterprise tier at 99.9%, the budget is 43.2 minutes per month.

### 5.2 Burn rate alerting

Burn rate is the rate at which the budget is consumed relative to its linear baseline. The multi-window multi-burn-rate policy below is implemented as Prometheus alert rules.

| Window | Burn rate | Meaning | Action |
|---|---|---|---|
| 1 hour | 14.4x | Consuming 1h of budget per 1h real time | Page primary on-call (Sev 1) |
| 6 hours | 6x | Consuming 6h of budget per 6h real time | Page primary on-call (Sev 2) |
| 3 days | 1x | Consuming budget at the baseline linear rate | Ticket; review weekly |

The 2% per hour and 10% per 6 hours practical thresholds correspond to the 14.4x and 6x burn rates above for a 99.5% SLO.

### 5.3 Budget exhaustion policy

When the 30-day error budget is more than 75% consumed with time remaining, the following policy applies:

1. All non-emergency deploys to production are frozen until the rolling window recovers above 75% remaining.
2. SRE retains unilateral authority to roll back any recent change.
3. Feature work pauses; reliability work takes precedence.
4. Weekly incident review meeting is escalated to daily until recovery.

### 5.4 Shared-dependency accounting

OpenAI outages are a shared dependency. Budget impact is accounted separately:

- If `/api/query` returns the degraded-but-contract-compliant `{answer: null, prompt, sources}` response and the frontend renders gracefully, the request counts as **successful** against SLI-1 (the backend did its job).
- If the backend times out waiting for OpenAI beyond its 10s contract, the request counts as **failed** but is tagged `shared_dependency="openai"` and reported in a separate monthly section.

This prevents OpenAI outages from unilaterally consuming the customer-facing budget while still tracking impact.

---

## 6. Exclusions

The following are explicitly excluded from SLA calculations:

| Exclusion | Rationale |
|---|---|
| Scheduled maintenance (section 9) | Announced >= 7 days in advance. |
| OpenAI-side outages | Tracked separately; see 5.4. |
| Force-majeure regional cloud outages | Excluded per standard cloud SLA cascade. |
| Customer-initiated `force_reingest` | Ingest during this window may briefly affect query quality, not availability. |
| Requests exceeding the tier rate ceiling | Rate-limited 429s do not count as failures. |
| Traffic from IPs outside the CORS allowlist | Returned without processing. |

---

## 7. SLA Credit Matrix

Applies to Business and Enterprise tiers. Credits are applied as a percentage of the monthly subscription fee.

| Monthly availability | Business tier credit | Enterprise tier credit |
|---|---|---|
| 99.5% — 100% | 0% | 0% |
| 99.0% — 99.49% | 5% | 10% |
| 98.0% — 98.99% | 10% | 25% |
| 95.0% — 97.99% | 25% | 50% |
| < 95.0% | 50% | 100% (with termination right) |

Credits must be requested in writing within 30 days of the affected month and are capped at 100% of the monthly fee.

---

## 8. Reporting

### 8.1 Customer-facing

| Artifact | Cadence | Audience |
|---|---|---|
| Monthly SLO report (PDF) | 1st business day of following month | Customer account contact |
| Incident post-mortem | Within 5 business days of any Sev 1 | Customer security and operations contacts |
| Live status page | Continuous | Public |

### 8.2 Internal

| Artifact | Cadence | Audience |
|---|---|---|
| Weekly SRE review | Monday 10:00 local | Platform Engineering, Product |
| Monthly error-budget scorecard | Last Friday | Engineering Leadership |
| Quarterly SLO revision cycle | End of Q | VP Engineering sign-off |

---

## 9. Measurement Infrastructure

### 9.1 Server-side

- **Prometheus histograms** emitted from each stage in `backend/services/retriever.py`:
  - `technova_retrieval_latency_seconds_bucket{stage="embed"}`
  - `technova_retrieval_latency_seconds_bucket{stage="dense"}`
  - `technova_retrieval_latency_seconds_bucket{stage="bm25"}`
  - `technova_retrieval_latency_seconds_bucket{stage="rrf"}`
  - `technova_retrieval_latency_seconds_bucket{stage="rerank"}`
  - `technova_retrieval_latency_seconds_bucket{stage="generate"}`
- **Counters**: `technova_query_total{status, role, access_denied}`, `technova_access_denied_total{role, reason}`.
- Emitted via `prometheus_client` middleware (v1.1 — currently prototyped as print-statement timings in `backend/routers/query.py`).

### 9.2 Synthetic probes

Every 60 seconds a probe runner executes a fixed set of canary queries against `/api/query` in all regions. The probe suite includes:

1. Ten semantic queries covering each document in the corpus.
2. Five exact-token queries for the BM25 path.
3. Five Project B restricted-probe queries that must return access-denied.

Failure of any probe triggers the corresponding SLI.

### 9.3 Real User Monitoring

The frontend emits end-to-end timing from the browser via `web-vitals` and a lightweight `fetch` wrapper in `frontend/lib/api.ts`. RUM latency is the truth for SLO-5 end-to-end.

### 9.4 Access-denied correctness (SLI-5)

A dedicated hourly job reads the list of restricted chunk IDs from the Qdrant payload filter, issues queries from each Project B role, and asserts:

1. No restricted chunk ID appears in the `sources` array.
2. `access_denied` is true when and only when the restricted probe matches the query better than the accessible pool (threshold from `backend/services/security.py`, `restricted_cosine_threshold = 0.55`).

Any violation pages on-call immediately.

---

## 10. Maintenance Windows

| Window | Cadence | Duration | Scope |
|---|---|---|---|
| Standard | First Sunday of month, 02:00–04:00 UTC | 2h | Dependency patching, Qdrant minor version, Next.js patch |
| Extended | As needed, announced 14 days in advance | up to 4h | Major Qdrant upgrade, Postgres major version, model upgrade |
| Emergency | Announced as soon as feasible | as needed | CVE-driven patch; exempt from notice requirement per tier |

Time spent in standard and extended windows is excluded from SLA calculations per section 6. Emergency maintenance is excluded only when triggered by a disclosed CVE with a CVSS score >= 7.0.

---

## 11. Baseline Observations (2026-04)

Current observed metrics from the dev environment (M2 Pro, 16 GB, MPS embed) on a 400-chunk corpus, sampled over a week of internal usage:

| Metric | Observed | SLO target |
|---|---|---|
| Query p50 (backend) | 720 ms | < 900 ms |
| Query p95 (backend) | 2100 ms | < 2800 ms |
| Query p99 (backend) | 3900 ms | < 5000 ms |
| OpenAI p50 | 640 ms | n/a (shared) |
| OpenAI p95 | 1400 ms | n/a (shared) |
| End-to-end p50 | 1360 ms | n/a |
| End-to-end p95 | 3500 ms | < 4500 ms |
| Ingest cold (400 chunks) | 42 s | n/a |
| Access-denied correctness | 100% | 100% |

The production Docker topology (CPU-only, no MPS) is expected to increase backend p50 by ~15–25% on embed and rerank; this is within the SLO budget but must be re-baselined after the first week of production traffic.

---

## 12. Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Platform Engineering | Initial release |
