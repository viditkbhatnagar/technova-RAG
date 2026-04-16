# TechNova RAG — Threat Model (STRIDE)

| Field | Value |
|---|---|
| Owner | TechNova Trust & Security |
| Classification | INTERNAL |
| Last Reviewed | 2026-04-16 |
| Next Review | 2026-10-16 |
| Version | 1.0 |

## 1. System Overview and Trust Boundaries

TechNova RAG is a multi-document retrieval augmented generation platform covering eleven fixed internal PDFs stored under `/docs/`. The system exposes three surfaces — Project A (open chat), Project B (role-gated secure chat), and the knowledge graph — over a shared FastAPI backend (`backend/main.py`). Singletons are hydrated into `app.state` during the lifespan context: `embedder`, `store`, `bm25`, `retriever`, `graph_data`, `chat_store`.

The trust boundaries relevant to this model are:

- **TB-1 Browser / Internet → Frontend (Vercel edge):** untrusted user agents terminate at the Next.js 16.2 app hosted on Vercel.
- **TB-2 Frontend → Backend (CORS boundary):** enforced by the CORS middleware in `backend/main.py`; allowed origins are pinned to `http://localhost:3000` and a regex on `https://*.vercel.app`.
- **TB-3 Backend process → Qdrant:** runs over Qdrant's HTTP API (collection `technova_docs`, 768-dim cosine). In dev, native backend to Dockerised Qdrant. In prod, in-cluster Docker Compose network.
- **TB-4 Backend → Neon Postgres:** asyncpg 0.30 TLS connection, only active when `DATABASE_URL` is set. Stores chat messages and corpus mirror.
- **TB-5 Backend → OpenAI:** outbound HTTPS to `api.openai.com` for `gpt-4o-mini` inference; `OPENAI_API_KEY` in env.
- **TB-6 Backend → HuggingFace Hub:** only during cold start, when `BAAI/bge-base-en-v1.5`, `cross-encoder/ms-marco-MiniLM-L-6-v2`, and `en_core_web_sm` are cached to disk. No runtime data exchange.
- **TB-7 Data plane boundary (within backend):** the security pre-filter separating RESTRICTED chunks from the scoring pool. Implemented in `backend/services/security.py`. This is the Project B invariant and is enforced twice: at the Qdrant `search` payload filter and at the BM25 `allowed_chunk_ids` pre-restriction derived from `store.scroll_all`.

## 2. Assets

| Asset | Sensitivity | Location | Custodian |
|---|---|---|---|
| Corpus chunk text (RESTRICTED tier) | Salary_Structure, Board_Minutes_Q4, Security_Incident_Report | Qdrant payload + Postgres mirror + `backend/bm25_index.pkl` | Platform Engineering |
| Corpus chunk text (CONFIDENTIAL tier) | Financial_Report, Product_Roadmap, Vendor_Contracts | Qdrant payload + mirror | Platform Engineering |
| Role → clearance mapping | Trust anchor for Project B | `backend/config.py` (`ROLE_CLEARANCE`) | Platform Engineering |
| Document classification mapping | Source of truth for access control | `backend/config.py` (`DOCUMENT_METADATA`) | Trust & Security |
| Chat history (user prompts + model completions) | May contain restated restricted content for admin users | Neon Postgres `messages` table | Data Platform |
| Embeddings | Non-reversible but leakable signal over proprietary corpus | Qdrant `technova_docs` | Platform Engineering |
| BM25 pickle | Serialized inverted index | `backend/bm25_index.pkl` | Platform Engineering |
| Graph JSON | spaCy NER output with entity labels by document | `backend/graph_data.json` (or in-memory) | Platform Engineering |
| Model artefacts | Downloaded at startup | HuggingFace cache on disk | Platform Engineering |
| Secrets | `OPENAI_API_KEY`, `DATABASE_URL`, Qdrant URL | `.env` (not committed), Vercel env vars | Platform Engineering |

## 3. Threat Actors

- **TA-1 External unauthenticated attacker.** Scans the public backend from the open internet; attempts origin spoofing against CORS; probes `/api/query` for information disclosure.
- **TA-2 Over-broad internal role (malicious employee or compromised session).** Passes `role` in request body (no SSO in v1.0) and attempts to retrieve content above their intended clearance.
- **TA-3 Compromised LLM provider response.** The model returns output that hallucinates restricted material, or is manipulated via indirect prompt injection embedded in PDFs.
- **TA-4 Compromised sub-processor.** Neon, Qdrant Cloud, Vercel, or OpenAI suffers a key/material exposure that propagates into TechNova.
- **TA-5 Insider with repository access.** Can alter `DOCUMENT_METADATA` to downgrade a document's classification without review.

## 4. STRIDE Analysis by Trust Boundary

### TB-2 Frontend → Backend

| Category | Threat | Likelihood | Impact | Residual |
|---|---|---|---|---|
| Spoofing | Attacker forges `Origin` header mimicking `*.vercel.app` preview URL to bypass CORS regex. | Medium | Medium | **Open** — CORS regex `https://.*\.vercel\.app` accepts all Vercel-hosted origins including malicious preview deployments. |
| Tampering | Attacker mutates request body to inject `role: "admin"`. | High | High | **Open — v1.0 gap.** Accepted risk for demo-grade Project B; remediation is SSO + server-side role resolution (Roadmap v1.1). |
| Repudiation | No signed request, no audit trail beyond `messages` table. | Medium | Low | Partial — Postgres `messages` gives weak non-repudiation; no tamper-evident log (Roadmap v1.1). |
| Info Disclosure | Verbose FastAPI error exposes stack trace. | Low | Low | Mitigated by `uvicorn` in non-debug mode; disable `--reload` in prod. |
| Denial of Service | Unbounded request rate overwhelms `gpt-4o-mini` spend. | High | Medium | **Open.** No rate limiting middleware. Roadmap: per-IP sliding window in `backend/main.py`. |
| Elevation of Privilege | Same as Tampering above. | High | High | Open; same remediation. |

### TB-3 Backend → Qdrant

| Category | Threat | Residual |
|---|---|---|
| Spoofing | Rogue Qdrant instance. | Mitigated in Docker by compose network isolation; in prod, Qdrant URL pinned and reachable only in-cluster. |
| Tampering | Direct write to collection bypassing `store.upsert` path. | Mitigated by network isolation; API key for Qdrant Cloud. |
| Info Disclosure | Qdrant HTTP exposed publicly. | **Open** in careless deployments. Documented mitigation: Qdrant bound to loopback / private network only. |
| Elevation of Privilege | If backend connects without API key, a tenant separation attack is possible on shared Qdrant Cloud. | Mitigated: Qdrant API key required in prod. |

### TB-4 Backend → Postgres

| Category | Threat | Residual |
|---|---|---|
| Info Disclosure | Connection string leak. | Mitigated: `DATABASE_URL` held in env only; `.env` gitignored. |
| Tampering | SQL injection via chat content. | Mitigated: asyncpg parameterised statements; no string concatenation in `chat_store`. |
| Repudiation | Chat message written without user id. | Partial — `role` is stored per message, but no user id in v1.0. |

### TB-5 Backend → OpenAI

| Category | Threat | Residual |
|---|---|---|
| Info Disclosure | Prompt contents leave the trust boundary. | Accepted, governed by OpenAI data policy (no training by default). Documented in `industry-documents/legal-and-commercial/SUB_PROCESSORS.md`. |
| Tampering | Compromised upstream returns malicious tokens. | Low likelihood, no tool-use configured, output rendered through `react-markdown` with sanitization. |

### TB-7 Data plane boundary (Project B invariant)

| Category | Threat | Control | Residual |
|---|---|---|---|
| Info Disclosure | RESTRICTED chunk leaks into candidate pool via BM25 path only. | `get_allowed_chunk_ids(role)` in `backend/services/security.py` intersected before BM25 scoring. | Mitigated. |
| Info Disclosure | RESTRICTED chunk leaks via dense path only. | Qdrant payload filter `security_level $lte ROLE_CLEARANCE[role]`. | Mitigated. |
| Info Disclosure | LLM hallucinates restricted content from priors. | Answer is grounded; prompt instructs "answer only from context". Residual risk remains — LLM training data leakage. | Partial. |
| Timing side channel | Access-denied latency differs enough to signal presence of restricted match (`restricted_cosine_threshold=0.55`). | Latency normalisation not implemented. | **Open — documented residual.** |
| Elevation of Privilege | Repository insider downgrades `security_level` in `DOCUMENT_METADATA`. | Code review + protected branch; SBOM-sensitive constants tracked. | Partial — no formal four-eyes enforcement. |

## 5. LLM-Specific Threats

| ID | Threat | OWASP LLM ref | Mitigation | Status |
|---|---|---|---|---|
| L-1 | Direct prompt injection in user query (`ignore previous instructions`). | LLM01 | System prompt anchored; context clearly delimited; no tool use in v1.0. | Mitigated |
| L-2 | Indirect prompt injection via adversarial content embedded in PDF chunks. | LLM01 | Corpus is TechNova-authored; change-control on `docs/` directory; `DOCUMENT_METADATA` gates ingestion (unmapped PDFs silently skipped). | Mitigated for current corpus; would require content sanitization for user-ingested PDFs (Roadmap v1.2). |
| L-3 | Training-data leakage (model regurgitates unrelated proprietary content from pretraining). | LLM06 | Grounded-answer system prompt; gpt-4o-mini; no fine-tuning on TechNova data. | Accepted residual. |
| L-4 | Jailbreak ("DAN"-style) bypasses system prompt. | LLM01 | Context injection dominates the prompt; RESTRICTED chunks never reach the prompt regardless of LLM compliance. Security invariant holds even under total LLM compromise. | Mitigated at architecture level. |
| L-5 | Tool-use exfiltration. | LLM07 | No function calling / tool use enabled. | N/A — by design. |
| L-6 | Output-handling XSS via markdown. | LLM02 | `react-markdown` 10.1.0 sanitizes; no `dangerouslySetInnerHTML`. | Mitigated. |
| L-7 | Model DoS via long prompt. | LLM04 | Chunk assembly capped at top-5 with 500-char chunks; user query unbounded (Roadmap: length limit middleware). | Partial. |
| L-8 | Sensitive info disclosure via model priors invoked by restricted terms. | LLM06 | Access-denied messaging for weak accessible + strong restricted probe (threshold 0.55). Answer grounded on accessible chunks only. | Mitigated. |

## 6. Project B Invariant — Defence and Residual Risk

The controlling invariant: *restricted chunks never enter the scoring pool.* This is enforced in two places, each of which is independently sufficient against the single-path attacker.

1. **Dense pre-filter.** `HybridRetriever.retrieve` calls `store.search(..., query_filter=get_security_filter(role))`. The filter is a Qdrant `Filter(must=[FieldCondition(key="security_level", range=Range(lte=ROLE_CLEARANCE[role]))])` constructed in `backend/services/security.py`. RESTRICTED chunks (security_level=3) are unreachable for employees (clearance=1) or managers (clearance=2).
2. **Lexical pre-filter.** BM25 is scored over the set `allowed_chunk_ids = {c.chunk_id for c in store.scroll_all() if c.security_level <= ROLE_CLEARANCE[role]}`. Only those IDs are indexed into the scoring pass for this request.
3. **Restricted-space probe (informational).** Separately the retriever probes the restricted subspace with the same query to decide whether to emit the access-denied message. The probe result is never placed in the answer context; it only drives the message emission.

Residual risk — **timing side channel.** The extra probe adds measurable latency when `restricted_cosine_threshold=0.55` is exceeded. A sophisticated attacker could infer *existence* (not content) of restricted documents matching a query by measuring response time distributions. Mitigations considered: constant-time padding (Roadmap v1.2), blind probe on every request regardless of top-1 score (considered but rejected for cost).

## 7. Mitigation Matrix

| Threat | Control | Artefact | Status |
|---|---|---|---|
| Role spoofing in request body | Move to SSO + server-side role resolution | `backend/routers/query.py` | Roadmap v1.1 |
| Preview-deployment origin spoof | Tighten CORS regex to specific preview project | `backend/main.py` | Roadmap v1.1 |
| Rate-limit/DoS | Per-IP sliding window | `backend/middleware/ratelimit.py` (to be created) | Roadmap v1.1 |
| Restricted-chunk leakage via BM25 | `allowed_chunk_ids` intersection before scoring | `backend/services/security.py` | Implemented |
| Restricted-chunk leakage via dense | Qdrant payload filter `security_level $lte clearance` | `backend/services/security.py` | Implemented |
| Access-denied messaging without content leak | Restricted probe with cosine threshold 0.55, never surfaced to LLM | `backend/services/security.py::self_correcting_retrieve` | Implemented |
| Prompt injection (direct) | Context-first system prompt, no tools | `backend/services/generator.py` | Implemented |
| Prompt injection (indirect via PDF) | Change-control on `docs/` + `DOCUMENT_METADATA` allowlist | `backend/config.py` | Implemented |
| Output XSS | react-markdown default sanitization | `frontend/lib/components/*` | Implemented |
| Stack-trace disclosure | Disable `--reload` in prod; FastAPI default 500 handler | `Dockerfile` | Implemented |
| Secret leakage | `.env` gitignored; Vercel env vars | `.gitignore` | Implemented |
| Sub-processor compromise | Contractual DPAs, incident notification requirement | `SUB_PROCESSORS.md` | Implemented |
| Timing side-channel on access denied | Latency normalisation | — | Roadmap v1.2 |
| Insider metadata downgrade | Protected branch + code review + audit log | `CODEOWNERS` | Partial |
| No audit-log persistence | Append-only audit table distinct from `messages` | — | Roadmap v1.1 |
| No PII redaction | Pre-ingest redaction pipeline | — | Roadmap v1.2 |

## 8. Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Trust & Security | Initial release |
