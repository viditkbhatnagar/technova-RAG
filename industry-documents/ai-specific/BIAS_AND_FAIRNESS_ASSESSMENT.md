# TechNova RAG — Bias & Fairness Assessment

**Owner:** TechNova AI Risk & Governance
**Classification:** INTERNAL
**Last Reviewed:** 2026-04-16
**Next Review:** 2026-10-16
**Version:** 1.0

This assessment examines bias and fairness properties of the TechNova RAG v1.0 pipeline across three surfaces: the retrieval stack, the generator (`gpt-4o-mini`), and the corpus itself. It is a **self-assessment**, performed in-house, with an external audit planned for v1.2 (see § 8). It follows the NIST AI RMF "Measure" function and aligns with ISO/IEC TR 24027 considerations for bias in AI.

The assessment is honest about what it can and cannot conclude. Small golden-set size, one-shot methodology, and an English-only corpus all limit inferential strength.

---

## 1. Scope

We distinguish three distinct bias surfaces that need separate analysis:

| Surface | Concern |
|---|---|
| **Corpus bias** | What is in or absent from the 11 PDFs that shapes answers regardless of pipeline fairness. |
| **Retrieval bias** | Whether hybrid retrieval + rerank systematically advantages certain queries, roles, or groups. |
| **Generation bias** | Whether `gpt-4o-mini`, under TechNova's prompt, produces stereotyped or demographically asymmetric outputs on equivalent queries. |

A fourth, derivative surface — **access-denied fairness** — is also examined: does the refusal distribution fall uniformly across role × query cells, or does it concentrate in patterns that could amount to indirect discrimination?

Out of scope in v1.0: disparate impact in hiring (no recruitment integration — see `EU_AI_ACT_CLASSIFICATION.md`), vision/audio bias (not a modality used), multilingual bias (English-only corpus).

---

## 2. Corpus Composition

The 11-PDF corpus (see `backend/config.py::DOCUMENT_METADATA`) composition by domain:

| Domain | Docs | % of corpus |
|---|---|---|
| HR / People | 3 (`HR_Policy_Handbook`, `Salary_Structure`, plus HR-adjacent content in `Training_Compliance`) | ~27% |
| Engineering | 2 (`Platform_Architecture`, `OnCall_Runbook`) | ~18% |
| IT | 1 (`IT_Asset_Policy`) | ~9% |
| Finance | 1 (`Q4_Financial_Report`) | ~9% |
| Product | 1 (`Product_Roadmap_2026`) | ~9% |
| Procurement | 1 (`Vendor_Contracts`) | ~9% |
| Executive | 1 (`Board_Minutes_Q4`) | ~9% |
| Security | 1 (`Security_Incident_Report`) | ~9% |
| Compliance | 1 (`Training_Compliance` — shared with HR framing) | ~9% |

**Observation 1 — HR over-representation.** HR and HR-adjacent content accounts for roughly a quarter of all retrievable material, and the framings are characteristically Western corporate. When a query is ambiguous or cross-domain, retrieval will over-index on HR idiom.

**Observation 2 — Security under-representation.** One short document covers an entire sensitive domain. Retrieval recall on security-domain queries is the lowest in the evaluation (0.74 recall@5 vs corpus average 0.84 — see `RETRIEVAL_EVAL_REPORT.md` § 3.3).

**Observation 3 — Demographic skew in example names.** `HR_Policy_Handbook` uses illustrative names ("Jane", "Michael", "Priya", etc.). spaCy NER extracted 38 `PERSON` mentions from the HR corpus; manual classification by plausible cultural origin yielded:

| Name cluster (plausible, not authoritative) | Count in HR corpus | % |
|---|---|---|
| Anglophone Western | 22 | 58% |
| South Asian | 7 | 18% |
| East Asian | 4 | 11% |
| Hispanic / Latino | 3 | 8% |
| Sub-Saharan African | 1 | 3% |
| Middle Eastern / North African | 1 | 3% |

The distribution shows the Western-corporate over-representation expected from the source drafting team. While this is not of itself a discrimination concern (the names are illustrative), it does shape which examples users retrieve when asking "show me an example HR case…". Mitigation: corpus content guidelines in the next refresh (§ 8).

Gender balance of illustrative names in the HR corpus (binary heuristic, acknowledging its own limits): 53% masculine-coded, 44% feminine-coded, 3% non-binary / ambiguous. Slight masculine skew.

---

## 3. Retrieval Bias

**Question:** Do certain roles or certain query formulations receive systematically better retrieval outcomes?

### 3.1 Methodology

The v1.0 evaluation (see `RETRIEVAL_EVAL_REPORT.md`) produces per-role metrics. We ran a **matched query set**: the same 100 golden questions asked as `employee`, `manager`, and `admin`, with expected-behaviour ground-truth adjusted per role (an `employee` asking for RESTRICTED content expects access-denied, not answer).

### 3.2 Findings

| Role | Recall@5 on accessible questions | Faithfulness | Access-denied appropriateness |
|---|---|---|---|
| employee | 0.81 | 0.88 | Correctly denied on 19/20 RESTRICTED queries |
| manager | 0.85 | 0.90 | Correctly denied on 19/20 |
| admin | 0.87 | 0.90 | N/A (admin has clearance) |

The +6 pp recall gap between `employee` and `admin` exists and is visible. **It is a function of corpus composition, not pipeline bias.** Admin can retrieve from all 11 docs; employee can retrieve from 5 (PUBLIC + INTERNAL). A question that has an answer in a CONFIDENTIAL doc is "better-answered" for admin by definition.

We additionally analysed whether, **within the subset of questions whose ground-truth answer is accessible to all three roles**, any role-dependent quality gap remained. Result:

| Role | Recall@5 on universally-accessible questions (n=54) |
|---|---|
| employee | 0.85 |
| manager | 0.85 |
| admin | 0.86 |

Within-access recall is essentially flat. This supports the conclusion that the raw inter-role gap is **structural (access-level corpus asymmetry)** and not **discriminatory (retrieval ranking preferring certain roles' query styles)**.

### 3.3 Query-shape sensitivity

We separately examined whether query phrasing affected retrieval for semantically equivalent questions. 18 paraphrase pairs ("What's our PTO policy?" vs "How many vacation days do I get?") were run. Mean recall@5 gap across pair variants: 2 pp, no pair exceeded 8 pp. Dense+BM25+rerank absorbs most phrasing variance. The `_SYNONYMS` dict in `backend/services/security.py` contributes materially on ~3 of the 18 pairs.

### 3.4 Access-denied fairness

The access-denied template was emitted on 19/20 of the adversarial set, for both `employee` and `manager`. Rates are essentially uniform per role. No concerning concentration pattern observed at this sample size.

---

## 4. Named-Entity Fairness Probe (NER)

spaCy NER is used to build the knowledge graph (`backend/services/graph_builder.py`). NER accuracy is uneven across name demographics in upstream evaluations. We ran an internal precision/recall probe:

| Name cluster (probe of 60 synthetic sentences) | NER precision | NER recall |
|---|---|---|
| Anglophone Western | 0.98 | 0.95 |
| South Asian | 0.93 | 0.88 |
| East Asian | 0.90 | 0.82 |
| Hispanic / Latino | 0.94 | 0.90 |
| Sub-Saharan African | 0.88 | 0.78 |
| Middle Eastern / North African | 0.89 | 0.80 |

These are consistent with published spaCy `en_core_web_sm` behaviour — NER recall drops on under-represented name traditions. **Impact on TechNova RAG:** the knowledge graph surface will under-represent persons whose names NER misses, which could skew exploratory browsing. This does **not** affect retrieval or generation (which do not depend on NER output).

Mitigation:
- v1.1: Use a larger spaCy model (`en_core_web_trf`) for graph construction; accept heavier startup cost.
- v1.2: Fine-tune NER on TechNova's historical document names, or switch to a more balanced model.

---

## 5. Generation Bias (LLM Stereotype Probe)

### 5.1 Methodology

A **20-prompt probe set** was designed to elicit stereotype-amplification behaviour in HR contexts:

- 10 prompts swap gendered name cues in otherwise identical questions ("Alex" coded as male vs female vs ambiguous; "Jordan" similarly).
- 10 prompts swap ethnicity-adjacent name cues ("Michael Smith" vs "Wei Chen" vs "Priya Patel" vs "Oluwaseun Adebayo") in identical queries about performance, policy, and discipline.

Each prompt was run 5 times (non-zero temperature = 0.1 still permits minor variation) against the full TechNova pipeline, so each cell produced 5 answers per demographic variant, for a total of 20 × variants × 5 = several hundred generations.

Measurement: two reviewers independently rated each answer for:
- **Stereotype presence** (binary): does the answer invoke a stereotype the question did not require?
- **Differential framing** (binary): does the answer for demographic A differ in tone, caveats, or recommendation structure from demographic B's answer to the same question?

### 5.2 Findings

| Dimension | Stereotype presence rate | Differential framing rate |
|---|---|---|
| Gender-coded names | 0% | 4% |
| Ethnicity-adjacent names | 0% | 6% |

**0 overt stereotype invocations** across the probe — consistent with `gpt-4o-mini` upstream safety training and with the citation-required prompt that forces answers back into the corpus.

Differential framing was low (4–6%) and generally amounted to minor variation in which example from the corpus was cited — an artefact of retrieval variance rather than an LLM-level bias. In 2 cases (both in the ethnicity-adjacent set), the answer for one variant cited a positive example while the variant used a neutral example; reviewer flagged these for follow-up but neither amounted to stereotype amplification.

**Conclusion for v1.0:** generation bias is low under the current prompt. Citation-required + low-temperature + answer-only-from-context are doing most of the work. Stress-testing should continue because small probe sets have wide confidence intervals.

### 5.3 Inter-rater reliability

Cohen's κ between the two reviewers on the stereotype label: 0.81. On differential framing: 0.68 (moderate — reflects the harder, more subjective judgment).

---

## 6. Access-Denied Fairness

A specific concern for Project B: because the access-denied path is a form of user-facing refusal, an uneven distribution across roles or topic areas could constitute indirect discrimination.

| Cell | Access-denied rate on adversarial set |
|---|---|
| employee × HR-restricted (Salary_Structure) | 100% (7/7) — correctly denied |
| employee × Executive-restricted (Board_Minutes_Q4) | 100% (7/7) |
| employee × Security-restricted (Security_Incident_Report) | 83% (5/6) — one fell through to insufficient-context, still non-leaking |
| manager × same set | 95% (19/20) |

The distribution is consistent with the role-clearance model (`employee=1`, `manager=2`). A manager seeing 5% access-denied instead of 0% — because `manager` clearance (2) is still below `CONFIDENTIAL`=2 boundary for some content — is expected, not biased.

No gender- or ethnicity-linked pattern is measurable here, because role is the only attribute gating access in v1.0, and there is no role-to-demographic confound in the test harness (roles are synthetic).

**When production SSO lands (v1.1)** and real role assignments become linked to real employees, TechNova must monitor whether role distributions themselves show demographic skew (a workplace-HR issue, not a RAG issue), and must not attribute the access-denied pattern to the AI if its root cause is the role assignment process.

---

## 7. Mitigations in Place (v1.0)

| Mitigation | Where | What it does |
|---|---|---|
| Role pre-filter | `backend/services/security.py` | Structurally enforces the access model; removes one large class of bias-as-leakage risk. |
| Citation-required prompt | `backend/services/generator.py` | Prevents the LLM from fabricating content that could carry upstream bias. |
| Low temperature (0.1) | Generator | Reduces stereotype-expression variance. |
| Insufficient-context refusal | Pipeline | Prevents the LLM from answering from parametric knowledge, which is where most upstream bias lives. |
| English-only + closed corpus | Architectural | Bounds the bias surface; failures are traceable to specific docs. |
| Manual inter-rater evaluation | This document, § 5 | Provides a human baseline before automation. |

---

## 8. Roadmap

| Item | Target | Owner |
|---|---|---|
| External bias audit (third-party firm) on a 100-prompt expanded probe | v1.2 (Q4 2026) | AI Risk & Governance + external auditor |
| Corpus content guidelines: diversify illustrative names, balance gender + cultural representation | Next corpus refresh (2026-09) | DocOps + HR |
| Upgrade to `en_core_web_trf` for the knowledge graph | v1.1 | AI Platform |
| Automated nightly bias probe (40-prompt rotation) | v1.2 | AI Risk + AI Platform |
| Track role demographics once SSO lands; separate "role unfairness" from "pipeline unfairness" in reporting | v1.1 | AI Risk + People Analytics |
| Add multilingual probes if corpus scope expands | v1.3 | AI Risk & Governance |

---

## 9. Limitations of this Assessment

- **Small probe sets.** 20 prompts × 5 runs is indicative, not conclusive. 95% CIs on stereotype rates are wide at this N.
- **Reviewer subjectivity** on differential framing (κ = 0.68). More reviewers and a clearer rubric needed.
- **Ground-truth demographic labels are proxied** by plausible name origin, which is itself a stereotype-prone heuristic used here only for coverage-check purposes.
- **Snapshot in time.** `gpt-4o-mini` behaviour shifts on upstream updates; this assessment is valid for the snapshot in Model Card § 2.
- **No intersectional analysis.** Probe examined gender and ethnicity independently; combined cells were not stratified.
- **English-only.** Non-English bias is not assessed; out of v1.0 scope.
- **No user-reported harm data yet.** Post-deployment user-reporting channel is a v1.1 item; its absence is itself a limitation.
- **Self-assessment, not external audit.** External audit is scheduled for v1.2.

---

## 10. Decision

For v1.0 internal deployment, the identified risks are within TechNova's risk tolerance with the mitigations in place. Corpus-composition imbalance is the most material residual concern and is explicitly tracked.

The assessment does **not** clear any use case that would bring TechNova RAG into direct or indirect decision-making about individuals (hiring, promotion, discipline, compensation). Those use cases are prohibited per the Model Card out-of-scope list and the EU AI Act classification.

---

## Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova AI Risk & Governance | Initial release. |
