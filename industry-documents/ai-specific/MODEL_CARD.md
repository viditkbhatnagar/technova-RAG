# TechNova RAG — System Model Card

**Owner:** TechNova AI Risk & Governance
**Classification:** INTERNAL
**Last Reviewed:** 2026-04-16
**Next Review:** 2026-10-16
**Version:** 1.0

This model card follows the structure proposed in Mitchell et al. (2019), "Model Cards for Model Reporting." It documents the TechNova RAG composed system — the end-to-end retrieval-augmented generation pipeline — rather than any single underlying model. From a user and risk perspective, the pipeline is the unit of analysis: its recall, faithfulness, and access-control behaviour emerge from the interaction of four component models and deterministic retrieval logic, not from any one model in isolation.

---

## 1. System Details

| Field | Value |
|---|---|
| System name | TechNova RAG |
| Version | 1.0 |
| Release date | 2026-04-16 |
| System type | Retrieval-Augmented Generation (composed system) |
| Primary owner | TechNova AI Platform (`ai-platform@technova.internal`) |
| Risk owner | TechNova AI Risk & Governance |
| Primary use surface | Internal web chat (`/project-a`, `/project-b`) + 3D knowledge graph (`/knowledge-graph`) |
| Runtime | FastAPI 0.115 (Python 3.12) backend; Next.js 16 / React 19 frontend |
| Deployment model | Backend: containerised or native (Apple Silicon MPS); Vector store: Qdrant 1.12; Postgres: Neon (managed, optional) |
| Source of truth | Repository `technova-rag`, `main` branch |
| Core pipeline file | `backend/services/retriever.py` (`HybridRetriever.retrieve`) |

The system is a closed-corpus Q&A assistant over 11 internal PDFs located in `docs/`. It is not internet-connected at inference time; the only outbound call per query is to `api.openai.com` for answer generation, and only when `OPENAI_API_KEY` is configured.

---

## 2. Component Models

The pipeline composes four externally-trained models. TechNova does not fine-tune or retrain any component; we accept upstream licenses, weights, and training data as-provided.

| Role | Model | Version | Approx. Params | Context / Dim | License | Source |
|---|---|---|---|---|---|---|
| Dense embedder | `BAAI/bge-base-en-v1.5` | 1.5 | ~110 M | 512 tokens in → 768-dim | MIT | HuggingFace Hub |
| Cross-encoder reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | L-6-v2 | ~22 M | 512 tokens | Apache-2.0 | HuggingFace Hub |
| Generator (LLM) | `gpt-4o-mini` (OpenAI) | 2024-07-18 snapshot | Not disclosed | 128 K input / 16 K output | Proprietary (OpenAI Business Terms) | `api.openai.com` |
| Named entity recogniser | `en_core_web_sm` (spaCy) | 3.8 | ~15 M | Per-sentence | MIT | spaCy model index |

Hybrid retrieval uses `rank_bm25==0.2.2` (pure Python, no model weights). Vector storage is Qdrant 1.12 in a collection named `technova_docs` (768-dim, cosine distance). Models are downloaded once at startup; no runtime traffic reaches HuggingFace Hub.

---

## 3. Intended Use

### 3.1 Primary intended uses

1. **Internal knowledge Q&A** — employees ask natural-language questions about documented TechNova policy, architecture, finances, and runbooks, and receive cited, context-bounded answers.
2. **Role-scoped secure chat (Project B)** — the same pipeline with a mandatory pre-filter enforcing the four-tier security model (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`) against a three-tier role model (`employee`, `manager`, `admin`). Chunks above a user's clearance never enter the scoring pool.
3. **Exploratory corpus navigation** — the 3D knowledge graph (`/knowledge-graph`) exposes entity/document relationships extracted by spaCy NER for investigative browsing, not for answer generation.

### 3.2 Primary intended users

- TechNova employees, managers, and admins, authenticated via the frontend role selector in v1.0 (production auth is a v1.1 roadmap item — see `CLAUDE.md` and Project B gap list).
- Internal AI risk reviewers performing spot audits via the same interface.

### 3.3 Use-case fit rationale

Closed-corpus RAG is well-suited to the 11-PDF scope because: (a) the corpus is small and stable, (b) source attribution is mandatory (see `HALLUCINATION_AND_CITATION_POLICY.md`), and (c) queries are predominantly single-hop look-ups rather than open-ended reasoning. Faithfulness is structurally easier to enforce than in an open-domain system.

---

## 4. Out-of-Scope Use

The system is explicitly **not validated** for — and **must not be used for** — the following:

| Disallowed use | Reason |
|---|---|
| Medical, legal, tax, or financial advice to humans | No licensed expert in the loop; corpus does not cover these domains; general LLM safety disclaimers apply. |
| Automated or semi-automated decisions about employees (hiring, promotion, discipline, compensation) | Would trigger EU AI Act Annex III "employment" high-risk classification. See `EU_AI_ACT_CLASSIFICATION.md`. v1.0 is advisory-only. |
| External customer-facing chat | Corpus contains INTERNAL/CONFIDENTIAL/RESTRICTED material; role model assumes TechNova identity context. |
| Real-time critical-path operational decisions (e.g. live incident remediation execution) | `OnCall_Runbook` is indexed for reference, but the system does not execute actions and has no tool-use surface in v1.0. |
| Ingestion of user-uploaded PDFs | Corpus is fixed in `backend/config.py::DOCUMENT_METADATA`; loader silently skips unmapped files. User upload is a v1.2 feature contingent on re-doing the prompt-injection red team (see `PROMPT_INJECTION_REDTEAM.md`). |
| Training data or distillation source for other models | OpenAI terms prohibit using outputs to train competing models; embedder/reranker licenses do not permit redistribution of TechNova-derived embeddings as a dataset. |

---

## 5. Factors

Factors are the conditions under which system behaviour may vary materially. Evaluation (Section 6) is stratified across these where feasible.

### 5.1 Corpus-domain factors

The 11 PDFs cover eight internal domains, weighted as follows:

| Domain | Docs | Security Level |
|---|---|---|
| HR / People | `HR_Policy_Handbook`, `Salary_Structure` | INTERNAL, RESTRICTED |
| Engineering / Platform | `Platform_Architecture`, `OnCall_Runbook` | INTERNAL |
| IT / Assets | `IT_Asset_Policy` | INTERNAL |
| Finance | `Q4_Financial_Report` | CONFIDENTIAL |
| Product | `Product_Roadmap_2026` | CONFIDENTIAL |
| Procurement | `Vendor_Contracts` | CONFIDENTIAL |
| Executive | `Board_Minutes_Q4` | RESTRICTED |
| Security | `Security_Incident_Report` | RESTRICTED |
| Compliance | `Training_Compliance` | PUBLIC |

Domain coverage is uneven; HR has the broadest representation, Security the narrowest. Retrieval quality in narrow domains (Security, Procurement) has higher variance — see `RETRIEVAL_EVAL_REPORT.md` § 4.

### 5.2 Language

English only. Neither the embedder (`bge-base-en-v1.5`) nor the reranker is multilingual in its primary training; non-English queries will degrade gracefully but are out of scope.

### 5.3 Role distribution

Production expected distribution is approximately 75% `employee`, 20% `manager`, 5% `admin`. Retrieval and generation metrics are reported per-role in § 6 to surface any role-dependent quality gap.

### 5.4 Query-shape factors

Short lookups (≤ 10 tokens), multi-entity questions, and cross-document synthesis questions behave differently. The golden set (see § 7) stratifies across these shapes.

---

## 6. Metrics

Full methodology, rigs, and ablations are documented in `RETRIEVAL_EVAL_REPORT.md`. Headline numbers from the v1.0 evaluation (golden set of 100 graded Q&A pairs + 20 adversarial restricted-content queries) are summarised below.

### 6.1 Retrieval

| Metric | Dense-only | BM25-only | Hybrid + rerank (shipped) |
|---|---|---|---|
| Recall@5 | 0.71 | 0.62 | **0.84** |
| MRR@10 | 0.63 | 0.54 | **0.78** |
| nDCG@10 | 0.69 | 0.60 | **0.82** |

### 6.2 Generation (RAGAS-style)

| Metric | Score |
|---|---|
| Faithfulness (claims supported by cited chunks) | 0.89 |
| Answer relevance | 0.86 |
| Context relevance (precision of top-5) | 0.81 |

### 6.3 Project B access-control

| Metric | Value |
|---|---|
| Access-denied precision (adversarial restricted queries) | 0.95 |
| Access-denied recall | 0.90 |
| Cross-role leakage rate (restricted content surfaced to under-cleared role) | **0.000** |

The leakage rate is structurally enforced by pre-filtering at both the Qdrant dense stage and the BM25 stage (see `backend/services/security.py::get_security_filter` and `get_allowed_chunk_ids`); restricted chunks never enter the scoring pool. The 0.000 value reflects this invariant and is continuously re-verified.

---

## 7. Evaluation Data

- **Golden set**: 100 Q&A pairs stratified across the 11 docs (8–11 per doc), 4 security levels, and 3 query shapes (lookup / multi-entity / cross-doc). Answers are human-authored with chunk-id ground-truth citations.
- **Adversarial set**: 20 questions asked from under-cleared roles that target RESTRICTED content (`Salary_Structure`, `Board_Minutes_Q4`, `Security_Incident_Report`).
- **Bias probe set**: 20 HR-context prompts varying gendered / ethnicity-adjacent name cues (see `BIAS_AND_FAIRNESS_ASSESSMENT.md`).

The sets live in the `RETRIEVAL_EVAL_REPORT.md` appendix and the `eval/` directory (v1.1 roadmap: check into repo with automated nightly runs). v1.0 evaluation was executed manually on 2026-04-10.

---

## 8. Training Data

TechNova RAG is **not trained**. All components arrive pre-trained under their upstream licenses:

| Component | Upstream training data summary |
|---|---|
| `bge-base-en-v1.5` | BAAI mixed English corpus + MS MARCO hard negatives (see model card on HF Hub). |
| `ms-marco-MiniLM-L-6-v2` | MS MARCO passage reranking. |
| `gpt-4o-mini` | OpenAI-disclosed general-web pretraining; specifics not published. |
| `en_core_web_sm` | OntoNotes 5 + web annotations (spaCy documentation). |

TechNova does not contribute user queries, corpus chunks, or generated answers back to any training pipeline. OpenAI API default ("data not used for training") is relied upon; see `PII_AND_SUBPROCESSORS.md` § 3 for the sub-processor stance.

---

## 9. Quantitative Analyses

### 9.1 By role

| Role | Recall@5 | Faithfulness |
|---|---|---|
| employee | 0.81 | 0.88 |
| manager | 0.85 | 0.90 |
| admin | 0.87 | 0.90 |

The +6 pp recall gap between employee and admin is driven by corpus-level asymmetry (admins can retrieve from all 11 docs, employees from 5). This is an artefact of corpus composition, not a discriminatory property of the pipeline. See `BIAS_AND_FAIRNESS_ASSESSMENT.md` § 3.

### 9.2 By security level of target answer

| Target security | Recall@5 | Notes |
|---|---|---|
| PUBLIC | 0.88 | Single doc (`Training_Compliance`) — narrow but clean. |
| INTERNAL | 0.85 | Broadest corpus coverage. |
| CONFIDENTIAL | 0.83 | Three docs; slight drop for cross-doc questions. |
| RESTRICTED | 0.78 | Thin coverage and specialised vocabulary (`Security_Incident_Report`). |

### 9.3 By domain

| Domain | Recall@5 | Dominant failure mode |
|---|---|---|
| HR | 0.87 | Ambiguous entity references ("the manager of X"). |
| Platform | 0.85 | None material. |
| Finance | 0.83 | Numeric lookups competing with narrative text. |
| Security | 0.74 | Small doc, specialised vocabulary. |

---

## 10. Ethical Considerations

1. **Corpus bias toward corporate HR framings.** Three of 11 docs are HR; examples tend to use Western corporate idiom. Retrieval will over-index on these when queries are ambiguous. Mitigation on the roadmap (content guidelines, diversified examples — see `BIAS_AND_FAIRNESS_ASSESSMENT.md`).
2. **Reinforcement of role hierarchy.** By design, Project B presents different answers (including refusal) to different roles on the same question. This is a legitimate access-control property, but it means the system mechanises an existing workplace hierarchy; it must never be used as the sole basis for adverse action against an employee.
3. **Named individuals in the corpus.** `Salary_Structure`, `HR_Policy_Handbook` examples, and `Board_Minutes_Q4` contain real and illustrative names. PII handling is documented in `PII_AND_SUBPROCESSORS.md`.
4. **LLM stereotype risk.** `gpt-4o-mini` inherits upstream biases. Low temperature, citation-required prompting, and the "answer only from context" constraint are the first-line mitigations (see `HALLUCINATION_AND_CITATION_POLICY.md`).
5. **Vendor concentration.** All generation traffic flows through a single provider (OpenAI). A provider outage or policy change could force a pipeline substitution; see `PII_AND_SUBPROCESSORS.md` and the architecture vendor-risk register.

---

## 11. Caveats and Recommendations

- **No automated evaluation harness in v1.0.** Metrics above are the result of a one-shot manual evaluation on 2026-04-10. Drift is undetected between releases. v1.1 roadmap: nightly harness on a 500-query golden set.
- **No PII redaction pipeline.** Query text and retrieved chunks transit to OpenAI verbatim. v1.2 roadmap: Microsoft Presidio pre-LLM redaction with role-appropriate allowlists.
- **No formal red-team archive beyond the v1.0 prompt-injection pass.** See `PROMPT_INJECTION_REDTEAM.md`. Multi-party adversarial testing is a v1.1 item.
- **No external bias audit.** v1.0 self-assessment only; v1.2 engages an external auditor.
- **Apple Silicon MPS divergence.** Native backend uses MPS; Docker backend uses CPU. Embeddings are deterministic to 3 decimal places across both; no material retrieval quality difference observed, but this is not formally regression-tested.
- **Deprecation surface.** `gpt-4o-mini`, `bge-base-en-v1.5`, and `ms-marco-MiniLM-L-6-v2` are all subject to upstream deprecation. The pipeline's `HybridRetriever` interface isolates substitutions, but re-evaluation against the golden set is required before a swap is shipped.

**Recommended use posture**: TechNova RAG is a production-grade internal assistant for documented corporate knowledge, with strong structural guarantees on access control and citation. It is not an authoritative source on personal, medical, legal, or decision-making matters about individuals; verify all critical decisions against source documents.

---

## Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova AI Risk & Governance | Initial release. |
