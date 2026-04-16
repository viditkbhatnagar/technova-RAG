# TechNova RAG — Observability Plan

**Owner:** TechNova Platform Engineering / SRE
**Classification:** INTERNAL
**Last Reviewed:** 2026-04-16
**Next Review:** 2026-10-16
**Version:** 1.0

---

## 1. Intent

Observability is the ability to ask an arbitrary question about the production system and get an answer from the telemetry, without shipping new code. For TechNova RAG, the questions that matter fall in four classes:

1. **Is the system up and fast?** — SLO queries.
2. **Is it returning the right answers?** — retrieval quality and access-denied correctness.
3. **Is it under attack or being probed?** — security posture.
4. **Where does the money go?** — vendor usage, especially OpenAI tokens.

This plan defines the three-pillar observability stack (metrics, logs, traces), the specific signals TechNova emits, the dashboards built on top, and the PII boundary that the telemetry must respect.

---

## 2. Pillars

| Pillar | Stack (v1.1 target) | v1.0 status |
|---|---|---|
| Metrics | Prometheus + Grafana (self-hosted or Grafana Cloud) | Partial: per-stage timings currently emitted via print statements in `backend/routers/query.py` and `backend/services/retriever.py`; Prometheus exporter not yet wired. |
| Logs | Structured JSON logs → Loki (self-hosted) or CloudWatch / Datadog Logs | Partial: Python logging with unstructured strings; structured JSON scheme not yet applied. |
| Traces | OpenTelemetry SDK → Tempo or Datadog APM | Not implemented in v1.0. |

**Implementation status.** v1.0 ships functional endpoint timings and a working `/api/status` but does not have Prometheus scrape or OTel wiring. The plan below is the v1.1 target; everything described in sections 3–6 is the contract against which the v1.1 instrumentation work is scoped.

---

## 3. Metrics

Prometheus metric naming follows the `technova_<subsystem>_<name>_<unit>` convention. All metrics are exported from the FastAPI process via `prometheus_client.make_asgi_app()` mounted at `/metrics`, protected by a basic auth credential so it is not publicly scrapable.

### 3.1 Retrieval pipeline

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `technova_retrieval_latency_seconds` | Histogram | `stage={embed,dense,bm25,rrf,rerank,generate}` | Per-stage latency distribution |
| `technova_query_duration_seconds` | Histogram | `role, access_denied` | End-to-end query latency |
| `technova_query_total` | Counter | `status, role, access_denied` | Total queries and their outcomes |
| `technova_rerank_top1_score` | Histogram | `role` | Distribution of rerank top-1 score (a leading indicator of retrieval quality) |
| `technova_retrieval_method_total` | Counter | `method={dense,bm25,hybrid}` | How often each retrieval path contributed to the top-5 — operationalizes the RRF behavior documented in `backend/services/retriever.py` |
| `technova_rrf_overlap_ratio` | Histogram | (none) | Fraction of top-5 that came from both dense and BM25 (hybrid) — dips indicate index drift or query-language shift |

### 3.2 Security

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `technova_access_denied_total` | Counter | `role, reason={restricted_probe_stronger, role_not_allowed}` | Access-denied events; the primary signal for SLI-5 |
| `technova_restricted_probe_hits_total` | Counter | `role` | How often the informational restricted probe in `security.self_correcting_retrieve` found a strong match (never surfaced to user) |
| `technova_self_correcting_iterations` | Histogram | `role` | Iteration count in the self-correcting loop |

### 3.3 External dependencies

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `technova_openai_tokens_total` | Counter | `direction={in,out}, model` | Token consumption — feeds the cost dashboard |
| `technova_openai_latency_seconds` | Histogram | `model` | OpenAI round-trip latency |
| `technova_openai_errors_total` | Counter | `status, model` | Rate limits and outages |
| `technova_qdrant_latency_seconds` | Histogram | `operation={search,upsert,scroll}` | Qdrant performance |
| `technova_qdrant_up` | Gauge | (none) | 0/1 health |
| `technova_postgres_write_errors_total` | Counter | `table` | Chat history persistence health |
| `technova_hf_model_load_seconds` | Histogram | `model_name` | Model startup time (cold vs. warm cache) |

### 3.4 Ingest

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `technova_ingest_duration_seconds` | Histogram | `force_reingest` | Ingest wall-clock |
| `technova_ingest_total` | Counter | `status={ok,error}` | Ingest attempts |
| `technova_ingest_chunks_indexed` | Gauge | (none) | Current corpus chunk count — same number as `/api/status` reports |
| `technova_bm25_rebuild_seconds` | Histogram | (none) | BM25 index rebuild time |
| `technova_graph_build_seconds` | Histogram | (none) | Knowledge graph build time |

### 3.5 Application

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `technova_http_requests_total` | Counter | `method, route, status` | Raw HTTP counts |
| `technova_http_duration_seconds` | Histogram | `route` | Per-route latency |
| `technova_sessions_active` | Gauge | (none) | Count of sessions updated in last 5 minutes |

---

## 4. Log Schema

Logs are structured JSON emitted to stdout by the FastAPI process and shipped to the log aggregator by the container runtime. Every log line has the following shape.

```json
{
  "timestamp": "2026-04-16T14:22:08.413Z",
  "level": "info",
  "service": "technova-backend",
  "version": "1.0.3",
  "request_id": "8f3e0d...",
  "session_id": "7a1c...",
  "role": "engineer",
  "event": "query_completed",
  "elapsed_ms": 823,
  "retrieval_stats": {
    "dense_hits": 10,
    "bm25_hits": 10,
    "rrf_fused": 18,
    "rerank_top1_score": 0.74,
    "retrieval_methods": {"dense": 2, "bm25": 1, "hybrid": 2}
  },
  "chunk_ids_hashed": ["h1...", "h2...", "h3...", "h4...", "h5..."],
  "access_denied": false,
  "openai_model": "gpt-4o-mini",
  "openai_tokens": {"in": 1521, "out": 284}
}
```

### 4.1 Field contract

| Field | Source | PII? |
|---|---|---|
| `request_id` | Generated per request (UUID v4) | No |
| `session_id` | Postgres sessions.id | No (opaque UUID) |
| `role` | From request | No |
| `event` | Semantic marker — `query_started`, `query_completed`, `access_denied`, `ingest_started`, `ingest_completed`, etc. | No |
| `chunk_ids_hashed` | SHA-256 of `chunk_id`, truncated to 16 hex | No |
| `retrieval_stats` | Structured snapshot from retriever | No |
| `query_text` | **NOT logged** at default level | Yes — forbidden at INFO |
| `chunk_text` | **NOT logged** at default level | Yes — forbidden at INFO |
| `answer_text` | **NOT logged** at default level | Yes — forbidden at INFO |

### 4.2 Log levels

| Level | Usage |
|---|---|
| DEBUG | Full query text, chunk text, prompt — enabled only in dev or under a time-limited investigation flag |
| INFO | Normal operation events — never includes PII |
| WARN | Recoverable anomalies (BM25 fallback, self-correcting loop triggered, OpenAI retry) |
| ERROR | Failures — never includes raw user input in the body |
| CRITICAL | Startup failures, security-invariant violations |

### 4.3 Retention

| Tier | Hot (searchable) | Cold (archival) |
|---|---|---|
| Default | 30 days | 1 year (S3 glacier) |
| Security events | 1 year | 7 years |
| Audit trail (Project B access-denied) | 7 years | 7 years |

Access-denied events are special-cased into a dedicated `security-audit` log stream with immutable storage (S3 Object Lock).

---

## 5. Tracing

Every request is traced with OpenTelemetry. Traces propagate from the browser via the W3C `traceparent` header set in `frontend/lib/api.ts`.

### 5.1 Span graph

```
http.server /api/query
├── security.role_filter
├── retriever.retrieve
│   ├── embedder.embed
│   ├── qdrant.search (dense, top_k=10)
│   ├── bm25.search (top_k=10)
│   ├── retriever.rrf_fuse (k=60)
│   └── reranker.rerank (top_k=5)
├── generator.generate
│   └── openai.chat.completions.create
└── chat_store.persist_message × 2
    └── postgres.insert
```

### 5.2 Span attributes

| Attribute | Example | Notes |
|---|---|---|
| `technova.role` | `engineer` | On root span |
| `technova.access_denied` | `false` | On root span |
| `technova.retrieval.dense_hits` | `10` | On retriever span |
| `technova.retrieval.rerank_top1` | `0.74` | On retriever span |
| `openai.model` | `gpt-4o-mini` | On generator span |
| `openai.tokens.in` / `openai.tokens.out` | integers | On generator span |
| `db.system` / `db.operation` | `postgresql` / `INSERT` | On postgres spans |

Span attributes never contain raw query text or chunk text.

### 5.3 Sampling

- 100% sampling for errors (failed spans).
- 10% head sampling for 2xx responses.
- 100% sampling for traces tagged `technova.access_denied=true` (important for audit).

---

## 6. Dashboards

Four canonical dashboards, each with a single explicit purpose. Dashboards are version-controlled as JSON under `infra/grafana/` (v1.1).

### 6.1 Query Performance

- p50/p95/p99 of `technova_query_duration_seconds`
- Per-stage latency stacked bars (`technova_retrieval_latency_seconds` by stage)
- Top-5 slowest routes (`technova_http_duration_seconds` by route)
- Backend replica count and CPU utilization
- Error rate by status class

### 6.2 Retrieval Quality

- Distribution of `technova_rerank_top1_score` (histogram heatmap)
- `technova_retrieval_method_total` breakdown — dense vs bm25 vs hybrid share
- `technova_rrf_overlap_ratio` over time — dip alerts on index drift
- Self-correcting loop iteration histogram
- Canary query pass rate (synthetic probes)

### 6.3 Security Posture

- `technova_access_denied_total` by role and reason
- `technova_restricted_probe_hits_total` — rare by design
- Access-denied rate anomaly detector (baseline from 7-day rolling mean)
- Top 10 sessions by access-denied count (potential reconnaissance)
- Access-denied correctness probe pass rate (must be 100%)

### 6.4 Model and Vendor Health

- `technova_openai_tokens_total` by direction (fuels cost tracking)
- `technova_openai_latency_seconds` p50/p95
- `technova_openai_errors_total` by status
- `technova_qdrant_up` gauge + operation latency
- `technova_postgres_write_errors_total`
- Cumulative monthly OpenAI spend projection (derived from tokens × price)

---

## 7. SLO Burn Alerts

Alerts map to two destinations based on severity. SLO burn uses multi-window multi-burn-rate rules as specified in `SLA_SLO.md` section 5.2.

| Alert | Severity | Destination |
|---|---|---|
| SLO-1 Query success burn 14.4x over 1h | Sev 1 | Page on-call |
| SLO-1 Query success burn 6x over 6h | Sev 2 | Page on-call |
| SLO-3 p95 > 2800 ms for 10 min | Sev 2 | Page on-call |
| SLO-2 p50 > 900 ms for 15 min | Sev 3 | Ticket |
| SLO-7 Ingest success failure (2 consecutive) | Sev 2 | Page on-call |
| SLO-8 Access-denied probe leak | Sev 1 | Page on-call + Security |
| Postgres write errors rate > 1/s for 5 min | Sev 2 | Page on-call |
| OpenAI 5xx rate > 5% for 10 min | Sev 3 | Ticket (shared-dependency) |
| Qdrant RAM > 85% | Sev 3 | Ticket |
| Access-denied rate > 5x 7d baseline | Sev 2 | Page on-call (security) |

Alert definitions live in `infra/prometheus/alerts.yml` (v1.1).

---

## 8. PII and Data Hygiene

The system operates over internal documents that may contain personal data. The observability contract is conservative by default.

### 8.1 Default exclusions (INFO and below)

- Raw query text
- Raw retrieved chunk text
- Raw LLM answer text
- Any document content

These fields are available at DEBUG level only, gated by a time-limited investigation flag (`LOG_DEBUG_TTL_MINUTES` set by SRE) and scoped to a specific `session_id`.

### 8.2 Identifier hygiene

- `chunk_id` values in metrics labels are forbidden (high cardinality); chunks are referenced only by hash in logs.
- Session IDs are opaque UUIDs, not user-identifiable. The join between `session_id` and user identity is held only in Postgres `sessions.user_id` and is not exported to metrics or logs.
- IP addresses in access logs are retained for 30 days and then truncated to /24 (IPv4) or /48 (IPv6).

### 8.3 Right-to-erasure

When a user requests erasure, the deletion job:

1. Removes their rows from `sessions` and `messages` in Postgres.
2. Purges log entries matching `session_id` in the last 30 days (older cold logs are purged on next quarterly cycle).
3. No Qdrant deletion is required (chunks do not contain user identifiers).

---

## 9. Appendix — Example PromQL

```promql
# p95 backend-only latency over last 5 minutes
histogram_quantile(
  0.95,
  sum by (le) (rate(technova_query_duration_seconds_bucket[5m]))
)

# Per-stage latency contribution (p50), last 5 minutes
histogram_quantile(
  0.50,
  sum by (le, stage) (rate(technova_retrieval_latency_seconds_bucket[5m]))
)

# Query success rate over 30 days (SLI-1)
1 - (
  sum(rate(technova_query_total{status=~"5.."}[30d]))
  / sum(rate(technova_query_total[30d]))
)

# Retrieval method distribution over last hour
sum by (method) (rate(technova_retrieval_method_total[1h]))

# Access-denied rate anomaly vs 7-day baseline
sum(rate(technova_access_denied_total[15m]))
/
avg_over_time(sum(rate(technova_access_denied_total[15m]))[7d:15m])

# OpenAI monthly spend projection from token counters
(
  sum(increase(technova_openai_tokens_total{direction="in", model="gpt-4o-mini"}[30d])) * 0.15 / 1e6
)
+
(
  sum(increase(technova_openai_tokens_total{direction="out", model="gpt-4o-mini"}[30d])) * 0.60 / 1e6
)

# Rerank top-1 score distribution drift (p50 moving week-over-week)
avg_over_time(
  histogram_quantile(0.5, sum by (le) (rate(technova_rerank_top1_score_bucket[1h])))[1w:1h]
)
```

---

## 10. Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Platform Engineering | Initial release |
