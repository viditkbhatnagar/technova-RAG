# TechNova RAG — Capacity and Cost Model

**Owner:** TechNova Platform Engineering / Finance Ops
**Classification:** INTERNAL
**Last Reviewed:** 2026-04-16
**Next Review:** 2026-10-16
**Version:** 1.0

---

## 1. Purpose

This document provides the unit economics for TechNova RAG, an end-to-end cost model across three load tiers, an enumeration of the bottlenecks that appear as load scales, and the capacity plan with monitoring thresholds that drive scaling actions. The target audience is engineering leadership, finance operations, and customer-facing teams who need to price and size deployments.

All numbers are grounded in observed production-parity measurements on the current 11-PDF corpus (~400 chunks) and in current-quarter list prices from the respective vendors. Prices are in USD. Tax and egress between AWS regions are excluded unless called out; they typically add 5–10% and are captured in the "misc" line.

---

## 2. Unit Economics — Cost per 1000 Queries

The canonical unit is a single `/api/query` round-trip. A query's cost decomposes into five components.

### 2.1 Component costs per query

| Component | Resource | Per-query | Source |
|---|---|---|---|
| OpenAI input tokens | gpt-4o-mini, ~1500 tokens (system + 5 chunks of ~200 tokens + question) | $0.000225 | $0.15 per 1M input tokens |
| OpenAI output tokens | gpt-4o-mini, ~300 tokens | $0.00018 | $0.60 per 1M output tokens |
| Embedding | BGE-base local, CPU-bound, ~30 ms | amortized to compute line | Self-hosted |
| Qdrant search | One ANN over ~400 vectors | amortized to compute line | Qdrant Cloud or self-host |
| Reranker | cross-encoder/MiniLM, 10 docs, ~80 ms CPU | amortized to compute line | Self-hosted |
| Backend compute | ~1 s CPU-wall-clock | varies by instance | See tier breakdowns |
| Postgres writes | 2 inserts (user + assistant message) | negligible per query | |

**Dominant cost** at all scales is OpenAI: `$0.000225 + $0.00018 = $0.000405` per query. That is **$0.405 per 1000 queries** for the LLM alone.

### 2.2 Sensitivity

| Assumption shift | Δ OpenAI cost per 1000 queries |
|---|---|
| Double context (10 chunks instead of 5) | +$0.225 (→ $0.63) |
| Double output (600 tokens) | +$0.18 (→ $0.585) |
| Drop rerank top-k to 3 | −$0.09 (→ $0.315) |
| Upgrade to gpt-4o full | ~10x → $4.05 |
| Downgrade to gpt-4o-mini with prompt caching (50% cache hit) | ~50% input side → $0.292 |

Prompt caching is a meaningful lever: with OpenAI's prompt caching, the system message and static instructions can be cached at $0.075 per 1M tokens, roughly halving the input bill for high-volume tenants with a stable prompt prefix. This is tracked as a v1.1 optimization.

---

## 3. Load Tiers

The three tiers below are used for sizing and cost projections. A real customer may sit between tiers; interpolate linearly on query volume.

| Tier | Queries/month | Concurrent users (peak) | Queries per second (peak) | Session cardinality |
|---|---|---|---|---|
| Low | 1,000 | 10 | 0.3 | ~100 |
| Medium | 50,000 | 250 | 7 | ~5,000 |
| High | 500,000 | 5,000 | 70 | ~50,000 |

Peak QPS is derived by assuming business-hour traffic concentrated in 8 hours over 22 working days: `queries / (22 × 8 × 3600) × burst_factor(3)` for peak.

---

## 4. Monthly Cost Estimate per Tier

### 4.1 Low tier (1K queries / month, 10 users)

| Line | Assumption | Monthly cost |
|---|---|---|
| OpenAI gpt-4o-mini | 1000 queries × $0.000405 | $0.41 |
| Qdrant | Self-host on t3.small (2 vCPU / 2 GB), single node, 8 GB EBS | $17.00 |
| Neon Postgres | Business starter, ~1 GB storage, ~2 CAU-h/day, scale-to-zero idle | $5.00 |
| Vercel | Hobby (free) for dev, Pro $20 if production | $0 (Hobby) |
| Backend compute | Single t3.small FastAPI replica, on-demand | $17.00 |
| Misc (egress, logs, monitoring) | | $5.00 |
| **Total** | | **~$44** |

The expected total is **~$25** if Postgres and Qdrant are shared across tenants on a pooled plan, or if Postgres scale-to-zero is aggressive. For a dedicated single-tenant Low deployment, $44 is realistic.

### 4.2 Medium tier (50K queries / month, 250 users)

| Line | Assumption | Monthly cost |
|---|---|---|
| OpenAI gpt-4o-mini | 50,000 × $0.000405 | $20 |
| Qdrant | Qdrant Cloud, 2 GB cluster, HA pair | $95 |
| Neon Postgres | Business scale, 10 GB, ~30 CAU-h/day | $65 |
| Vercel | Pro plan for production | $20 |
| Backend compute | 2 × t3.medium (4 vCPU / 4 GB) replicas | $60 |
| Reranker / embedder | on the backend instances (no separate node) | included |
| Misc (egress, logs, monitoring, Sentry, StatusPage) | | $140 |
| **Total** | | **~$400** |

Expected total **~$400**. The misc line absorbs monitoring and observability: Prometheus + Grafana Cloud Starter ~$50, Sentry Team ~$26, StatusPage starter ~$29, and ~$35 of S3 + bandwidth.

### 4.3 High tier (500K queries / month, 5000 users)

| Line | Assumption | Monthly cost |
|---|---|---|
| OpenAI gpt-4o-mini | 500,000 × $0.000405 | $200 |
| OpenAI prompt-caching offset | 50% cache hit on system prompt | −$50 |
| Qdrant | Qdrant Cloud, 16 GB cluster, 3-node HA | $900 |
| Neon Postgres | Enterprise, 100 GB, autoscale 8 CU | $650 |
| Vercel | Enterprise | $600 |
| Backend compute | 6 × c6i.xlarge replicas behind ALB | $720 |
| Reranker dedicated GPU node | 1 × g5.xlarge (A10G), shared across replicas | $370 |
| Monitoring (Grafana Cloud Pro, Datadog APM, PagerDuty, Sentry) | | $450 |
| Misc (egress, S3, backups) | | $200 |
| **Total** | | **~$4,040** |

Expected total **~$3,500–$4,000**. The range depends on whether the reranker runs on CPU (cheaper, slower) or on a shared GPU node (the breakdown above assumes GPU). Prompt caching saves enough on OpenAI that it pays for itself before we reach Enterprise volumes.

### 4.4 Cost summary

| Tier | Monthly | $/1000 queries effective |
|---|---|---|
| Low | ~$44 | $44 |
| Medium | ~$400 | $8.00 |
| High | ~$4,000 | $8.00 |

Economies of scale saturate around Medium: fixed costs (Qdrant cluster, Vercel Pro, monitoring) dominate Low, and per-query OpenAI cost dominates High. The plateau at ~$8 per 1000 queries is the design point.

---

## 5. Scaling Bottlenecks by Tier

### 5.1 Embedder

| Tier | Bottleneck? | Mitigation |
|---|---|---|
| Low | No (BGE CPU handles tens of queries/min easily) | None |
| Medium | Marginal at peak QPS 7; one backend instance can embed ~30 qps on c6i.xlarge | Two+ replicas share load |
| High | Yes at peak QPS 70 | Dedicated embed service with batched requests; or GPU embed node |

Embedding latency on CPU is ~30 ms per query. On an Apple Silicon M2 MPS, it is ~10 ms. Inside Docker (no MPS), we are CPU-bound; this is called out in `CLAUDE.md` as a dev-environment issue but affects prod throughput at scale.

### 5.2 Qdrant

| Tier | Bottleneck? | Mitigation |
|---|---|---|
| Low | No — single-node handles thousands of qps on 400 vectors | None |
| Medium | No — 2 GB cluster with HA is over-provisioned for 400 chunks | None |
| High | No for vector count, Yes for connection concurrency at 70 qps | Tune `max_segment_size` and HNSW `ef`; use Qdrant's async client |

At 1M chunks (v1.3 roadmap), HNSW construction and memory will be the primary constraints; this requires sharding across multiple collections or a Qdrant Cluster upgrade.

### 5.3 OpenAI rate limits

| Tier | OpenAI tier needed | Rate limit (RPM) | Headroom |
|---|---|---|---|
| Low | Tier 1 | 500 | 25x |
| Medium | Tier 2 | 3,500 | 8x |
| High | Tier 4 | 10,000 | 2.4x — tight |

Tier 4 requires $1,000+ in cumulative OpenAI spend and 30 days of account age. For a Day-1 Enterprise customer without OpenAI spend history, Tier 2 ceiling of 3,500 RPM corresponds to 58 RPS, which is below the Enterprise 70 RPS peak. Mitigations: request limit increase from OpenAI with Enterprise contract, or enable the vLLM adapter (v1.2).

### 5.4 Reranker

Cross-encoder MiniLM on CPU rejerks ~120 doc-pairs/sec per core. At 10 docs/query and Medium peak of 7 qps, we need 70 doc-pairs/sec — fits comfortably on one core. At High peak of 70 qps, we need 700 doc-pairs/sec — CPU-only requires 8+ cores for rerank alone.

For High tier we recommend a shared GPU node (g5.xlarge with A10G) that pushes rerank latency under 20 ms; it costs ~$370/month and serves the full fleet.

### 5.5 Postgres

Chat history is append-only with low contention. Neon autoscale handles write concurrency linearly with CU. At High tier, 70 qps of inserts is trivial relative to Postgres capability.

The one care area is read amplification: a session with 1000 messages read on every page load will burn compute. The backend should paginate (`sessions.py` endpoint) and apply index on `messages(session_id, created_at DESC)`.

---

## 6. Cost Optimization Levers

Ranked by ROI.

| Lever | Savings | Effort | Notes |
|---|---|---|---|
| Prompt caching on system prompt | −30 to −50% on input tokens | Low (one API flag) | Enable for all tiers |
| Reduce `top_k_final` from 5 to 3 | −22% on input tokens | Low (config) | Trade-off: marginal quality hit |
| Batched embedding at ingest | −20% ingest compute | Low | Already done for ingest |
| Switch reranker to `ms-marco-TinyBERT-L-2` | −50% rerank compute | Medium | Needs quality re-evaluation |
| Self-hosted LLM (vLLM + Llama 3 8B) | −100% OpenAI cost, +GPU cost | High | Break-even at ~5M queries/month |
| Move BM25 to Elasticsearch | Flatter scaling, lower pickle cost | Very high | Only justified at 10K+ docs |
| Qdrant scalar quantization | −75% Qdrant RAM, small recall hit | Low at scale | Valuable at 1M+ chunks |

### 6.1 Break-even analysis for self-hosted LLM

A g5.2xlarge (1 A10G, $1.21/hr on-demand, ~$870/month reserved) running vLLM + Llama 3 8B can serve ~5–10 queries/second sustained. OpenAI-equivalent volume at break-even: $870 / $0.000405 ≈ 2.1M queries/month. This is larger than the High tier, so for v1.0 OpenAI is the right call. Break-even shifts favorably if (a) the customer has security constraints that forbid OpenAI, or (b) volume exceeds ~2M queries/month.

---

## 7. Capacity Plan — Monitoring Thresholds

Each row below is a scaling trigger. When the metric crosses the threshold, the corresponding action executes (manually or via autoscaling policy).

| Metric | Threshold | Action | Cadence |
|---|---|---|---|
| `technova_query_total` rate | > 40 qps sustained 15 min | Scale backend replicas +1 | On demand |
| `technova_query_total` rate | > 60 qps sustained 15 min | Page on-call; check OpenAI tier headroom | On demand |
| Backend CPU util | > 70% sustained 10 min | Scale backend replicas +1 | On demand |
| Qdrant RAM usage | > 70% | Upgrade cluster size | Weekly review |
| OpenAI RPM consumption | > 70% of current tier | File request to OpenAI to raise tier | Weekly review |
| Neon CU consumption | > 80% of provisioned | Increase autoscale ceiling | Weekly review |
| Vercel bandwidth | > 80% of plan | Upgrade plan | Monthly review |
| Chunks in corpus | > 10,000 | Plan BM25 → Elasticsearch migration | Quarterly review |
| Chunks in corpus | > 100,000 | Plan Qdrant sharding | Quarterly review |

### 7.1 Scale-up latency

Backend replicas cold-start in ~30s (model loading). This is the floor on "scale-up latency" and must be considered for traffic spikes. Pre-warm pools are a v1.1 option for Enterprise.

---

## 8. Assumptions and Sensitivities

| Assumption | Value | If doubled | If halved |
|---|---|---|---|
| Average context size | 1500 tokens input | OpenAI input cost ×2 | OpenAI input cost ÷2 |
| Average output size | 300 tokens | OpenAI output cost ×2 | OpenAI output cost ÷2 |
| Chunks in corpus | 400 | Negligible effect on query cost | Negligible |
| Peak QPS burst factor | 3x average | Backend replicas needed ×2 | Backend replicas ÷2 |
| Reranker on CPU | baseline | Latency halves on GPU, $370/month added | n/a |
| OpenAI list price | current | Cost ×2 → self-host break-even moves to 1M queries/month | Cost ÷2 → self-host never breaks even |

### 8.1 What changes the model most

1. **OpenAI price movements** — the dominant line above Medium tier.
2. **Average context growth** — if product adds citations or longer chunks, input tokens grow linearly.
3. **QPS burst factor** — sizing replicas is driven by peak, not average.
4. **Corpus size at v1.3** — the 1M-chunk scenario is a different architecture, not a different cost within this model.

### 8.2 What does not matter

- Qdrant storage cost: vectors are tiny (~1.2 KB each × 400 = 500 KB for the corpus; even 1M chunks is 1.2 GB).
- Neon storage cost at Low/Medium: chat history grows slowly.
- Model pull cost from Hugging Face: zero — models are cached after first pull.

---

## 9. Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Platform Engineering | Initial release |
