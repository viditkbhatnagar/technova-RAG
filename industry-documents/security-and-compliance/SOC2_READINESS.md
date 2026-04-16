# TechNova RAG — SOC 2 Readiness Assessment

| Field | Value |
|---|---|
| Owner | TechNova Trust & Security |
| Classification | INTERNAL |
| Last Reviewed | 2026-04-16 |
| Next Review | 2026-10-16 |
| Version | 1.0 |

## 1. Scope

This assessment maps TechNova RAG v1.0 to the AICPA Trust Services Criteria (2017, revised 2022) for:

- **Security (Common Criteria CC1–CC9)** — applicable to all systems.
- **Availability (A1)** — applicable because the service is used by TechNova staff during business hours.
- **Confidentiality (C1)** — applicable because the system handles CONFIDENTIAL and RESTRICTED corpus content.

Processing Integrity (PI1) and Privacy (P1–P8) are not in scope for this pass. Privacy concerns are addressed separately in the `DPIA.md`.

Statuses used below: **Implemented**, **Partial**, **Roadmap**, **N/A**.

## 2. Control Mapping

### Common Criteria — CC1 Control Environment

| ID | Description | TechNova Implementation | Evidence / Artefact | Status |
|---|---|---|---|---|
| CC1.1 | Demonstrates commitment to integrity and ethical values. | Code of Conduct; Acceptable Use Policy referenced from compliance set. | `legal-and-commercial/ACCEPTABLE_USE.md` | Implemented |
| CC1.2 | Board oversight of internal control. | Board minutes include quarterly security review agenda item. | Board_Minutes_Q4 (RESTRICTED) | Partial — formalisation Roadmap v1.1 |
| CC1.3 | Management establishes structures, reporting lines, authorities. | Trust & Security team identified as control owner; CODEOWNERS on `backend/config.py` and `backend/services/security.py`. | `CODEOWNERS` | Implemented |
| CC1.4 | Commitment to attracting/developing competent personnel. | Training records in TechNova_Training_Compliance.pdf. | Training register | Implemented |
| CC1.5 | Holds individuals accountable. | PR-based change control; CODEOWNERS review on security-sensitive files. | Git history | Implemented |

### CC2 Communication and Information

| ID | Description | TechNova Implementation | Evidence | Status |
|---|---|---|---|---|
| CC2.1 | Relevant quality information obtained and used. | Logs emitted by uvicorn + structured app logs. | `uvicorn` stdout | Partial — centralisation Roadmap v1.1 |
| CC2.2 | Internally communicates information to support internal control. | Compliance corpus under `industry-documents/`; on-call runbook. | `TechNova_OnCall_Runbook.pdf` | Implemented |
| CC2.3 | Communicates with external parties. | Vulnerability disclosure policy. | `VULNERABILITY_DISCLOSURE_POLICY.md` | Implemented |

### CC3 Risk Assessment

| ID | Description | TechNova Implementation | Evidence | Status |
|---|---|---|---|---|
| CC3.1 | Specifies objectives with sufficient clarity to assess risk. | Security objectives and invariants stated. | `THREAT_MODEL.md` §6 | Implemented |
| CC3.2 | Identifies and analyses risk. | STRIDE per trust boundary + LLM Top 10. | `THREAT_MODEL.md` §4–5 | Implemented |
| CC3.3 | Considers potential for fraud. | Insider scenario (TA-5 metadata downgrade) covered. | `THREAT_MODEL.md` §3 | Partial — four-eyes enforcement Roadmap v1.1 |
| CC3.4 | Identifies and assesses changes that could impact control. | Re-classification procedure; re-ingest on change. | `DATA_CLASSIFICATION_MATRIX.md` §6 | Implemented |

### CC4 Monitoring Activities

| ID | Description | TechNova Implementation | Evidence | Status |
|---|---|---|---|---|
| CC4.1 | Ongoing and/or separate evaluations. | Bi-annual documentation review (Last Reviewed / Next Review headers). | This document + corpus | Implemented |
| CC4.2 | Evaluates and communicates deficiencies. | Risk register (Roadmap v1.1). | — | Partial |

### CC5 Control Activities

| ID | Description | TechNova Implementation | Evidence | Status |
|---|---|---|---|---|
| CC5.1 | Selects and develops control activities. | Security controls defined in `backend/services/security.py`. | Source file | Implemented |
| CC5.2 | Selects and develops general controls over technology. | Supply chain SBOM, dependency pinning. | `SBOM.md` | Implemented |
| CC5.3 | Deploys controls through policies and procedures. | This compliance corpus. | `industry-documents/` | Implemented |

### CC6 Logical and Physical Access Controls

| ID | Description | TechNova Implementation | Evidence | Status |
|---|---|---|---|---|
| CC6.1 | Logical access — identification and authentication. | No SSO in v1.0 — role passed in request body (demo-grade). | `backend/routers/query.py` | **Partial — SSO is Roadmap v1.1** |
| CC6.2 | Authorisation — least privilege enforced. | Dual pre-filter (`get_security_filter`, `get_allowed_chunk_ids`) on dense + lexical paths. | `backend/services/security.py` | Implemented |
| CC6.3 | User registration and deregistration. | Out-of-band (TechNova IdP). No SCIM integration. | — | Roadmap |
| CC6.4 | Physical access. | Cloud providers (Vercel, Neon, optionally Qdrant Cloud) responsible; underlying data centres SOC 2 attested. | Sub-processor reports | Implemented (via inheritance) |
| CC6.5 | Data at rest protected. | Neon encryption at rest; Qdrant disk encryption recommended; production OPENAI key and Postgres credentials in secret manager. | Config | Implemented |
| CC6.6 | Logical access over data transmission. | TLS for all external boundaries (TB-1, TB-4, TB-5). | See `DATA_FLOW_DIAGRAM.md` §8 | Implemented |
| CC6.7 | Access to system restricted to authorised personnel. | Repo access via GitHub; prod deploys via Vercel seats + Docker host access. | IdP audit | Partial — quarterly access review Roadmap v1.1 |
| CC6.8 | Prevents/detects unauthorised / malicious software. | Dependency pinning; `pip-audit`, `npm audit`; no arbitrary code execution in runtime. | `SBOM.md`, CI | Partial — SCA automation Roadmap v1.1 |

### CC7 System Operations

| ID | Description | TechNova Implementation | Evidence | Status |
|---|---|---|---|---|
| CC7.1 | Detection of system events. | uvicorn + app logs; Vercel request logs; Neon query logs. No SIEM aggregation. | Host logs | **Partial — SIEM / centralised logging is Roadmap v1.1** |
| CC7.2 | Monitors for anomalies and incidents. | Manual review; no UEBA in v1.0. | — | Roadmap |
| CC7.3 | Evaluates security events. | Incident classification per `VULNERABILITY_DISCLOSURE_POLICY.md` severity ladder. | `VULNERABILITY_DISCLOSURE_POLICY.md` | Implemented |
| CC7.4 | Responds to security incidents. | Incident response plan (Roadmap v1.1 for full runbook). On-call runbook covers operational incidents. | `TechNova_OnCall_Runbook.pdf` | Partial |
| CC7.5 | Recovers from incidents / continuity. | Re-ingest restores corpus; managed services restore their own tier. | `DATA_FLOW_DIAGRAM.md` §10 | Partial — BCP/DR exercise Roadmap v1.1 |

### CC8 Change Management

| ID | Description | TechNova Implementation | Evidence | Status |
|---|---|---|---|---|
| CC8.1 | Authorises, designs, develops, tests, approves, implements changes. | Git PR flow; CODEOWNERS on security-sensitive files; no automated test suite in v1.0 (honest gap). | Git + `CODEOWNERS` | **Partial — no test suite; Roadmap v1.1** |

### CC9 Risk Mitigation

| ID | Description | TechNova Implementation | Evidence | Status |
|---|---|---|---|---|
| CC9.1 | Risk mitigation activities for business disruption. | Qdrant rebuild from `/docs/`; BM25 pickle regeneration via `POST /api/ingest {"force_reingest": true}`. | `backend/routers/ingest.py` | Implemented |
| CC9.2 | Vendor and business partner risk managed. | DPAs and DPO approvals on file. | `legal-and-commercial/SUB_PROCESSORS.md` | Implemented |

### Availability — A1

| ID | Description | TechNova Implementation | Evidence | Status |
|---|---|---|---|---|
| A1.1 | Maintains, monitors, evaluates current and future processing capacity. | Singleton model loading at startup keeps latency deterministic; Vercel and Neon provide autoscaling. | `backend/main.py` lifespan | Partial — capacity model Roadmap v1.1 |
| A1.2 | Environmental protections, software, data back-up processes. | Neon PITR; corpus PDFs are canonical in git (tracked large files via LFS Roadmap v1.1). | Neon configuration | Partial |
| A1.3 | Tests recovery plan. | No formal DR exercise in v1.0. | — | Roadmap |

### Confidentiality — C1

| ID | Description | TechNova Implementation | Evidence | Status |
|---|---|---|---|---|
| C1.1 | Identifies and maintains confidential information. | `DATA_CLASSIFICATION_MATRIX.md`; `DOCUMENT_METADATA` in `backend/config.py` as source of truth. | `backend/config.py` | Implemented |
| C1.2 | Disposes of confidential information. | Re-ingest replaces/removes; Qdrant supports filtered delete; BM25 rebuild enforced on force_reingest. | `backend/services/store.py` | Partial — verified deletion attestation Roadmap v1.1 |

## 3. Summary Score

| Category | Implemented | Partial | Roadmap | N/A |
|---|---|---|---|---|
| CC1 | 4 | 1 | 0 | 0 |
| CC2 | 2 | 1 | 0 | 0 |
| CC3 | 3 | 1 | 0 | 0 |
| CC4 | 1 | 1 | 0 | 0 |
| CC5 | 3 | 0 | 0 | 0 |
| CC6 | 3 | 3 | 2 | 0 |
| CC7 | 1 | 3 | 1 | 0 |
| CC8 | 0 | 1 | 0 | 0 |
| CC9 | 2 | 0 | 0 | 0 |
| A1 | 0 | 2 | 1 | 0 |
| C1 | 1 | 1 | 0 | 0 |
| **Total (33 points)** | **20** | **14** | **4** | **0** |

## 4. Gap Remediation Plan (Type I Readiness)

Target: SOC 2 Type I observation window open in Q4 2026 (around 2026-10-16, the next review cycle).

### Critical gaps (must-close)

1. **CC6.1 — Authentication and identity.** Remove the "role in request body" pattern. Integrate SSO (OIDC via TechNova IdP); resolve role server-side from token claims; revoke support for client-supplied role. Effort: ~3 engineering weeks. Owner: Platform Engineering.
2. **CC7.1 — Centralised logging.** Ship uvicorn + app + Vercel + Neon logs to a central store (Datadog or Grafana Loki). Effort: 2 weeks. Owner: Platform Engineering.
3. **CC8.1 — Automated testing.** Build a minimum viable test suite covering: security pre-filter correctness (Qdrant and BM25 paths), classification mapping integrity, API contract tests for `/api/query` and `/api/ingest`. Effort: 4 weeks. Owner: Platform Engineering.
4. **CC6.3 / CC6.7 — Access reviews.** Quarterly attestation of repository, Vercel, Neon, and Qdrant Cloud access. Formalised template. Effort: 1 week. Owner: Trust & Security.

### Supporting gaps

5. **CC4.2 — Risk register.** Materialise threat register derived from `THREAT_MODEL.md` into a tracked issue board.
6. **CC7.4 — Incident response plan.** Expand beyond the on-call runbook to cover data-impact incidents (notification chain, regulatory timing, DPO involvement).
7. **A1.1 / A1.3 — Capacity and DR testing.** Document capacity thresholds and run one DR exercise per year.
8. **C1.2 — Deletion attestation.** Produce a verifiable deletion log when removing chunks, covering Qdrant, BM25 pickle, corpus mirror, and chat history.

### Evidence collection strategy

An evidence locker is maintained at `industry-documents/architecture-and-ops/EVIDENCE_INDEX.md` (Roadmap v1.1). For each implemented control, the locker will catalogue screenshots, config exports, log samples, and change tickets.

## 5. Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Trust & Security | Initial release |
