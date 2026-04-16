# TechNova RAG — Industry Documentation Pack

| Owner | Classification | Last Reviewed | Next Review | Version |
|---|---|---|---|---|
| TechNova Trust & Security | INTERNAL | 2026-04-16 | 2026-10-16 | 1.0 |

This pack is the single place enterprise procurement, security, legal, and risk teams land when evaluating TechNova RAG for deployment. It covers the six disciplines that every serious enterprise buyer asks about: **security & compliance**, **AI governance**, **access & identity**, **architecture & operations**, **legal & commercial**, and **end-user documentation**.

Every document is specific to the TechNova codebase — real file paths, real dependencies, real configuration — and honest about v1.0 gaps. Where a control is aspirational, it is labelled `Roadmap — v1.1` (or later) rather than dressed up. Enterprise buyers trust honesty over a perfect-looking façade.

---

## How to navigate this pack

**If you are on the buyer side** and reviewing TechNova for procurement:

| Persona | Start here | Then read |
|---|---|---|
| Security / GRC | [security-and-compliance/THREAT_MODEL.md](security-and-compliance/THREAT_MODEL.md), [security-and-compliance/SOC2_READINESS.md](security-and-compliance/SOC2_READINESS.md) | [security-and-compliance/PENTEST_REPORT.md](security-and-compliance/PENTEST_REPORT.md), [access-and-identity/RBAC_DESIGN.md](access-and-identity/RBAC_DESIGN.md) |
| AI Risk | [ai-specific/MODEL_CARD.md](ai-specific/MODEL_CARD.md), [ai-specific/EU_AI_ACT_CLASSIFICATION.md](ai-specific/EU_AI_ACT_CLASSIFICATION.md) | [ai-specific/RETRIEVAL_EVAL_REPORT.md](ai-specific/RETRIEVAL_EVAL_REPORT.md), [ai-specific/PROMPT_INJECTION_REDTEAM.md](ai-specific/PROMPT_INJECTION_REDTEAM.md) |
| Legal | [legal-and-commercial/MSA_TEMPLATE.md](legal-and-commercial/MSA_TEMPLATE.md), [legal-and-commercial/DPA_TEMPLATE.md](legal-and-commercial/DPA_TEMPLATE.md) | [legal-and-commercial/SUBPROCESSORS.md](legal-and-commercial/SUBPROCESSORS.md), [legal-and-commercial/OSS_LICENSE_INVENTORY.md](legal-and-commercial/OSS_LICENSE_INVENTORY.md) |
| Architecture | [architecture-and-ops/HIGH_LEVEL_DESIGN.md](architecture-and-ops/HIGH_LEVEL_DESIGN.md), [architecture-and-ops/ADR_0001_hybrid_retrieval_with_rrf.md](architecture-and-ops/ADR_0001_hybrid_retrieval_with_rrf.md) | [architecture-and-ops/SLA_SLO.md](architecture-and-ops/SLA_SLO.md), [architecture-and-ops/DR_BCP.md](architecture-and-ops/DR_BCP.md) |
| IT / IAM | [access-and-identity/ROLE_CLEARANCE_MATRIX.md](access-and-identity/ROLE_CLEARANCE_MATRIX.md), [access-and-identity/SSO_SCIM_PLAN.md](access-and-identity/SSO_SCIM_PLAN.md) | [access-and-identity/AUDIT_LOG_SCHEMA.md](access-and-identity/AUDIT_LOG_SCHEMA.md), [access-and-identity/BREAK_GLASS_PROCEDURE.md](access-and-identity/BREAK_GLASS_PROCEDURE.md) |
| Ops / SRE | [architecture-and-ops/RUNBOOKS.md](architecture-and-ops/RUNBOOKS.md), [architecture-and-ops/OBSERVABILITY_PLAN.md](architecture-and-ops/OBSERVABILITY_PLAN.md) | [end-user/ADMIN_GUIDE.md](end-user/ADMIN_GUIDE.md), [architecture-and-ops/CAPACITY_AND_COST_MODEL.md](architecture-and-ops/CAPACITY_AND_COST_MODEL.md) |
| End users | [end-user/USER_GUIDE.md](end-user/USER_GUIDE.md) | [end-user/CHANGELOG.md](end-user/CHANGELOG.md) |
| New customer | [end-user/ONBOARDING_PLAYBOOK.md](end-user/ONBOARDING_PLAYBOOK.md) | [end-user/ADMIN_GUIDE.md](end-user/ADMIN_GUIDE.md), [access-and-identity/SSO_SCIM_PLAN.md](access-and-identity/SSO_SCIM_PLAN.md) |

---

## 1. [security-and-compliance/](security-and-compliance/)

Nine documents covering adversarial threat analysis, certification mappings, and disclosure posture.

| Document | What it covers |
|---|---|
| [THREAT_MODEL.md](security-and-compliance/THREAT_MODEL.md) | STRIDE across seven trust boundaries, LLM-specific threats (direct + indirect prompt injection, jailbreak, tool-use exfiltration), and mitigation matrix with file references |
| [DATA_FLOW_DIAGRAM.md](security-and-compliance/DATA_FLOW_DIAGRAM.md) | Mermaid DFDs for context, ingest, Project A query, Project B query (with self-correcting loop), knowledge graph — plus trust-boundary crossings table |
| [DATA_CLASSIFICATION_MATRIX.md](security-and-compliance/DATA_CLASSIFICATION_MATRIX.md) | Four-level scheme (PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED), handling rules per dimension, all 11 corpus PDFs mapped |
| [DPIA.md](security-and-compliance/DPIA.md) | GDPR Art. 35 DPIA — necessity, proportionality, risks to rights & freedoms, measures to address, DPO sign-off block |
| [SOC2_READINESS.md](security-and-compliance/SOC2_READINESS.md) | AICPA Trust Services Criteria mapping (CC1–CC9, A1, C1) with implementation status and gap remediation plan for Type I readiness |
| [ISO27001_SOA.md](security-and-compliance/ISO27001_SOA.md) | ISO/IEC 27001:2022 Statement of Applicability across all 93 Annex A controls |
| [PENTEST_REPORT.md](security-and-compliance/PENTEST_REPORT.md) | Third-party pentest template populated with findings against this codebase (role-in-body High, CORS Medium, timing side channel, etc.) |
| [SBOM.md](security-and-compliance/SBOM.md) | CycloneDX-style inventory of every Python + Node dep, model artefacts, container images, licenses, regeneration commands |
| [VULNERABILITY_DISCLOSURE_POLICY.md](security-and-compliance/VULNERABILITY_DISCLOSURE_POLICY.md) | Scope, safe harbor, SLAs, 90-day coordinated disclosure timeline |

## 2. [ai-specific/](ai-specific/)

Seven documents for AI risk teams under emerging regulation (EU AI Act, NIST AI RMF) and model-governance reviews.

| Document | What it covers |
|---|---|
| [MODEL_CARD.md](ai-specific/MODEL_CARD.md) | Google-style model card for the composed RAG system — component models table, intended use, out-of-scope use, quantitative analysis by role/level/domain |
| [RETRIEVAL_EVAL_REPORT.md](ai-specific/RETRIEVAL_EVAL_REPORT.md) | 100-Q golden set + 20 adversarial; recall@k, MRR, nDCG; ablations (RRF k, self-correction, synonym expansion); 0.000 cross-role leakage |
| [HALLUCINATION_AND_CITATION_POLICY.md](ai-specific/HALLUCINATION_AND_CITATION_POLICY.md) | Must-cite rule, prompt template, confidence-threshold decision flow, refusal templates |
| [PROMPT_INJECTION_REDTEAM.md](ai-specific/PROMPT_INJECTION_REDTEAM.md) | OWASP LLM-01 red-team battery (60 cases × 4 categories), nine-layer defense-in-depth, residual-risk analysis |
| [PII_AND_SUBPROCESSORS.md](ai-specific/PII_AND_SUBPROCESSORS.md) | Per-doc PII inventory, sub-processor data flows, Presidio redaction roadmap |
| [EU_AI_ACT_CLASSIFICATION.md](ai-specific/EU_AI_ACT_CLASSIFICATION.md) | Art. 3(1) AI-system analysis, Annex III screening, Art. 6(3) preparatory-task exception, Art. 50 transparency mapping |
| [BIAS_AND_FAIRNESS_ASSESSMENT.md](ai-specific/BIAS_AND_FAIRNESS_ASSESSMENT.md) | Corpus composition bias, retrieval bias quantification, generation stereotype probe, access-denied fairness analysis |

## 3. [access-and-identity/](access-and-identity/)

Five documents covering the role-gated security model that is the core of Project B.

| Document | What it covers |
|---|---|
| [ROLE_CLEARANCE_MATRIX.md](access-and-identity/ROLE_CLEARANCE_MATRIX.md) | Authoritative 11-doc × 3-role access table, grant-authority chain, review cadence |
| [RBAC_DESIGN.md](access-and-identity/RBAC_DESIGN.md) | Dual pre-filter architecture (Qdrant + BM25) with invariant proof sketch, self-correcting-loop posture, adversarial test harness |
| [SSO_SCIM_PLAN.md](access-and-identity/SSO_SCIM_PLAN.md) | OIDC + SAML flows, Okta/Entra/Google integration, SCIM 2.0 endpoints, JWT model, v1.1 migration plan |
| [AUDIT_LOG_SCHEMA.md](access-and-identity/AUDIT_LOG_SCHEMA.md) | Thirteen event types, common envelope, append-only v1.1 `audit_events` table with HMAC hash chain |
| [BREAK_GLASS_PROCEDURE.md](access-and-identity/BREAK_GLASS_PROCEDURE.md) | 2-of-3 approval, 4h time-box, monitoring flags, auto-expiry, annual drill |

## 4. [architecture-and-ops/](architecture-and-ops/)

Eight documents for architecture review boards and the SRE / on-call teams that will run the system.

| Document | What it covers |
|---|---|
| [HIGH_LEVEL_DESIGN.md](architecture-and-ops/HIGH_LEVEL_DESIGN.md) | Goals & non-goals, system context + logical architecture (mermaid), tenancy, residency, failure isolation |
| [SLA_SLO.md](architecture-and-ops/SLA_SLO.md) | Tiered availability targets, SLIs, SLOs (p50/p95/p99), error-budget math, credit schedule |
| [DR_BCP.md](architecture-and-ops/DR_BCP.md) | RPO/RTO per data class, recovery procedures per scenario, restore runbook, annual DR drill |
| [RUNBOOKS.md](architecture-and-ops/RUNBOOKS.md) | Ten runbooks: ingest, Qdrant, OpenAI, stuck query, re-ingest, credential rotation, BM25 pickle, access-denied spike, Neon failover, frontend rollback |
| [CAPACITY_AND_COST_MODEL.md](architecture-and-ops/CAPACITY_AND_COST_MODEL.md) | Unit economics, three load tiers (Low/Medium/High), scaling bottlenecks, cost-optimization levers |
| [OBSERVABILITY_PLAN.md](architecture-and-ops/OBSERVABILITY_PLAN.md) | Metrics (Prometheus), logs (structured), traces (OTel), dashboards, SLO burn alerts, PII hygiene |
| [ADR_TEMPLATE.md](architecture-and-ops/ADR_TEMPLATE.md) | Michael Nygard ADR format and conventions |
| [ADR_0001_hybrid_retrieval_with_rrf.md](architecture-and-ops/ADR_0001_hybrid_retrieval_with_rrf.md) | Rationale for hybrid dense + BM25 + RRF + rerank, alternatives considered |

## 5. [legal-and-commercial/](legal-and-commercial/)

Six documents for enterprise legal and procurement. MSA and DPA are marked as templates requiring counsel review.

| Document | What it covers |
|---|---|
| [MSA_TEMPLATE.md](legal-and-commercial/MSA_TEMPLATE.md) | Master Services Agreement skeleton, 15 sections plus Exhibits A–E |
| [DPA_TEMPLATE.md](legal-and-commercial/DPA_TEMPLATE.md) | GDPR Art. 28 DPA, SCC Module Two, Annexes I–III, UK IDTA, Swiss FADP |
| [SUBPROCESSORS.md](legal-and-commercial/SUBPROCESSORS.md) | Customer-facing register, 30-day change notice, per-sub-processor data minimization |
| [OSS_LICENSE_INVENTORY.md](legal-and-commercial/OSS_LICENSE_INVENTORY.md) | Every Python + Node dep with license; NOTICE.txt template for Apache-2.0 obligations |
| [ACCEPTABLE_USE_POLICY.md](legal-and-commercial/ACCEPTABLE_USE_POLICY.md) | Prohibited uses, adversarial-probing carve-out for authorized research, consequences ladder |
| [SUPPORT_SLA.md](legal-and-commercial/SUPPORT_SLA.md) | Four tiers, P1–P4 severity matrix, response/resolution targets, escalation path |

## 6. [end-user/](end-user/)

Five documents for administrators and end users — the people actually running and using the system.

| Document | What it covers |
|---|---|
| [ADMIN_GUIDE.md](end-user/ADMIN_GUIDE.md) | Setup, ingest, classification management, monitoring, backup/restore, troubleshooting, full API reference |
| [USER_GUIDE.md](end-user/USER_GUIDE.md) | Asking good questions, reading citations, Project A vs B, access-denied handling, knowledge graph use |
| [ONBOARDING_PLAYBOOK.md](end-user/ONBOARDING_PLAYBOOK.md) | Four-week customer onboarding with weekly gates, RACI matrix, risk mitigations |
| [CHANGELOG.md](end-user/CHANGELOG.md) | Keep-a-Changelog history v0.1 through v1.0, mapped to real commits |
| [VERSIONING_POLICY.md](end-user/VERSIONING_POLICY.md) | SemVer, API versioning plan, data/model/dependency version policies |

---

## Refresh and ownership

| Domain | Primary owner | Refresh cadence |
|---|---|---|
| Security & compliance | Trust & Security | Annual + on incident |
| AI governance | AI Risk & Governance | Annual + on model change |
| Access & identity | Identity & Access | Quarterly |
| Architecture & ops | Platform Engineering | On major release |
| Legal & commercial | Legal | Annual + on sub-processor change |
| End user | Documentation | On every release |

Every document carries its own metadata block (Owner / Classification / Last Reviewed / Next Review / Version) and closes with a Revision History table. The dates in this pack reflect the v1.0 release on 2026-04-16.

## What's out of scope for this pack

- **Marketing / sales material.** Nothing in this pack is marketing; it is evaluation material.
- **Customer-specific configurations.** Per-tenant residency, role mappings, and corpus choices are handled in the [ONBOARDING_PLAYBOOK.md](end-user/ONBOARDING_PLAYBOOK.md).
- **Internal engineering docs that are not buyer-facing.** Those live in the parent repo's [CLAUDE.md](../CLAUDE.md), [MASTER_CONTEXT.md](../MASTER_CONTEXT.md), [API_CONTRACT.md](../API_CONTRACT.md), and [CONVENTIONS.md](../CONVENTIONS.md).

## Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Trust & Security | Initial release — 40 documents across 6 domains |
