# TechNova RAG — ISO/IEC 27001:2022 Statement of Applicability

| Field | Value |
|---|---|
| Owner | TechNova Trust & Security |
| Classification | INTERNAL |
| Last Reviewed | 2026-04-16 |
| Next Review | 2026-10-16 |
| Version | 1.0 |

## 1. Scope

This Statement of Applicability covers all 93 controls from ISO/IEC 27001:2022 Annex A. Scope of applicability is the TechNova RAG platform (backend FastAPI service, Next.js frontend, Qdrant vector store, optional Neon Postgres mirror, and associated corpus in `/docs/`).

Status values: **Y** — applicable and implemented; **Partial** — applicable, in progress or partially implemented; **Roadmap** — applicable, planned (not yet implemented); **N** — not applicable (with justification). TechNova is a small-company deployment; several organisational controls are sized accordingly.

## 2. A.5 — Organisational Controls (37 controls)

| Control | Title | Applicable | Justification / Implementation | Status | Owner |
|---|---|---|---|---|---|
| A.5.1 | Policies for information security | Y | Compliance corpus under `industry-documents/` | Y | Trust & Security |
| A.5.2 | Information security roles and responsibilities | Y | Trust & Security as control owner; CODEOWNERS on security files | Y | Trust & Security |
| A.5.3 | Segregation of duties | Y | PR review + CODEOWNERS; four-eyes on security-sensitive files | Partial | Platform Engineering |
| A.5.4 | Management responsibilities | Y | Board-level oversight documented in Board_Minutes_Q4 | Y | Executive |
| A.5.5 | Contact with authorities | Y | DPO designated; breach notification path defined | Partial | Trust & Security |
| A.5.6 | Contact with special interest groups | Y | Membership pending (OWASP, FIRST) | Roadmap v1.1 | Trust & Security |
| A.5.7 | Threat intelligence | Y | Manual monitoring of CVE feeds; automation Roadmap v1.1 | Partial | Platform Engineering |
| A.5.8 | Information security in project management | Y | This compliance corpus is the gate | Y | Trust & Security |
| A.5.9 | Inventory of information and other associated assets | Y | `DOCUMENT_METADATA` + `SBOM.md` | Y | Platform Engineering |
| A.5.10 | Acceptable use of information and other associated assets | Y | `legal-and-commercial/ACCEPTABLE_USE.md` | Y | Trust & Security |
| A.5.11 | Return of assets | Y | HR offboarding flow (TechNova_HR_Policy_Handbook.pdf) | Y | People Ops |
| A.5.12 | Classification of information | Y | `DATA_CLASSIFICATION_MATRIX.md` + `SECURITY_LEVELS` in `backend/config.py` | Y | Trust & Security |
| A.5.13 | Labelling of information | Y | `security_level` + `security_label` in Qdrant payload and Postgres mirror | Y | Platform Engineering |
| A.5.14 | Information transfer | Y | TLS for all external boundaries; DPA on sub-processor transfers | Y | Platform Engineering |
| A.5.15 | Access control | Y | `ROLE_CLEARANCE` + dual pre-filter | Y | Platform Engineering |
| A.5.16 | Identity management | Partial | No SSO in v1.0; role passed in request body | Partial — SSO Roadmap v1.1 | Platform Engineering |
| A.5.17 | Authentication information | Y | Secrets in env / secret manager; no hard-coded credentials | Y | Platform Engineering |
| A.5.18 | Access rights | Y | Quarterly review (Roadmap v1.1 formalisation) | Partial | Trust & Security |
| A.5.19 | Information security in supplier relationships | Y | `SUB_PROCESSORS.md`; DPAs with OpenAI, Neon, Vercel, Qdrant Cloud | Y | Legal |
| A.5.20 | Addressing information security within supplier agreements | Y | DPAs include incident-notification clauses | Y | Legal |
| A.5.21 | Managing information security in the ICT supply chain | Y | Dependency pinning; SBOM regeneration runbook | Partial | Platform Engineering |
| A.5.22 | Monitoring, review and change management of supplier services | Y | Sub-processor quarterly review | Partial | Trust & Security |
| A.5.23 | Information security for use of cloud services | Y | CSP controls documented for Vercel, Neon, OpenAI, Qdrant Cloud | Y | Platform Engineering |
| A.5.24 | Information security incident management planning and preparation | Y | Incident response plan (Roadmap v1.1 for data-impact incidents) | Partial | Trust & Security |
| A.5.25 | Assessment and decision on information security events | Y | Severity ladder in `VULNERABILITY_DISCLOSURE_POLICY.md` | Y | Trust & Security |
| A.5.26 | Response to information security incidents | Y | On-call runbook covers operational path | Partial | Platform Engineering |
| A.5.27 | Learning from information security incidents | Y | Post-incident review in TechNova_Security_Incident_Report.pdf | Partial | Trust & Security |
| A.5.28 | Collection of evidence | Y | Logs and PR history; forensic-grade evidence collection Roadmap v1.1 | Partial | Trust & Security |
| A.5.29 | Information security during disruption | Y | Reingest procedure; managed-service failover | Partial | Platform Engineering |
| A.5.30 | ICT readiness for business continuity | Y | DR plan Roadmap v1.1 | Roadmap | Platform Engineering |
| A.5.31 | Legal, statutory, regulatory and contractual requirements | Y | GDPR DPIA on file; DPAs signed | Y | Legal |
| A.5.32 | Intellectual property rights | Y | License table in `SBOM.md` | Y | Legal |
| A.5.33 | Protection of records | Y | Board minutes RESTRICTED; 90-day retention for chat | Y | Trust & Security |
| A.5.34 | Privacy and protection of PII | Y | `DPIA.md` | Y | DPO |
| A.5.35 | Independent review of information security | Y | External pentest (see `PENTEST_REPORT.md`) | Partial | Trust & Security |
| A.5.36 | Compliance with policies, rules and standards for information security | Y | This corpus; bi-annual review cycle | Y | Trust & Security |
| A.5.37 | Documented operating procedures | Y | On-call runbook, ingest procedure | Y | Platform Engineering |

## 3. A.6 — People Controls (8 controls)

| Control | Title | Applicable | Justification / Implementation | Status | Owner |
|---|---|---|---|---|---|
| A.6.1 | Screening | Y | Pre-hire background checks per HR policy | Y | People Ops |
| A.6.2 | Terms and conditions of employment | Y | Employment contracts include confidentiality | Y | People Ops |
| A.6.3 | Information security awareness, education and training | Y | TechNova_Training_Compliance.pdf covers baseline training | Y | Trust & Security |
| A.6.4 | Disciplinary process | Y | HR policy handbook | Y | People Ops |
| A.6.5 | Responsibilities after termination or change of employment | Y | Offboarding includes access revocation | Y | People Ops |
| A.6.6 | Confidentiality or non-disclosure agreements | Y | Standard in employment contracts; separate NDA for contractors | Y | Legal |
| A.6.7 | Remote working | Y | Remote working policy in HR handbook | Y | People Ops |
| A.6.8 | Information security event reporting | Y | `security@technova.example` + internal reporting channel | Y | Trust & Security |

## 4. A.7 — Physical Controls (14 controls)

TechNova RAG v1.0 is a cloud-hosted service. Physical controls are primarily inherited from sub-processors (Vercel, Neon, AWS/GCP for OpenAI, Qdrant Cloud hosting). TechNova's own offices host no production data.

| Control | Title | Applicable | Justification / Implementation | Status | Owner |
|---|---|---|---|---|---|
| A.7.1 | Physical security perimeters | N (inherited) | CSP-managed data centres; SOC 2 reports available | Y (inherited) | CSP |
| A.7.2 | Physical entry | N (inherited) | CSP-managed | Y (inherited) | CSP |
| A.7.3 | Securing offices, rooms and facilities | Y | Office access controlled; no production storage on-prem | Y | Facilities |
| A.7.4 | Physical security monitoring | N (inherited) | CSP-managed | Y (inherited) | CSP |
| A.7.5 | Protecting against physical and environmental threats | N (inherited) | CSP-managed | Y (inherited) | CSP |
| A.7.6 | Working in secure areas | Y | No secure-area concept beyond office | Partial | Facilities |
| A.7.7 | Clear desk and clear screen | Y | Endpoint policy in IT asset policy | Y | People Ops |
| A.7.8 | Equipment siting and protection | Y | Endpoint device management per IT asset policy | Y | IT |
| A.7.9 | Security of assets off-premises | Y | MDM on staff laptops; disk encryption required | Y | IT |
| A.7.10 | Storage media | Y | No removable media for production data | Y | IT |
| A.7.11 | Supporting utilities | N (inherited) | CSP-managed | Y (inherited) | CSP |
| A.7.12 | Cabling security | N (inherited) | CSP-managed | Y (inherited) | CSP |
| A.7.13 | Equipment maintenance | N (inherited) | CSP-managed for production; internal for office | Y (inherited) | CSP / IT |
| A.7.14 | Secure disposal or re-use of equipment | Y | Endpoint decommission includes disk wipe | Y | IT |

## 5. A.8 — Technological Controls (34 controls)

| Control | Title | Applicable | Justification / Implementation | Status | Owner |
|---|---|---|---|---|---|
| A.8.1 | User endpoint devices | Y | MDM, disk encryption, OS patching via IT asset policy | Y | IT |
| A.8.2 | Privileged access rights | Y | GitHub admin, Vercel owner, Neon, Qdrant Cloud — small number of named individuals | Partial — PAM not implemented | Platform Engineering |
| A.8.3 | Information access restriction | Y | Dual pre-filter on dense + lexical; `ROLE_CLEARANCE` mapping | Y | Platform Engineering |
| A.8.4 | Access to source code | Y | GitHub team permissions; CODEOWNERS | Y | Platform Engineering |
| A.8.5 | Secure authentication | Partial | No SSO in v1.0 for the app itself | Partial — Roadmap v1.1 | Platform Engineering |
| A.8.6 | Capacity management | Y | Vercel autoscale; Neon autoscale; Qdrant capacity thresholds documented in `ARCHITECTURE.md` | Partial | Platform Engineering |
| A.8.7 | Protection against malware | Y | Code-signed container images; no arbitrary upload paths; dependency pinning | Y | Platform Engineering |
| A.8.8 | Management of technical vulnerabilities | Y | `pip-audit`, `npm audit`; severity SLAs in `VULNERABILITY_DISCLOSURE_POLICY.md` | Partial | Platform Engineering |
| A.8.9 | Configuration management | Y | Infrastructure as code via Docker Compose + Vercel project config | Partial | Platform Engineering |
| A.8.10 | Information deletion | Y | Reingest; chunk-level delete via Qdrant filter | Partial — verification log Roadmap v1.1 | Platform Engineering |
| A.8.11 | Data masking | Roadmap | No PII redaction pipeline in v1.0 | Roadmap v1.2 | Platform Engineering |
| A.8.12 | Data leakage prevention | Y | Dual pre-filter; egress limited to declared sub-processors | Partial | Platform Engineering |
| A.8.13 | Information backup | Y | Neon PITR; corpus canonical in git | Partial | Platform Engineering |
| A.8.14 | Redundancy of information processing facilities | Y | Inherited from Vercel/Neon; single Qdrant instance in dev | Partial | Platform Engineering |
| A.8.15 | Logging | Y | uvicorn + app logs; Postgres query logs | Partial — centralised SIEM Roadmap v1.1 | Platform Engineering |
| A.8.16 | Monitoring activities | Partial | Host metrics via Vercel/Neon; no app-level UEBA | Partial | Platform Engineering |
| A.8.17 | Clock synchronisation | Y | NTP on all hosts; managed services time-sync by CSP | Y | Platform Engineering |
| A.8.18 | Use of privileged utility programs | Y | Minimal footprint in container images; no shell in distroless Roadmap v1.1 | Partial | Platform Engineering |
| A.8.19 | Installation of software on operational systems | Y | Only images built from CI; no manual install | Y | Platform Engineering |
| A.8.20 | Network security | Y | CORS pinning; Qdrant not public in prod; Neon TLS | Y | Platform Engineering |
| A.8.21 | Security of network services | Y | Sub-processor security posture reviewed | Y | Platform Engineering |
| A.8.22 | Segregation of networks | Y | Prod/dev compose networks separate; frontend and backend in different trust zones | Partial | Platform Engineering |
| A.8.23 | Web filtering | N/A | Service has no outbound-user web-filtering need | N/A | — |
| A.8.24 | Use of cryptography | Y | TLS 1.2+; managed encryption at rest | Y | Platform Engineering |
| A.8.25 | Secure development lifecycle | Y | PR review + compliance corpus | Partial — no formal SAST in v1.0 | Platform Engineering |
| A.8.26 | Application security requirements | Y | OWASP Top 10 covered; see `PENTEST_REPORT.md` | Partial | Platform Engineering |
| A.8.27 | Secure system architecture and engineering principles | Y | Threat model; defence in depth (dual pre-filter) | Y | Platform Engineering |
| A.8.28 | Secure coding | Y | Linting via eslint; Python typing | Partial — no SAST tooling in CI | Platform Engineering |
| A.8.29 | Security testing in development and acceptance | Y | Manual pentest; no automated test suite | Partial — Roadmap v1.1 | Platform Engineering |
| A.8.30 | Outsourced development | N | No outsourced development | N/A | — |
| A.8.31 | Separation of development, test and production environments | Y | Dev compose, Vercel preview, Vercel prod | Y | Platform Engineering |
| A.8.32 | Change management | Y | PR flow + CODEOWNERS + compliance corpus | Y | Platform Engineering |
| A.8.33 | Test information | Y | Synthetic queries; no production data in test | Y | Platform Engineering |
| A.8.34 | Protection of information systems during audit testing | Y | Pentest windows scheduled; prod changes frozen during audit | Y | Platform Engineering |

## 6. Summary

| Annex | Total | Y | Partial | Roadmap | N/A |
|---|---|---|---|---|---|
| A.5 Organisational | 37 | 22 | 13 | 2 | 0 |
| A.6 People | 8 | 8 | 0 | 0 | 0 |
| A.7 Physical | 14 | 12 (inherited 8) | 2 | 0 | 0 |
| A.8 Technological | 34 | 13 | 17 | 2 | 2 |
| **Total** | **93** | **55** | **32** | **4** | **2** |

## 7. Priority Remediation (Path to ISO 27001 Certification)

1. A.5.16 / A.8.5 — SSO and server-side identity.
2. A.8.15 / A.8.16 — Centralised logging + monitoring.
3. A.8.25 / A.8.28 / A.8.29 — SDLC maturity: SAST, SCA automation, automated test suite.
4. A.5.30 — Documented BCP/DR plan and annual exercise.
5. A.8.11 — PII redaction pipeline.
6. A.5.28 / A.8.10 — Evidence collection and verified deletion.

## 8. Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Trust & Security | Initial release |
