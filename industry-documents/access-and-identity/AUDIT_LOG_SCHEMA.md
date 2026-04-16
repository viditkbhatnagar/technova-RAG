# Audit Log Schema

| Field | Value |
|---|---|
| Owner | TechNova Identity and Access |
| Classification | INTERNAL |
| Last Reviewed | 2026-04-16 |
| Next Review | 2026-10-16 |
| Version | 1.0 |

---

## 1. Purpose

The audit log is the ground-truth record of every security-relevant action in TechNova RAG. It exists to:

- Support SOC 2 CC7 (system monitoring) and CC6 (logical access) controls with auditable evidence.
- Enable detection of role-boundary violations and anomalous access patterns.
- Provide forensic reconstruction in the event of a security incident, including the exact chunks retrieved for a given query, the rerank scores, and whether an access-denied path was taken.
- Underpin the break-glass procedure (see `BREAK_GLASS_PROCEDURE.md`) with a tamper-resistant trail.

The audit log is separate from application logging (structured logs via `logging` in Python). Application logs are a debugging surface; audit logs are a legal and compliance surface with retention, integrity, and access guarantees that application logs do not make.

---

## 2. Event Taxonomy

The event taxonomy is deliberately small and stable. New event types are added through a governed schema change, not ad-hoc.

| Event type | Trigger | Category |
|---|---|---|
| `AUTH_LOGIN` | Successful SSO authentication; session JWT minted. | Authentication |
| `AUTH_LOGOUT` | Explicit logout; SLO initiation. | Authentication |
| `AUTH_FAIL` | Any auth failure (bad signature, expired token, unknown role, refresh reuse). | Authentication |
| `QUERY_SUBMIT` | Request received on `/api/query` (Project A or B). | Access |
| `QUERY_RESPONSE` | Response returned for `/api/query`. | Access |
| `ACCESS_DENIED` | Restricted-space probe triggered denial; `access_denied=true`. | Access |
| `INGEST_START` | `/api/ingest` received; corpus ingestion beginning. | Operations |
| `INGEST_COMPLETE` | Ingestion finished (success or failure). | Operations |
| `CONFIG_CHANGE` | Git commit to `backend/config.py` deployed; detected via CI hook. | Change management |
| `ROLE_GRANT` | Role assigned to a user via admin API (v1.1). | Change management |
| `ROLE_REVOKE` | Role removed via admin API or SCIM deactivation. | Change management |
| `SESSION_DELETE` | User deleted via SCIM DELETE; all active sessions revoked. | Authentication |
| `ADMIN_OP` | Any admin API call that mutates state and does not have its own event type. | Operations |

Any security-relevant action that does not fit one of the types above is not loggable - it must be refactored to fit, or a new event type must be added through the schema change process in section 11.

---

## 3. Common Envelope

Every event carries the same envelope. The envelope is immutable; payloads differ by event type.

```json
{
  "event_id":   "UUIDv7 - monotonic, sortable",
  "event_type": "QUERY_RESPONSE",
  "occurred_at": "2026-04-16T14:03:22.118Z",
  "actor_sub":  "auth0|65e9...  (IdP subject identifier)",
  "actor_role": "manager",
  "source_ip":  "10.42.18.204",
  "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) ...",
  "tenant_id":  "acme",
  "request_id": "01HXYZ...  (propagated from X-Request-ID)",
  "session_id": "sess_01HXYZ...  (nullable for pre-auth events)",
  "payload":    { /* event-specific */ }
}
```

Field notes:

- `event_id` uses UUIDv7 (time-ordered) so that events sort naturally without a separate index on `occurred_at`.
- `actor_sub` is the IdP `sub` claim in v1.1. In v1.0 it is the literal string `"legacy-unauthenticated"` plus the body-supplied role, since no identity exists.
- `actor_role` captures the role at the moment the event occurred. A subsequent role change does not rewrite history.
- `request_id` is the X-Request-ID header, propagated from the frontend or injected by the backend. Cross-references application logs.
- `tenant_id` is always populated in v1.1; in v1.0 it is the deployment id.

---

## 4. Payload Schemas

The high-value event type is `QUERY_RESPONSE`. Its schema is provided in full; other payloads are summarised.

### 4.1 QUERY_RESPONSE

```json
{
  "query_hash": "sha256 of the normalised query string",
  "query_length_chars": 134,
  "retrieval": {
    "top_k_retrieval": 20,
    "top_k_rerank": 5,
    "rrf_k": 60,
    "retrieved_chunk_ids_hashed": [
      "sha256:3f1a...",
      "sha256:c804..."
    ],
    "methods": ["hybrid", "hybrid", "dense", "hybrid", "bm25"],
    "rerank_top1_score": 0.84,
    "rerank_scores": [0.84, 0.72, 0.61, 0.55, 0.49],
    "security_filter_applied": { "role": "manager", "clearance_lte": 2 },
    "bm25_allowed_set_size": 842,
    "self_correcting_invoked": false,
    "synonyms_applied": []
  },
  "access_denied": false,
  "access_denied_reason": null,
  "restricted_probe": {
    "ran": false,
    "top_cosine": null
  },
  "generation": {
    "model": "gpt-4o-mini",
    "prompt_tokens": 1482,
    "completion_tokens": 287,
    "total_tokens": 1769,
    "cost_usd_estimate": 0.000438
  },
  "latency_ms": {
    "dense": 42,
    "bm25": 18,
    "rerank": 71,
    "generation": 814,
    "total": 961
  }
}
```

Design notes:

- Chunk IDs are SHA-256 hashed before logging. The ingest pipeline maintains a separate `chunk_id -> hash` mapping in Postgres so forensic investigators can resolve hashes to content with appropriate authorization. This separation prevents the audit log itself from becoming a second source of restricted content.
- The raw query string is not logged by default. Its hash and length are retained indefinitely; the raw body is stored for ninety days in a separate privacy-scoped table (section 7) to support incident investigation and then purged.
- `restricted_probe.top_cosine` is numeric even when the probe triggers a denial; this is the only numeric signal about the restricted space, and it does not by itself identify a document.

### 4.2 ACCESS_DENIED

```json
{
  "reason": "restricted_probe_strong_match",
  "accessible_top1_rerank": -0.08,
  "restricted_top_cosine": 0.71,
  "restricted_probe_doc_domain": "finance",
  "message_shown": "A higher clearance is required to answer this question."
}
```

`restricted_probe_doc_domain` is the domain of the best restricted match (for example `finance`, `hr`, `governance`), not the document slug. Domain is safe to log because it is a coarse taxonomy present across multiple documents; the slug would narrow the leak.

### 4.3 AUTH_LOGIN / AUTH_LOGOUT / AUTH_FAIL

```json
{
  "protocol": "oidc",
  "idp": "okta",
  "outcome": "success",
  "resolved_role": "employee",
  "role_source": "claim:technova_role",
  "failure_reason": null
}
```

`failure_reason` is one of a closed set: `signature_invalid`, `expired`, `no_role_resolvable`, `refresh_reuse_detected`, `audience_mismatch`, `issuer_unknown`, `replay_detected`.

### 4.4 INGEST_START / INGEST_COMPLETE

```json
{
  "force_reingest": true,
  "docs_total": 11,
  "docs_ingested": 11,
  "chunks_total": 1204,
  "duration_s": 142.3,
  "bm25_rebuilt": true,
  "graph_rebuilt": true,
  "qdrant_collection_dropped": true,
  "outcome": "success",
  "git_sha": "045f97e"
}
```

### 4.5 CONFIG_CHANGE

```json
{
  "git_sha": "abc1234",
  "pr_url": "https://github.com/technova/rag/pull/142",
  "files_changed": ["backend/config.py"],
  "classification_deltas": [
    { "doc": "Vendor_Contracts.pdf", "old": "INTERNAL", "new": "CONFIDENTIAL" }
  ],
  "approver_sub": "auth0|..."
}
```

### 4.6 ROLE_GRANT / ROLE_REVOKE

```json
{
  "target_sub": "auth0|...",
  "target_email_hash": "sha256:...",
  "role": "manager",
  "prior_role": "employee",
  "ticket_ref": "ACC-4812",
  "justification_hash": "sha256:...",
  "approver_sub": "auth0|..."
}
```

---

## 5. Current Storage - Version 1.0

In v1.0 the audit surface is the Postgres `messages` table introduced for chat history. The relevant columns are:

| Column | Type | Notes |
|---|---|---|
| `session_id` | uuid | FK to `sessions`. |
| `role` | text | `user` or `assistant`. |
| `content` | text | The chat content. Raw text, no hash. |
| `sources` | jsonb | Array of chunk-source objects including doc slug, chunk_id, retrieval_method, score. |
| `retrieval_stats` | jsonb | Retrieval pipeline stats (dense top-k, BM25 top-k, rerank scores). |
| `access_denied` | boolean | True when the restricted-space probe triggered a denial. |
| `access_denied_message` | text | The human-readable denial message shown to the user. |
| `created_at` | timestamptz | Row creation time. |

This coverage is sufficient for product analytics and some forensic reconstruction, but has three material gaps for audit purposes:

1. **Mutability**. The `messages` table is a normal relational table. A future migration, an inadvertent UPDATE, or a malicious insider with Postgres access can rewrite history. An audit log must be append-only at the storage layer.
2. **No dedicated schema**. `messages` mixes product data (chat UX) with control data (access decisions). SOC 2 evidence gathering is awkward.
3. **Raw content retention**. `content` includes the raw user query indefinitely, creating a privacy surface that should be time-boxed.

These gaps are acknowledged and tracked. v1.0 compensates by operating in a demonstration environment with no regulated data.

---

## 6. Target Storage - Version 1.1

v1.1 introduces a dedicated append-only audit table and a weekly immutable export.

### 6.1 `audit_events` table

```sql
CREATE TABLE audit_events (
    event_id        uuid PRIMARY KEY,
    event_type      text NOT NULL,
    occurred_at     timestamptz NOT NULL,
    actor_sub       text,
    actor_role      text,
    source_ip       inet,
    user_agent      text,
    tenant_id       text NOT NULL,
    request_id      text,
    session_id      uuid,
    payload         jsonb NOT NULL,
    hash_self       bytea NOT NULL,        -- HMAC-SHA256 of row
    hash_prev       bytea NOT NULL,        -- hash_self of the previous row
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX audit_events_occurred_at ON audit_events (occurred_at);
CREATE INDEX audit_events_actor_sub   ON audit_events (actor_sub);
CREATE INDEX audit_events_event_type  ON audit_events (event_type);

-- Row-level security: only Security and Compliance roles may SELECT.
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_read ON audit_events FOR SELECT
    USING (current_setting('technova.role', true) IN ('security', 'compliance'));

-- Block UPDATE and DELETE at the table level.
CREATE RULE audit_events_no_update AS ON UPDATE TO audit_events DO INSTEAD NOTHING;
CREATE RULE audit_events_no_delete AS ON DELETE TO audit_events DO INSTEAD NOTHING;
```

INSERT is the only permitted mutation. UPDATE and DELETE are blocked by DO INSTEAD NOTHING rules; even a superuser accidentally issuing UPDATE is a no-op. Postgres role `audit_writer` has INSERT only; no role has UPDATE or DELETE.

### 6.2 S3 export

A nightly job streams the prior day's events to an S3 bucket with Object Lock in Governance mode, retention seven years. Each file is signed with the exported hash-chain anchor. S3 Object Lock is the immutability backstop: even if Postgres is compromised, the S3 copy is retrievable and verifiable.

---

## 7. Retention

| Data | Retention | Rationale |
|---|---|---|
| Audit events (full envelope + payload with hashes only) | 7 years | SOC 2, ISO 27001 typical; aligned with GDPR recital allowances for security logs. |
| Raw query body (separate `query_bodies` table, keyed by `event_id`) | 90 days | Privacy: queries may contain PII; short retention minimises exposure. |
| Raw chat content (`messages.content`) | 90 days in v1.1 | Aligned with raw query retention. |
| SAML and OIDC tokens | Not stored | Tokens are verified and discarded. Only claim extracts are logged. |
| Break-glass session transcripts | 7 years | Higher sensitivity; matches audit retention. |

Purge jobs run daily and write their own `ADMIN_OP` audit events with `purged_rows` counts.

---

## 8. Integrity

Integrity of the audit chain is protected by a hash chain plus an external anchor.

### 8.1 Per-row HMAC

For each row, `hash_self = HMAC-SHA256(key, canonical_json(row_without_hash_fields) || hash_prev)`. The key is stored in AWS KMS and rotated annually; prior keys are retained for verification of historical rows.

Verification: a compliance auditor can replay the chain from any anchor forward. A single tampered row invalidates every row after it. The chain makes targeted edits detectable without requiring full replay.

### 8.2 Weekly transparency anchor

Every Monday at 00:00 UTC, the latest `hash_self` is posted to an append-only internal transparency log (Postgres table + S3 mirror) and optionally to a public Git repository for external witness. An attacker who tampers with historical events must also rewrite every weekly anchor, which is publicly visible.

### 8.3 Backfill prevention

The `occurred_at` column is indexed, but an INSERT with a past timestamp still hashes into the chain at its INSERT position. A backfilled event therefore appears out of order in the chain and is detectable by comparing `occurred_at` ordering with `event_id` (UUIDv7) ordering.

---

## 9. Access and Egress

Read access to `audit_events` is restricted to users in the Security and Compliance groups. The row-level security policy enforces this at the database layer.

Egress paths:

- **Athena** - audit events exported to S3 in Parquet format are queryable via AWS Athena; IAM policy restricts the workgroup to Security and Compliance principals.
- **Splunk HEC** - optional live forwarding via HTTP Event Collector for SIEM ingestion.
- **Ad-hoc CSV export** - requires ticket approval; the export itself is an `ADMIN_OP` audit event with the ticket reference and the row count.

Developers do not have access to `audit_events`. Application logging (`logging` to stdout, shipped to CloudWatch) is sufficient for debugging; audit events are a compliance surface, not a debugging surface.

---

## 10. Privacy

The audit log is designed to be disclosable to auditors without disclosing user content.

- Common envelope fields are either identifiers (`actor_sub`, `session_id`) or metadata (`source_ip`, `user_agent`). No payload is stored in the common envelope.
- Chunk references are hashes. Content resolution requires a separate authorized path.
- Query bodies are stored for 90 days only, in a separate table, with stricter access controls than the envelope.
- Email addresses are never stored directly; `target_email_hash` (SHA-256) is used for cross-referencing without allowing bulk harvesting.
- GDPR Article 17 (right to erasure) interacts awkwardly with 7-year audit retention; the TechNova position is that audit events qualify for the legitimate-interests exception for security logs. Legal counsel review is on file.

---

## 11. Monitoring and SIEM Rules

The following SIEM rules run daily against audit events and fire alerts into the Security team's channel.

| Rule | Trigger | Severity |
|---|---|---|
| High `ACCESS_DENIED` rate per user | > 10 denials per user per hour | Medium |
| Repeated `AUTH_FAIL` with `refresh_reuse_detected` | Any occurrence | High |
| `ROLE_GRANT` without `ticket_ref` | Any occurrence | High |
| `CONFIG_CHANGE` affecting `DOCUMENT_METADATA` outside change window | Any | Medium |
| `INGEST_START` outside business hours without an active `INC-*` ticket | Any | Medium |
| `QUERY_RESPONSE` with rerank top-1 < -0.2 and accessible results returned | Investigation flag | Low |
| Break-glass `is_break_glass=true` session active more than 4 hours | Any | High |

Rules are version-controlled alongside the application. Tuning requires a PR and Security sign-off.

### 11.1 Schema change process

A new event type or a new required payload field follows this process:

1. PR to this document with the schema change.
2. Data Governance and Security approvals.
3. PR to the audit writer code, guarded by a feature flag.
4. Backfill strategy documented (usually "no backfill; new events only").
5. Production rollout with feature flag off for 24 hours, then on.
6. SIEM rule update if the new event affects monitoring.

---

## 12. Appendix - Sample Events

### 12.1 QUERY_RESPONSE

```json
{
  "event_id": "01HX8Z9Q2K5V3T4R7P1N8M6B2C",
  "event_type": "QUERY_RESPONSE",
  "occurred_at": "2026-04-16T14:03:22.118Z",
  "actor_sub": "auth0|65e9abcd",
  "actor_role": "manager",
  "source_ip": "10.42.18.204",
  "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3)",
  "tenant_id": "acme",
  "request_id": "01HX8Z9Q1J",
  "session_id": "f3a1...",
  "payload": {
    "query_hash": "sha256:9ac3...",
    "retrieval": {
      "rerank_top1_score": 0.84,
      "methods": ["hybrid","hybrid","dense","hybrid","bm25"],
      "security_filter_applied": {"role":"manager","clearance_lte":2}
    },
    "access_denied": false,
    "generation": {"model":"gpt-4o-mini","total_tokens":1769}
  }
}
```

### 12.2 ACCESS_DENIED

```json
{
  "event_id": "01HX8ZA3...",
  "event_type": "ACCESS_DENIED",
  "occurred_at": "2026-04-16T14:07:11.482Z",
  "actor_sub": "auth0|4412fe",
  "actor_role": "employee",
  "tenant_id": "acme",
  "payload": {
    "reason": "restricted_probe_strong_match",
    "accessible_top1_rerank": -0.08,
    "restricted_top_cosine": 0.71,
    "restricted_probe_doc_domain": "hr"
  }
}
```

### 12.3 CONFIG_CHANGE

```json
{
  "event_id": "01HX91...",
  "event_type": "CONFIG_CHANGE",
  "occurred_at": "2026-04-16T10:00:00.000Z",
  "actor_sub": "auth0|deploybot",
  "actor_role": "admin",
  "tenant_id": "acme",
  "payload": {
    "git_sha": "abc1234",
    "pr_url": "https://github.com/technova/rag/pull/142",
    "files_changed": ["backend/config.py"],
    "classification_deltas": [
      {"doc":"Vendor_Contracts.pdf","old":"INTERNAL","new":"CONFIDENTIAL"}
    ],
    "approver_sub": "auth0|dg-lead"
  }
}
```

---

## 13. Revision History

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Identity & Access | Initial release |
