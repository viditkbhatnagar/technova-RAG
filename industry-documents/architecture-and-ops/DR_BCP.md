# TechNova RAG — Disaster Recovery and Business Continuity Plan

**Owner:** TechNova Platform Engineering / SRE
**Classification:** INTERNAL
**Last Reviewed:** 2026-04-16
**Next Review:** 2026-10-16
**Version:** 1.0

---

## 1. Scope and Intent

This document defines how the TechNova RAG platform recovers from disasters ranging from a single component failure to a full regional cloud outage, and how operations continue under adverse workforce conditions. It applies to the FastAPI backend, Qdrant vector store, Neon Postgres, local derived artifacts (`backend/bm25_index.pkl`, `backend/graph_data.json`), the corpus PDFs in `docs/`, and the Next.js frontend hosted on Vercel.

Recovery targets are stratified by data class because the cost of protecting each is very different: the corpus PDFs are the only truly irreplaceable artifacts; everything else is derivable given the corpus and configuration.

---

## 2. Data Classification and RPO / RTO Targets

| Data class | Examples | Criticality | RPO | RTO | Rationale |
|---|---|---|---|---|---|
| Source corpus | `docs/*.pdf`, `backend/config.py::DOCUMENT_METADATA` | Tier 1 (irreplaceable) | 0 | 30 min | Source of truth; everything else is rebuildable from this. |
| Chat history | Neon Postgres `sessions`, `messages`, `documents`, `chunks` | Tier 2 (business record) | 15 min | 1 h | Conversation audit trail; Neon PITR supports 15-min granularity. |
| Vector index | Qdrant collection `technova_docs` | Tier 3 (rebuildable) | 24 h | 2 h | Daily snapshot; full rebuild from corpus takes ~60 min. |
| Derived artifacts | `backend/bm25_index.pkl`, `backend/graph_data.json` | Tier 4 (fully derivable) | n/a | ~1 h (re-ingest time) | Rebuild is deterministic from corpus; no backup required. |
| Configuration | `backend/config.py`, `.env`, `docker-compose.yml` | Tier 2 | 0 | 15 min | Versioned in git; secrets in Vault / Doppler with audit trail. |
| Model binaries | BGE, MiniLM reranker, spaCy | Tier 4 | n/a | ~10 min | Pulled on demand from Hugging Face; cached locally. |

RPO = Recovery Point Objective (max acceptable data loss). RTO = Recovery Time Objective (max acceptable downtime).

---

## 3. Backup Strategy

### 3.1 Corpus (Tier 1)

- Corpus PDFs live in `docs/` in git and are mirrored to an S3 bucket `technova-corpus-prod` with versioning enabled and cross-region replication (`us-east-2` primary, `eu-central-1` secondary).
- Every corpus change is a pull request that updates `DOCUMENT_METADATA` in `backend/config.py` — unmapped PDFs are silently skipped by the loader, so the PR is the control point.
- S3 Object Lock in compliance mode is applied for 7 years on the primary bucket (regulatory retention).

### 3.2 Postgres (Tier 2)

- Neon Postgres continuous WAL replication provides point-in-time recovery (PITR) to any moment within the retention window (30 days on Business, 90 days on Enterprise).
- Daily logical `pg_dump` exported to `technova-backups-prod/postgres/YYYY-MM-DD.sql.gz` at 03:00 UTC.
- Weekly restore test: a nightly job provisions a scratch Neon branch from the previous day's dump and runs a schema-validation suite. Failures page on-call.

### 3.3 Qdrant (Tier 3)

- Daily snapshot of the `technova_docs` collection via `POST /collections/technova_docs/snapshots`, uploaded to `technova-backups-prod/qdrant/YYYY-MM-DD.snapshot`.
- 30-day retention on primary region; 90-day retention cross-region.
- Snapshot integrity verified weekly by a restore-and-compare job that runs the ten canary queries against the restored collection and asserts result equivalence.

### 3.4 Derived artifacts (Tier 4)

No backup. `/api/ingest` with `force_reingest=true` deterministically rebuilds `backend/bm25_index.pkl` and `backend/graph_data.json` from the corpus. Ingest time is ~42s for the current 400-chunk corpus.

### 3.5 Configuration and secrets

- Non-secret config is versioned in git.
- Secrets (`OPENAI_API_KEY`, `DATABASE_URL`, Qdrant API key) are stored in Doppler with full audit log and version pinning. Secret rotation is documented in `RUNBOOKS.md` R-06.

---

## 4. Recovery Procedures by Scenario

### 4.1 Scenario matrix

| Scenario | Trigger | Primary recovery | RPO / RTO |
|---|---|---|---|
| Single backend replica crash | Liveness fails | Auto-restart via orchestrator | RPO 0 / RTO 2 min |
| All backend replicas down | ALB health all red | Scale out; roll back last deploy | RPO 0 / RTO 15 min |
| Qdrant total loss | Collection not found, repeated 5xx | Restore from daily snapshot (section 5) | RPO 24h / RTO 2h |
| Neon Postgres data corruption | Integrity check fails | PITR restore to last known-good timestamp | RPO 15 min / RTO 1h |
| Accidental corpus deletion | `/api/status` shows 0 documents | S3 version restore + force_reingest | RPO 0 / RTO 30 min |
| OpenAI outage | Generator errors sustained | Graceful degradation (prompt + sources returned); banner on frontend | RPO 0 / no downtime |
| Region failure | Cloud provider status red | Failover to secondary region | RPO 15 min / RTO 4h |
| BM25 pickle corruption | `_load_bm25` raises on startup | Force re-ingest (R-07) | RPO 0 / RTO 1h |

### 4.2 Region failure (full failover)

Secondary region is cold-standby for Business tier, warm-standby for Enterprise.

1. SRE declares regional failover via incident channel.
2. DNS CNAME flipped from `api.technova.example` to the secondary region ALB (TTL pre-lowered to 60 s during standard maintenance).
3. Secondary-region Neon branch promoted to primary (Neon console or API).
4. Secondary-region Qdrant cluster already holds replicated snapshots; verify latest snapshot restored and collection present.
5. Backend replicas in secondary region scaled from 1 to N.
6. Synthetic probes re-pointed; if green for 10 consecutive runs, declare recovery.
7. Customer communication sent via StatusPage.

Dry-run target: < 4h end-to-end; measured annually at the DR drill (section 6).

### 4.3 Data corruption — Postgres PITR

Triggered by a failed integrity check or an accidental DELETE detected by audit log.

1. Identify corruption timestamp `T_bad` from audit log or user report.
2. In Neon console, select the target branch and restore to `T_bad - 1 minute`.
3. Restoration creates a new branch; promote it to primary after schema validation.
4. Update `DATABASE_URL` secret in Doppler; deploy propagates to backend replicas via rolling restart.
5. Verify via `curl http://localhost:8000/api/status` that the backend reports chat-history availability.

### 4.4 OpenAI outage — graceful degradation

OpenAI outages are treated as a pre-existing contract, not a disaster. The generator in `backend/services/generator.py` returns `None` when the API is unreachable or the key is unset; `/api/query` then returns the assembled prompt and retrieved sources. The frontend renders these and displays a banner.

Operational checklist during sustained outage:

1. Pin a banner in the in-app notification area ("LLM generation temporarily disabled").
2. Disable `answer` display on the frontend via the feature flag `NEXT_PUBLIC_DISABLE_ANSWER`.
3. Increase retrieval `top_k_final` from 5 to 8 so users can self-synthesize.
4. Track duration in incident channel; post hourly updates to StatusPage.

---

## 5. Qdrant Total-Loss Restore Runbook

Step-by-step procedure for restoring the `technova_docs` collection from the most recent daily snapshot. This is the canonical reference for R-05 in `RUNBOOKS.md`.

**Preconditions:**
- S3 read access to `technova-backups-prod/qdrant/`
- Qdrant cluster URL and API key in Doppler
- At least one healthy backend replica to issue `/api/status` against

**Steps:**

1. Declare incident, open incident channel, notify stakeholders.
2. Confirm the failure: `curl -sS ${QDRANT_URL}/collections | jq '.result.collections'` should list `technova_docs`; if absent, proceed.
3. Identify the most recent good snapshot:
   `aws s3 ls s3://technova-backups-prod/qdrant/ | sort | tail -5`
4. If running Qdrant Cloud: use the Cloud console restore workflow, selecting the snapshot from step 3.
   If self-hosted: copy snapshot to the Qdrant node at `/qdrant/snapshots/technova_docs/`, then:
   `curl -X PUT "${QDRANT_URL}/collections/technova_docs/snapshots/recover" -H "api-key: ${QDRANT_KEY}" -d '{"location": "file:///qdrant/snapshots/technova_docs/<file>.snapshot"}'`
5. Wait for the collection status to be `green`.
6. Verify payload indexes are in place — the snapshot preserves them, but re-creation is idempotent:
   `curl -X PUT "${QDRANT_URL}/collections/technova_docs/index" -H "api-key: ${QDRANT_KEY}" -d '{"field_name": "security_level", "field_schema": "keyword"}'`
   Repeat for `doc_slug`.
7. Restart backend replicas to force `app.state` singletons to reconnect.
8. Verify ingest state:
   `curl http://api.technova.example/api/status | jq '.chunks_indexed'`
   This should match the baseline (~400 for current corpus).
9. Run the ten canary queries from the acceptance test pack (`scripts/canary_queries.sh`). All must return non-empty `sources`.
10. If any canary fails, decide between rolling back to an older snapshot or triggering `force_reingest`:
    `curl -X POST http://api.technova.example/api/ingest -H 'content-type: application/json' -d '{"force_reingest": true}'`
11. Close incident once probes are green for 30 minutes.

**Acceptance criteria:**
- `chunks_indexed` matches baseline
- All 10 canary queries return non-empty `sources`
- Access-denied probes return correctly for Project B roles

---

## 6. DR Drill

### 6.1 Annual full-stack drill

Conducted once per calendar year, typically in Q3. The drill simulates a total primary-region outage and exercises the full failover procedure in a production-parity environment.

| Phase | Duration | Activity |
|---|---|---|
| Preparation | T-2 weeks | Announce, freeze non-essential deploys, brief on-call |
| Execution | T+0 to T+4h | Simulate primary region failure; execute section 4.2 failover |
| Validation | T+4h to T+6h | Run full synthetic probe suite; manual validation by QA |
| Recovery | T+6h to T+8h | Fail back to primary region |
| Post-mortem | Within 5 business days | Document gaps, update runbooks |

### 6.2 Success criteria

- RTO met: failover completes within 4 hours
- RPO met: no data loss beyond 15-minute Postgres window, no corpus loss, no vector loss beyond 24-hour window
- All canary queries pass in the secondary region
- Customer-visible downtime < 30 minutes (via DNS flip, not full outage)

### 6.3 Quarterly component drills

Lighter exercises run every quarter on a single component:

- Q1: Qdrant snapshot restore (dev environment)
- Q2: Postgres PITR (staging)
- Q3: Full regional failover (production dry-run)
- Q4: Secret rotation under load (production, see R-06)

---

## 7. Communication Plan

### 7.1 Customer-facing channels

| Channel | Owner | When |
|---|---|---|
| StatusPage (status.technova.example) | SRE | All Sev 1 and Sev 2 events |
| Email via StatusPage subscribers | SRE | Sev 1, or Sev 2 > 30 min |
| Direct Slack to Enterprise customer | Customer Success | Sev 1 with Enterprise customer impact |
| Post-mortem PDF | SRE + Engineering Lead | Within 5 business days of Sev 1 |

### 7.2 Internal channels

| Channel | Purpose |
|---|---|
| `#incident-tr` Slack channel | Real-time coordination; one channel per incident |
| PagerDuty | On-call paging; Sev 1 pages primary + secondary immediately |
| Confluence incident page | Running log, becomes post-mortem skeleton |

### 7.3 Communication templates

- **Initial acknowledgement** (< 10 min from detection): "We are aware of an issue affecting TechNova RAG query latency. Engineering is investigating. Next update in 30 minutes."
- **Mitigation update**: "We have applied mitigation X. Metrics are recovering. Next update in 30 minutes."
- **Resolution**: "The issue has been resolved as of HH:MM UTC. A full post-mortem will be published within 5 business days."

---

## 8. Business Continuity — Workforce

### 8.1 Remote-first operations

The TechNova Platform Engineering team is remote-first across three regions (US East, Europe Central, India). All operational systems are accessible over VPN from any region; no on-site presence is required to operate the platform.

### 8.2 On-call coverage

| Role | Primary | Secondary | Handoff |
|---|---|---|---|
| SRE on-call | Rotating weekly | Rotating weekly | Monday 10:00 local, 24h overlap |
| Engineering manager on-call | Rotating monthly | Same | First of month |
| Executive sponsor | Static (VP Engineering) | n/a | n/a |

Coverage is distributed across three time zones to avoid waking anyone in the middle of the night. A primary in each region means any Sev 1 reaches a human within 15 minutes.

### 8.3 Pandemic and force majeure

- All operational processes are executable from a laptop with internet access; no physical dependency.
- Secrets and production access are gated by hardware security keys (Yubikey); each operator maintains two.
- Payroll and expense systems are independent of engineering infrastructure; engineer well-being is not coupled to incident response.

### 8.4 Succession and bus-factor mitigation

Each runbook in `RUNBOOKS.md` names at least two engineers who can execute it. The on-call rotation explicitly spans both roles to keep knowledge distributed. New hires must shadow two incidents before being added to the primary rotation.

---

## 9. Vendor Concentration Risk

### 9.1 Current dependencies

| Vendor | Service | Substitutability | Impact of loss |
|---|---|---|---|
| OpenAI | gpt-4o-mini | Medium (adapter layer exists; swap to vLLM + Llama 3 in 1-2 weeks) | Degraded — retrieval-only mode sustains service |
| Neon | Postgres | High (standard Postgres; migrate to any managed Postgres in days) | Chat history degraded |
| Qdrant (Cloud) | Vector store | Medium (self-host path exists; schema is stable) | Core outage — retrieval blocked |
| Vercel | Frontend hosting | High (static Next.js; redeploy elsewhere in hours) | Frontend outage, API direct still works |
| Hugging Face | Model hub | High (models are cached locally and pinned) | Startup impact only |
| AWS S3 | Object store | High | Low (replaceable) |

### 9.2 Mitigations

- **LLM**: Roadmap v1.2 — fully implement `generator.py` adapter protocol so that swapping from OpenAI to a self-hosted vLLM + Llama 3 is a configuration change (`LLM_PROVIDER=vllm` in env).
- **Vector store**: Qdrant schema is intentionally simple (cosine, 768-dim, payload filters) so that migration to Weaviate or pgvector is a one-time reindex rather than a re-architecture.
- **Model hub**: All models are pinned by revision in `backend/services/embedder.py` and `backend/services/retriever.py`; the model cache volume persists across deploys. A Hugging Face outage does not affect steady-state operation.

### 9.3 Concentration ceiling

No single vendor may represent more than 60% of compute spend; OpenAI is currently the largest share at ~55% for Medium-tier workloads and is the primary target for diversification in v1.2.

---

## 10. Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Platform Engineering | Initial release |
