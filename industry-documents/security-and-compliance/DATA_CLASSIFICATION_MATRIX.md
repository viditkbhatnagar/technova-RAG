# TechNova RAG — Data Classification Matrix

| Field | Value |
|---|---|
| Owner | TechNova Trust & Security |
| Classification | INTERNAL |
| Last Reviewed | 2026-04-16 |
| Next Review | 2026-10-16 |
| Version | 1.0 |

## 1. Purpose and Scope

This matrix defines how TechNova classifies information that is indexed, retrieved, or displayed by the TechNova RAG platform, and the handling requirements that follow from each classification. It applies to all eleven PDFs in `/docs/`, all derived artefacts (embeddings, chunk text in Qdrant payloads, BM25 pickle, knowledge graph), and all copies of those artefacts (including the optional Neon Postgres corpus mirror).

Out of scope: third-party public datasets, pretraining data of `BAAI/bge-base-en-v1.5` or `gpt-4o-mini`, and end-user queries (governed separately by the chat-history retention policy).

## 2. Classification Levels

TechNova uses four classification levels, defined by the integer mapping in `backend/config.py`:

```python
SECURITY_LEVELS = {"PUBLIC": 0, "INTERNAL": 1, "CONFIDENTIAL": 2, "RESTRICTED": 3}
ROLE_CLEARANCE = {"employee": 1, "manager": 2, "admin": 3}
```

| Level | Integer | Clearance required | Definition | Representative examples |
|---|---|---|---|---|
| PUBLIC | 0 | None | Information intended for unrestricted external release. Disclosure causes no harm. | Published training/compliance materials intended for the public audience. |
| INTERNAL | 1 | employee or above | Day-to-day operational information. Disclosure would cause limited business harm but no regulatory exposure. | HR policy handbook, IT asset policy, platform architecture (non-security-sensitive), on-call runbook. |
| CONFIDENTIAL | 2 | manager or above | Information whose disclosure would cause commercial, financial, or competitive harm. | Financial report, product roadmap, vendor contract terms. |
| RESTRICTED | 3 | admin only | Information whose disclosure would cause individual, legal, or fiduciary harm. | Salary structure (pay data), board minutes, security incident reports. |

## 3. Handling Rules Matrix

| Control | PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED |
|---|---|---|---|---|
| Storage location | Any TechNova-controlled store | TechNova-controlled store with access control | TechNova-controlled store with role-based access and logging | As CONFIDENTIAL plus role=admin only; separate backup key |
| Encryption at rest | Optional but recommended | Required (Qdrant disk, Postgres managed encryption, Vercel build artefacts) | Required | Required + separate key scope from INTERNAL/CONFIDENTIAL (Roadmap v1.1 KMS separation) |
| Encryption in transit | Required (HTTPS) | Required | Required | Required |
| Access control | Open | `ROLE_CLEARANCE >= 1` | `ROLE_CLEARANCE >= 2` | `ROLE_CLEARANCE >= 3` |
| Qdrant pre-filter | No filter necessary | `security_level lte 1` | `security_level lte 2` | `security_level lte 3` |
| BM25 pre-filter | Same | Same | Same | Same (`get_allowed_chunk_ids`) |
| Display in Project A | Allowed | Allowed | Not allowed (product rule) | Not allowed |
| Display in Project B | Allowed to all roles | Allowed to employee+ | Allowed to manager+ | Allowed to admin only |
| Chat-history retention | 90d | 90d | 30d (Roadmap v1.1 shorter for C+R) | 30d (Roadmap v1.1) |
| Disposal | Standard deletion | Standard deletion | Crypto-shred on re-ingest | Crypto-shred + verified removal from Postgres mirror |
| Access logging | Not required | Recommended | Required (Roadmap v1.1 audit table) | Required (Roadmap v1.1) |
| Backup location | Same region | Same region | Same region | Same region, separate IAM scope (Roadmap v1.1) |
| External transmission | Permitted | Legitimate-interest basis | Approved recipients only, DPA required | Prohibited except under legal hold |
| Printing / export | Permitted | Employee-only | Controlled, watermarked (advisory in v1.0) | Prohibited |

## 4. Corpus Mapping — Authoritative

All eleven PDFs in `/docs/` are enumerated in `DOCUMENT_METADATA` (`backend/config.py`). The loader silently skips any PDF not present in this mapping — this is by design and ensures the classification table is the single source of truth.

| # | File | Classification | Level | Domain | Rationale |
|---|---|---|---|---|---|
| 1 | TechNova_Training_Compliance.pdf | PUBLIC | 0 | Training | Published training/compliance materials with no sensitive internal content. |
| 2 | TechNova_HR_Policy_Handbook.pdf | INTERNAL | 1 | HR | Employment policies applicable to all staff; no individual compensation data. |
| 3 | TechNova_IT_Asset_Policy.pdf | INTERNAL | 1 | IT | Asset handling rules; contains no specific asset serials or endpoint identifiers. |
| 4 | TechNova_Platform_Architecture.pdf | INTERNAL | 1 | Engineering | High-level architecture; excludes credentials and network topology. |
| 5 | TechNova_OnCall_Runbook.pdf | INTERNAL | 1 | Engineering | Runbook steps without secrets; secrets remain in the secret manager. |
| 6 | TechNova_Q4_Financial_Report.pdf | CONFIDENTIAL | 2 | Finance | Pre-public financial performance; material non-public information until filed. |
| 7 | TechNova_Product_Roadmap_2026.pdf | CONFIDENTIAL | 2 | Product | Forward-looking strategy; competitive harm if disclosed. |
| 8 | TechNova_Vendor_Contracts.pdf | CONFIDENTIAL | 2 | Legal | Third-party commercial terms under confidentiality clauses. |
| 9 | TechNova_Salary_Structure.pdf | RESTRICTED | 3 | HR | Individual compensation data; employee privacy + equal-pay legal exposure. |
| 10 | TechNova_Board_Minutes_Q4.pdf | RESTRICTED | 3 | Governance | Director-level deliberations; fiduciary confidentiality. |
| 11 | TechNova_Security_Incident_Report.pdf | RESTRICTED | 3 | Security | Historical incident detail; disclosure would aid repeat attackers. |

Totals: 1 PUBLIC, 4 INTERNAL, 3 CONFIDENTIAL, 3 RESTRICTED.

## 5. Labelling Requirements

**Qdrant payload.** Every chunk carries `security_level` (int) and `security_label` (string). Both fields are payload-indexed for filter efficiency:

```python
store.create_payload_index("security_level", "integer")
store.create_payload_index("doc_slug", "keyword")
store.create_payload_index("domain", "keyword")
```

**Postgres mirror.** When `DATABASE_URL` is set, the `corpus_mirror` table replicates `(chunk_id, doc_slug, doc_name, domain, security_level, security_label, page_number, text)` so that the Documents UI can render without hitting Qdrant. The `security_level` column is `NOT NULL` and constrained to `CHECK (security_level BETWEEN 0 AND 3)`.

**UI surfaces.** Classification badges render on:

- `/documents` — list view, filter chips keyed by `security_label`.
- `/project-b` — chat citations display the classification badge adjacent to the document name.
- `/knowledge-graph` — document nodes are colour-coded by classification.

**Source PDF.** The file-level classification is the `DOCUMENT_METADATA` entry. If a PDF contains mixed classifications (uncommon), the document inherits the highest classification of any contained content.

## 6. Re-Classification Procedure

Classification is not static. Re-classification follows this flow:

1. **Requestor.** Any employee can file a re-classification request via the `trust@technova.example` alias.
2. **Evidence required.** Requestor must supply: document identifier, proposed new classification, rationale, and references supporting the change.
3. **Reviewer.** Document Owner (typically the originating department head) plus Trust & Security reviewer. Board-level documents require CFO or General Counsel concurrence.
4. **Decision SLA.** 10 business days.
5. **Execution.** Reviewer updates `DOCUMENT_METADATA` in `backend/config.py` via pull request. CODEOWNERS requires Trust & Security review on that file. Merge triggers re-ingest (`POST /api/ingest {"force_reingest": true}` in the target environment).
6. **Audit.** Change recorded in the classification register (Roadmap v1.1 — formal register; currently the PR history serves this role).
7. **Cadence.** Annual review of all eleven documents each April; next review 2026-10-16 (bi-annual Trust & Security cycle).

## 7. Deviation / Exception Handling

| Scenario | Action |
|---|---|
| PDF added to `/docs/` without `DOCUMENT_METADATA` entry | Loader skips silently — this is secure-by-default. CI check (Roadmap v1.1) to fail a build when `/docs/*.pdf` count diverges from `len(DOCUMENT_METADATA)`. |
| Classification downgrade | Requires two-person review (dual control). |
| Classification upgrade | Single Document Owner approval sufficient. |
| Temporary suppression from index | Set `DOCUMENT_METADATA[file]["suppressed"] = True` and re-ingest (Roadmap v1.1 flag). |

## 8. Related Documents

- `THREAT_MODEL.md` — threat coverage per classification.
- `DATA_FLOW_DIAGRAM.md` — where classification labels travel.
- `industry-documents/architecture-and-ops/INGEST_PIPELINE.md` — operational detail.
- `industry-documents/access-and-identity/RBAC.md` — role/clearance mapping source of truth.

## 9. Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Trust & Security | Initial release |
