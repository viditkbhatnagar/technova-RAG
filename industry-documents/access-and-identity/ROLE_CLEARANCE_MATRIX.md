# Role and Clearance Authorization Matrix

| Field | Value |
|---|---|
| Owner | TechNova Identity and Access |
| Classification | INTERNAL |
| Last Reviewed | 2026-04-16 |
| Next Review | 2026-10-16 |
| Version | 1.0 |

---

## 1. Purpose and Scope

This document is the authoritative source for the role-to-document access model of the TechNova RAG platform. It binds the logical role taxonomy to the physical enforcement points in the codebase (`backend/config.py`, `backend/services/security.py`) and to the corpus of eleven internal PDFs that constitute the knowledge base for Project A (open chat) and Project B (role-gated secure chat).

Where any ambiguity arises between this document, `backend/config.py`, and operational behaviour, `backend/config.py` wins for runtime enforcement and this document wins for governance intent. Discrepancies between the two must be resolved before the next quarterly review.

This matrix governs access to the RAG corpus only. Access to raw PDF files on filesystems, cloud object stores, and source control is governed by separate data-classification controls owned by Data Governance.

---

## 2. Principles

The authorization model is built on three non-negotiable principles.

### 2.1 Least privilege

Every role is granted the minimum clearance necessary to perform its duties. Roles are additive in clearance, but not in scope: a manager can see what an employee sees plus CONFIDENTIAL material, but no user has access to material outside their clearance band regardless of business justification, except through the documented break-glass procedure (see `BREAK_GLASS_PROCEDURE.md`).

### 2.2 Separation of duties

The authority to grant a role, classify a document, ingest the corpus, and query the corpus are held by different functions. A single individual cannot unilaterally expand their own access. The chain of custody for any classification or role change is captured in the audit log (see `AUDIT_LOG_SCHEMA.md`).

### 2.3 No role escalation at query time

Roles are evaluated at request entry and are not re-evaluated, relaxed, or expanded anywhere downstream in the retrieval pipeline. In particular, the self-correcting retrieval loop in `backend/services/security.py` (`self_correcting_retrieve`) never widens the set of allowed chunks; it only expands the lexical surface of the query via the `_SYNONYMS` dictionary. A restricted chunk that was outside the allowed pool at stage one is outside at stage N. This is the invariant cited throughout the design documents.

---

## 3. Role Definitions

TechNova RAG v1.0 recognises three roles. Roles are mapped to numeric clearances in `ROLE_CLEARANCE` in `backend/config.py`.

### 3.1 employee (clearance = 1)

- **Population**: all full-time and part-time employees, and contractors with a signed confidentiality agreement.
- **Purpose**: day-to-day reference of public and internal operating procedures, HR self-service, IT policy look-ups, compliance training content.
- **Typical queries**: "What is the IT password rotation policy?", "How do I request PTO?", "What are the fire drill procedures?"
- **Grant authority**: provisioned automatically on HR onboarding.

### 3.2 manager (clearance = 2)

- **Population**: people managers, team leads, programme managers, product managers, and finance partners above an agreed seniority band.
- **Purpose**: operational decision-making that requires visibility into financial results, product direction, and vendor commitments.
- **Typical queries**: "What was Q4 opex variance versus plan?", "Which vendors are up for renewal in H1 2026?", "What is the product roadmap theme for Q2?"
- **Grant authority**: HR Business Partner plus the employee's VP; provisioned via ticket today, via SSO group in v1.1.

### 3.3 admin (clearance = 3)

- **Population**: executive leadership, board members with an active seat, General Counsel, Chief Information Security Officer, Head of People.
- **Purpose**: governance, security incident response, compensation setting, board-level deliberation.
- **Typical queries**: "What were the findings of the last security incident review?", "What is the current salary band for L6 engineers?", "Summarise the Q4 board minutes."
- **Grant authority**: CEO or General Counsel; two-of-three executive approval for external board members. Provisioning via ticket today, via SSO+SCIM with attestation in v1.1.

Roles are mutually exclusive at the authorization layer. A user is exactly one of {employee, manager, admin}. There is no hierarchical "inherits" marker in config; inheritance is expressed numerically through clearance.

---

## 4. Clearance Scheme

Document sensitivity is stratified into four bands. The numeric values are the exact integers emitted by `SECURITY_LEVELS` in `backend/config.py` and used in Qdrant payload filters.

| Clearance band | Numeric value | Intent |
|---|---|---|
| PUBLIC | 0 | No harm on disclosure; often already externally available. |
| INTERNAL | 1 | Internal operations, standard HR, IT, runbooks. Non-public but low sensitivity. |
| CONFIDENTIAL | 2 | Business-sensitive: finance, roadmap, third-party commitments. |
| RESTRICTED | 3 | Material non-public information, personnel compensation, security incident detail. |

The comparison at runtime is `document.security_level <= user.clearance`. Thus:

- employee (1) sees PUBLIC (0) and INTERNAL (1).
- manager (2) sees PUBLIC through CONFIDENTIAL (0, 1, 2).
- admin (3) sees everything including RESTRICTED (3).

Only admins can access RESTRICTED content. No role has "write" semantics on documents; the corpus is read-only through the application.

---

## 5. Corpus x Role Access Matrix

The matrix below is the authoritative access table for the eleven production documents. Classification in the second column mirrors `DOCUMENT_METADATA` in `backend/config.py`. Cells show Accessible (A) or Denied (D) with rationale.

| Document | Classification | employee (1) | manager (2) | admin (3) |
|---|---|---|---|---|
| Training_Compliance | PUBLIC (0) | A - mandatory training content, cleared for all staff | A | A |
| HR_Policy_Handbook | INTERNAL (1) | A - operational HR reference | A | A |
| IT_Asset_Policy | INTERNAL (1) | A - required for device enrolment and acceptable use | A | A |
| Platform_Architecture | INTERNAL (1) | A - engineering reference, no secrets | A | A |
| OnCall_Runbook | INTERNAL (1) | A - incident response steps | A | A |
| Q4_Financial_Report | CONFIDENTIAL (2) | D - contains pre-release financial detail | A - required for forecasting and budget reviews | A |
| Product_Roadmap_2026 | CONFIDENTIAL (2) | D - forward-looking commitments under embargo | A - required to align team planning | A |
| Vendor_Contracts | CONFIDENTIAL (2) | D - commercial terms and pricing are confidential | A - required for vendor management | A |
| Salary_Structure | RESTRICTED (3) | D - personnel compensation data | D - compensation not visible to line managers in this corpus | A |
| Board_Minutes_Q4 | RESTRICTED (3) | D - board deliberations | D - board deliberations | A |
| Security_Incident_Report | RESTRICTED (3) | D - active security intelligence | D - active security intelligence | A |

Rationale summary:

- The four INTERNAL documents are the backbone of employee self-service and are the main driver of Project A and Project B traffic from the employee population.
- The three CONFIDENTIAL documents are where manager-tier access is most valuable; all three are subject to a formal embargo policy maintained by Legal and Communications.
- The three RESTRICTED documents concentrate the material non-public risk of the corpus. They are the target of the adversarial test harness described in `RBAC_DESIGN.md` section (g).

The single PUBLIC document is retained for two reasons: it is the anchor for the compliance training workflow, and it provides a control document that should return results even for the lowest clearance, enabling smoke tests of the pipeline.

---

## 6. Role Grant Authority and Approval Chains

Role assignment is a governed process. The matrix below states who requests, who approves, and who records the grant.

| Role | Requestor | Approver | Recorder | Provisioning path (v1.0) | Provisioning path (v1.1) |
|---|---|---|---|---|---|
| employee | HR on hire | HR Business Partner | HRIS (Workday) | Manual list maintained alongside HRIS | SCIM 2.0 user create from HRIS, JIT on first SSO |
| manager | Hiring manager | VP + HRBP | HRIS | Ticket to Platform Eng | SCIM group `TN-Managers` membership |
| admin | CEO or GC | CEO + GC (two signatures for external board members) | Office of the CEO | Ticket to Platform Eng, access reviewed monthly | SCIM group `TN-Admins` with quarterly attestation |

Revocation follows the same chain in reverse. HR-driven deactivation (termination, role change) has an SLA of four hours in v1.0 and will be five minutes via SCIM deprovisioning in v1.1.

No role change short-circuits the chain. A manager cannot grant employee clearance, and an admin cannot grant admin clearance without the second signature. The ticketing system ID is captured in the audit record (event type `ROLE_GRANT` / `ROLE_REVOKE`).

---

## 7. Review Cadence

Two review cycles apply:

1. **Quarterly review of role assignments.** Security and Compliance pull a dump of active users and their assigned role. Managers attest to their direct reports' continued need for manager or admin clearance. Any user without attestation within fifteen business days is automatically downgraded to employee. This review is tracked as a compliance control aligned with SOC 2 CC6.1.

2. **Annual review of the matrix itself.** This document is re-read in full each year by Data Governance plus the Security Officer. Any role addition, document reclassification, or structural change requires Steering Committee sign-off. The next scheduled review is 2026-10-16 (mid-cycle) and 2027-04-16 (annual).

Ad-hoc reviews are triggered by any of: a new document entering the corpus, a security incident implicating this matrix, a regulatory change affecting classification, or the deprecation of a role.

---

## 8. Change Control

The matrix and its backing configuration are modified through the following process.

1. **Role added or semantics changed.** Requires a CLAUDE-spec style design note, a pull request modifying `ROLE_CLEARANCE` in `backend/config.py`, and a coordinated update to the RBAC design document. Re-ingest is not required because roles are evaluated at query time against chunk payload metadata.

2. **Document reclassified.** The `security_level` field in `DOCUMENT_METADATA` in `backend/config.py` is updated and a full re-ingest is triggered: `curl -X POST http://localhost:8000/api/ingest -d '{"force_reingest": true}'`. Re-ingest is necessary because the existing Qdrant payload retains the previous `security_level`; the pre-filter operates on payload, not config, and payload is only rewritten by re-ingest. Failure to re-ingest after a classification change is a severity-1 control drift.

3. **Document added or removed.** Update `DOCUMENT_METADATA` first; the loader silently skips any PDF not listed. Then re-ingest. Removal from `DOCUMENT_METADATA` without dropping the Qdrant collection will leave orphaned vectors - use `force_reingest: true` to guarantee a clean collection.

4. **Clearance scheme modified.** Reserved; changing `SECURITY_LEVELS` is a breaking change requiring migration of every chunk payload and of Postgres `documents` and `chunks` mirror tables. Treated as a major version bump.

All changes are recorded against this document via the revision history table in section 10, and a `CONFIG_CHANGE` event is written to the audit log with the commit SHA and the PR URL.

---

## 9. Appendix A - Configuration Excerpt

The following is the authoritative excerpt of `backend/config.py` that implements this matrix. Any drift between this excerpt and the live file must be reconciled before merge.

```python
# backend/config.py

SECURITY_LEVELS = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "CONFIDENTIAL": 2,
    "RESTRICTED": 3,
}

ROLE_CLEARANCE = {
    "employee": 1,
    "manager": 2,
    "admin": 3,
}

DOCUMENT_METADATA = {
    "Training_Compliance.pdf":       {"doc_slug": "training_compliance",       "domain": "compliance", "security": "PUBLIC"},
    "HR_Policy_Handbook.pdf":        {"doc_slug": "hr_policy_handbook",        "domain": "hr",         "security": "INTERNAL"},
    "IT_Asset_Policy.pdf":           {"doc_slug": "it_asset_policy",           "domain": "it",         "security": "INTERNAL"},
    "Platform_Architecture.pdf":     {"doc_slug": "platform_architecture",     "domain": "engineering","security": "INTERNAL"},
    "OnCall_Runbook.pdf":            {"doc_slug": "oncall_runbook",            "domain": "engineering","security": "INTERNAL"},
    "Q4_Financial_Report.pdf":       {"doc_slug": "q4_financial_report",       "domain": "finance",    "security": "CONFIDENTIAL"},
    "Product_Roadmap_2026.pdf":      {"doc_slug": "product_roadmap_2026",      "domain": "product",    "security": "CONFIDENTIAL"},
    "Vendor_Contracts.pdf":          {"doc_slug": "vendor_contracts",          "domain": "legal",      "security": "CONFIDENTIAL"},
    "Salary_Structure.pdf":          {"doc_slug": "salary_structure",          "domain": "hr",         "security": "RESTRICTED"},
    "Board_Minutes_Q4.pdf":          {"doc_slug": "board_minutes_q4",          "domain": "governance", "security": "RESTRICTED"},
    "Security_Incident_Report.pdf":  {"doc_slug": "security_incident_report",  "domain": "security",   "security": "RESTRICTED"},
}
```

The filename-to-`security_level` derivation at ingest time is `SECURITY_LEVELS[DOCUMENT_METADATA[filename]["security"]]`. Chunks written to Qdrant and to the Postgres `chunks` mirror carry the resolved integer, not the symbolic name.

---

## 10. Revision History

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Identity & Access | Initial release |
