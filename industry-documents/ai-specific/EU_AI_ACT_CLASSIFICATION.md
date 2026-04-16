# TechNova RAG — EU AI Act Classification

**Owner:** TechNova AI Risk & Governance (with Legal)
**Classification:** INTERNAL
**Last Reviewed:** 2026-04-16
**Next Review:** 2026-10-16
**Version:** 1.0

This document analyses the status of the TechNova RAG system under **Regulation (EU) 2024/1689** ("the EU AI Act"). It establishes the classification, obligations, and compliance posture for v1.0 of the system, and describes how changes in scope would re-open the analysis.

The analysis is internal counsel's working assessment. It is not a legal opinion binding on any EU authority, nor does it substitute for qualified local counsel review at the point of any EU-market deployment.

---

## 1. System Classification

### 1.1 Is it an "AI system" under Art. 3(1)?

Art. 3(1) defines an AI system as a *"machine-based system that is designed to operate with varying levels of autonomy and that may exhibit adaptiveness after deployment, and that, for explicit or implicit objectives, infers, from the input it receives, how to generate outputs such as predictions, content, recommendations, or decisions that can influence physical or virtual environments."*

**TechNova RAG meets this definition.** The pipeline infers retrieval relevance (BGE embedder → reranker) and generates content (gpt-4o-mini), influencing the virtual environment of TechNova's internal knowledge management workflows.

### 1.2 Which role does TechNova play under the Act?

| Role | Applies? | Why |
|---|---|---|
| Provider (Art. 3(3)) | **No** for the underlying models. | TechNova does not develop, train, or fine-tune any component model. BGE, ms-marco-MiniLM, spaCy, and gpt-4o-mini are developed by third parties. |
| Provider of the composed system | **Partially — yes internally.** | TechNova "places on the market" the composed system inside TechNova, which is a form of making-available that triggers provider-like obligations. For an external launch, full Art. 16 provider obligations would activate. |
| Deployer (Art. 3(4)) | **Yes.** | TechNova uses the system for internal Q&A. |
| Importer / Distributor | N/A | No EU market distribution in v1.0. |

v1.0 treats TechNova as **Deployer + internal-Provider**. Full external-Provider obligations are deferred until (and unless) the system is offered outside the company.

### 1.3 General-Purpose AI Model (Chapter V)

`gpt-4o-mini` is a general-purpose AI model. Provider obligations under Chapter V (Arts. 53–56) fall on **OpenAI**, not TechNova. As a downstream integrator, TechNova:

- Reads OpenAI's published technical documentation and safety evaluations.
- Records the model identifier and snapshot in the Model Card (`ai-specific/MODEL_CARD.md`).
- Subscribes to OpenAI's deprecation and incident notifications.

No GPAI-with-systemic-risk thresholds apply to the TechNova-developed layer because TechNova does not train any model.

---

## 2. Risk Class Analysis

### 2.1 Prohibited practices (Art. 5)

| Prohibition | TechNova RAG? |
|---|---|
| Subliminal / manipulative techniques | No — transparent Q&A surface. |
| Exploitation of vulnerabilities | No. |
| Social scoring (public authorities) | No. |
| Predictive policing based on profiling | No. |
| Untargeted scraping for facial recognition | No. |
| Emotion recognition in workplace/education | No. |
| Biometric categorisation for sensitive attributes | No. |
| Real-time remote biometric ID in public spaces | No. |

**None of the Art. 5 prohibitions apply.**

### 2.2 High-risk screening (Annex III)

Annex III lists eight high-risk use categories. Screening:

| # | Category | Applies? | Analysis |
|---|---|---|---|
| 1 | Biometric identification / categorisation | No | No biometrics collected or inferred. |
| 2 | Critical infrastructure management | No | Not used to operate transport, water, gas, electricity, or critical digital infrastructure. `OnCall_Runbook` is informational only. |
| 3 | Education / vocational training | No | Not used to determine access or evaluate students. `Training_Compliance` is internal policy, not learner assessment. |
| 4 | **Employment, workers' management, and access to self-employment** | **Potentially** | Detailed analysis below. |
| 5 | Access to essential private / public services | No | Internal employee tool, not a gating mechanism for benefits. |
| 6 | Law enforcement | No. |
| 7 | Migration, asylum, border control | No. |
| 8 | Administration of justice and democratic processes | No. |

The only category requiring analysis is **#4 Employment**.

### 2.3 Annex III #4 (Employment) analysis

Annex III point 4(a)–(b) (as adopted) flags as high-risk any AI intended to be used:
- *4(a): for the recruitment or selection of natural persons… to evaluate candidates*
- *4(b): to make decisions affecting terms of work-related relationships, the promotion or termination, to allocate tasks based on individual behaviour or personal traits or characteristics, or to monitor and evaluate the performance and behaviour of persons in such relationships.*

TechNova RAG is deployed in a workplace and the corpus contains HR and compensation material (`HR_Policy_Handbook`, `Salary_Structure`), so the question is live. The analysis:

| Question | v1.0 answer |
|---|---|
| Does TechNova RAG make decisions about candidates? | No. No recruitment pipeline integration; no candidate data ingested. |
| Does it make decisions about employee promotion, termination, or task allocation? | No. It is **advisory-only**: it returns text answers to information queries. No downstream system executes actions on its output. |
| Does it monitor or evaluate employee performance? | No. No telemetry of employee conduct is ingested; it reads fixed policy, not activity logs. |
| Does it materially influence human decisions about employees? | Indirectly — a manager could read a policy answer before a decision. This is analogous to a manager reading the HR handbook directly; the system does not score, rank, or recommend about the employee. |

### 2.4 Art. 6(3) exception

Art. 6(3) provides that a system which would otherwise fall under Annex III is **not** high-risk where it performs only a *"narrow procedural task"*, or *"improves the result of a previously completed human activity"*, or *"detects decision-making patterns or deviations from prior decision-making patterns and is not meant to replace or influence the previously completed human assessment, without proper human review"*, or *"performs a preparatory task to an assessment relevant for the purposes of the use cases"*.

TechNova RAG v1.0 fits the "preparatory task" and "narrow procedural task" exceptions:

- It **retrieves and summarises pre-existing written policy** — a narrow procedural task.
- It **prepares** information that a human then uses in their own reasoning. It does not substitute for human assessment.
- It does **not profile** the data subject in the Art. 6(3) second paragraph sense. The user asks about policy; the system does not score or classify the user.

### 2.5 Classification conclusion for v1.0

| Outcome | Basis |
|---|---|
| **Not prohibited.** | Art. 5 cleared. |
| **Not high-risk.** | Annex III #4 engaged only superficially; Art. 6(3) narrow-procedural / preparatory exception applies. |
| **Limited-risk with transparency obligations.** | Art. 50 applies (user must know they interact with an AI). |
| **GPAI-component.** | `gpt-4o-mini` obligations rest on OpenAI. TechNova is a downstream integrator with correspondingly light duties. |

---

## 3. Triggers That Would Reclassify

Any of the following future changes would reopen the analysis and likely shift TechNova RAG into **high-risk** under Annex III #4:

1. Direct integration into promotion, termination, or compensation decisions.
2. Automated task-allocation or performance evaluation features.
3. Ingestion of employee behavioural telemetry (not just policy PDFs).
4. Generating recommendations about specific named employees.
5. External deployment where TechNova becomes a Provider in the EU market.
6. Adding tool-use that takes actions in HRIS or other systems of record.

Each of these is explicitly **out-of-scope** in `ai-specific/MODEL_CARD.md` § 4. Project governance requires AI Risk & Governance sign-off on any feature that touches the list above.

---

## 4. Art. 50 Transparency Obligations (Limited-Risk)

Art. 50(1) requires that users of AI systems be informed of that fact, unless obvious from context.

**TechNova implementation:**

| Surface | Implementation |
|---|---|
| Landing page `frontend/app/page.tsx` | Prominent statement that the system is AI, names the LLM provider, and links to this governance package. |
| Project A and B chat headers (`frontend/app/project-a`, `frontend/app/project-b`) | Persistent "AI assistant — verify before critical decisions" banner. |
| Every answer | Citation-required format surfaces the AI-mediated nature (see `HALLUCINATION_AND_CITATION_POLICY.md`). |
| 3D knowledge graph | Caption discloses NER is automated. |

Art. 50(2)–(4) obligations (labelling AI-generated content, marking synthetic media) do not apply because TechNova RAG does not generate images, audio, video, or synthetic media of real persons.

---

## 5. Obligations as Downstream Deployer of a GPAI

OpenAI, as the GPAI provider, carries Chapter V obligations (technical documentation, summary of training data, copyright-compliance policy, etc.). TechNova's downstream duties as a **deployer**:

| Duty | Art. | TechNova implementation |
|---|---|---|
| Use according to instructions | Art. 26 | Model Card § 3 intended use; out-of-scope list § 4. |
| Ensure human oversight | Art. 26(2) | Every answer is advisory; citations let humans verify; no action is taken on LLM output. |
| Keep logs | Art. 26(6) | Chat history in Neon Postgres (when enabled); audit trail in Qdrant + BM25 for retrieval steps. |
| Inform workers where used in work context | Art. 26(7) | Internal comms to HR and engineering in Q2 2026 before production rollout. This doc is circulated to Works Council-equivalent (TechNova has no formal works council in current geographies; consultation is voluntary). |
| Inform data subjects of high-risk use | Art. 26(11) | N/A — not high-risk. |
| Conduct fundamental-rights impact assessment (FRIA) | Art. 27 (public-sector / high-risk only) | N/A — not required; a lightweight equivalent is done under this governance package (`BIAS_AND_FAIRNESS_ASSESSMENT.md`). |

---

## 6. Technical Documentation (Art. 11 Equivalent)

Art. 11 obligates providers of high-risk systems to maintain technical documentation per Annex IV. **TechNova RAG v1.0 is not high-risk**, so Art. 11 is not strictly required. TechNova nonetheless maintains a functional equivalent to reduce future migration cost if scope changes:

| Annex IV item | TechNova artefact |
|---|---|
| General description of the system | `MASTER_CONTEXT.md`, `ai-specific/MODEL_CARD.md` |
| Elements and development process | `CONVENTIONS.md`, `CLAUDE.md`, backend/frontend READMEs |
| Monitoring, functioning, and control | `architecture-and-ops/SLO_AND_OBSERVABILITY.md` (if present; else roadmap) |
| Appropriateness of performance metrics | `ai-specific/RETRIEVAL_EVAL_REPORT.md` |
| Risk management system | This document + `ai-specific/BIAS_AND_FAIRNESS_ASSESSMENT.md` + `ai-specific/PROMPT_INJECTION_REDTEAM.md` |
| Changes made through its lifecycle | Git history; Revision History table in each governance doc |
| Standards applied | See § 8 below |
| EU declaration of conformity | Deferred — required only if high-risk classification triggers |
| Post-market monitoring plan | § 7 below |

---

## 7. Post-Market Monitoring (Art. 72 Equivalent)

Even outside high-risk, TechNova maintains a post-deployment monitoring plan:

| Signal | Source | Review cadence | Owner |
|---|---|---|---|
| Retrieval recall@5 regression | v1.1 nightly eval harness | Weekly | AI Platform |
| Cross-role leakage events | Query logs + citation audit | Weekly | AI Risk & Governance |
| Unknown-citation rate | Frontend log | Weekly | AI Platform |
| Refusal rate (insufficient-context) | Backend metrics | Monthly | AI Risk & Governance |
| Access-denied rate per role | Backend metrics | Monthly | AI Risk & Governance |
| User-reported issues | Internal form | On arrival | AI Risk & Governance |
| Upstream model deprecation notices | Vendor RSS / OpenAI status | On arrival | AI Platform |
| Incident triage | Security team | On arrival | Security |

Incidents that would be **reportable under Art. 73** if the system were high-risk are logged here for TechNova-internal incident review even though no EU filing obligation is triggered.

---

## 8. Standards Considered

| Standard | Relevance | Status |
|---|---|---|
| ISO/IEC 42001:2023 — AI Management Systems | Organisational AI management | TechNova AI Risk is evaluating certification for 2027. |
| ISO/IEC 23894:2023 — AI risk management | Reference for this analysis. | Applied informally. |
| ISO/IEC TR 24028 — AI trustworthiness | Informs terminology. | Applied informally. |
| NIST AI RMF 1.0 | Map / Measure / Manage / Govern. | Applied across this governance package. |
| CEN-CENELEC JTC 21 harmonised standards | Will operationalise EU AI Act conformity once published. | Monitoring. |

---

## 9. Compliance Timeline

EU AI Act phased application, and TechNova's corresponding milestones:

| Date | Regulation | TechNova action |
|---|---|---|
| 2 Feb 2025 | Art. 5 prohibitions apply | Confirmed none apply (see § 2.1). Review logged. |
| 2 Aug 2025 | GPAI obligations apply (Chapter V) | Confirmed OpenAI is the GPAI provider; Chapter V duties are OpenAI's. TechNova records model version in Model Card. |
| 2 Aug 2026 | High-risk obligations apply (Annex III) | **TechNova RAG v1.0 not in scope.** Re-run classification if scope expands (see § 3). |
| 2 Aug 2027 | High-risk systems under Annex I (product safety) apply | N/A. |

Monitoring cadence: this document is reviewed at least every 6 months and within 30 days of any material scope change.

---

## 10. Summary for Reviewers

| Question | Short answer |
|---|---|
| Is TechNova RAG an AI system? | Yes (Art. 3(1)). |
| Is it prohibited? | No. |
| Is it high-risk? | No — Art. 6(3) preparatory / narrow-procedural exception applies. |
| Does Art. 50 apply? | Yes — transparency obligations met. |
| Who carries GPAI obligations? | OpenAI for `gpt-4o-mini`. |
| Is TechNova a provider or deployer? | Deployer for v1.0; internal-provider; not an EU-market provider. |
| Would automated HR decision features change this? | Yes — high-risk reclassification likely. Controlled by feature-gate requirement in governance. |
| Is there technical documentation? | Yes — this governance package acts as equivalent. |

---

## Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova AI Risk & Governance | Initial release. |
