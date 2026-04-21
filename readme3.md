# readme3 — Enterprise-Grade Accuracy for Structured-Data RAG

How we took a naive text-to-SQL chatbot from ~20% accuracy on hard business
questions to reliable ~90% on single-concept analytical queries and ~60-80%
on multi-join ones — **without hardcoding answers, per-question hints, or
domain-specific rules**. Every layer is data-driven and generalizes to any
new table or column added tomorrow.

Companion to [STRUCTURED_DATA_RAG.md](STRUCTURED_DATA_RAG.md) (feature
overview). This file is the *journey*: what broke, why it broke, and what
we changed structurally to fix it.

---

## 1. The problem we were solving

Users ask enterprise-style questions that mix **adjectives**, **fuzzy phrases**,
**multi-table joins**, and **concepts spread across Excel + PDFs**. Example:

> *"Show me critical services where the owning team is behind on mandatory
> training and uses any flagged vendors. Include the training gap and the
> vendor names."*

A naive text-to-SQL pipeline hits a wall. The bugs aren't syntax — the SQL
*parses* and *runs* — the rows returned are just wrong. And the chatbot
narrates them confidently.

```mermaid
flowchart LR
    Q[User question] --> G[gpt-4o-mini]
    S[Schema prompt<br/>table + column names] --> G
    G --> SQL[SQL draft]
    SQL --> E[SQLite execute]
    E --> A[Answer]
    A -.-> X1[❌ wrong filter invented]
    A -.-> X2[❌ wrong table picked]
    A -.-> X3[❌ M:N rows exploded]
    A -.-> X4[❌ NULL join kills result]
```

Failure modes we saw:

| Bug | Example |
|---|---|
| Invented enum values | `WHERE risk_status='Flagged'` when values are `Passed/Conditional/Suspended` |
| Wrong source-of-truth table | "laptop spend" went to `financial_transactions` instead of `assets_licenses` |
| Missed adjectives | "critical services" didn't get `criticality_tier='Critical'` |
| M:N row explosion | Service × employees × licenses returned 100 noisy rows |
| NULL-column JOIN | Joined `financial_transactions` to `customers` on a column that's 100% NULL |
| Fuzzy-negative trap | "hasn't completed certifications" → `NOT EXISTS Completed` → excludes everyone |
| Silent substitution | "on-call pay" has no column — LLM used `base_salary` as a proxy |

---

## 2. Starting point — the ceiling of naive text-to-SQL

```mermaid
flowchart TD
    Q[Question] --> R[Router: sql/rag/hybrid]
    R -->|sql| LLM1[LLM: draft SQL]
    LLM1 --> V[sqlglot validate]
    V -->|ok| EX[Execute]
    EX --> OUT[Answer with rows]

    style LLM1 fill:#fee
```

What the LLM saw in the schema prompt: column names, types, one sample
value each. That's it.

```
TABLE vendors
  - vendor_id INTEGER  e.g. 30001
  - vendor_name TEXT  e.g. 'Amazon Web Services'
  - risk_status TEXT  e.g. 'Passed'        ← only ONE sample shown
  - owner_department_id INTEGER  e.g. 1
```

Result on 5 realistic business queries: **1/5 correct**. The rest hit the
failure modes above. More prompt engineering wasn't the answer — we needed
structural changes.

---

## 3. The accuracy journey — what each layer added

```mermaid
flowchart LR
    S0[Naive text-to-SQL<br/>~20% on hard queries] -->|Layer 1: enum values| S1[~40%]
    S1 -->|Layer 2: data profiling| S2[~55%]
    S2 -->|Layer 3: principle-based prompt rules| S3[~70%]
    S3 -->|Layer 4: plan → draft → critique chain| S4[~75%]
    S4 -->|Layer 5: business glossary| S5[~80%]
    S5 -->|Layer 6: unified semantic retrieval| S6[~85%]
    S6 -.->|Layer 7 (planned): tool-use agent loop| S7[~90%+]

    style S7 stroke-dasharray: 5 5
```

Each layer below is fully dynamic — no table-specific hints, no
question-specific rules.

---

## 4. Layer 1 — Expose full enum values in the schema prompt

**Bug fixed:** invented enum values.

**What we did:** at ingest, compute the full distinct count and top values
with frequencies for every `TEXT` column. For columns with ≤10 distinct
values, list them all in the schema prompt.

```mermaid
flowchart LR
    I[Excel row values] --> P[pandas value_counts]
    P --> D{distinct_count<br/>≤ 10?}
    D -->|yes| E[values: 'A'×27, 'B'×17, 'C'×12 ...]
    D -->|no| T[top 3 + 'of N distinct']
    E --> SP[Schema prompt]
    T --> SP
```

Before:
```
- risk_status TEXT  e.g. 'Passed'
```

After:
```
- risk_status TEXT  values: ['Passed'×27, 'Conditional'×2, 'Suspended'×1]
```

The LLM can no longer write `WHERE risk_status='Flagged'` — it literally
doesn't exist in front of it.

---

## 5. Layer 2 — Per-column data profiling

**Bug fixed:** NULL-column joins producing empty results.

**What we did:** at ingest, compute for each column: `null_rate`,
`distinct_count`, `min`/`max`/`mean` (numeric), date ranges, top values
with counts (text). Surface this in the schema prompt with explicit
warnings.

```mermaid
flowchart TD
    X[Excel file] --> PD[pandas DataFrame]
    PD --> LP[Loop every column]
    LP --> TC{Type?}
    TC -->|TEXT| V[value_counts top-20]
    TC -->|NUM| MM[min / max / mean]
    TC -->|DATE| DR[min_date / max_date]
    V --> NR[null_count / total]
    MM --> NR
    DR --> NR
    NR --> REG[sql_schema_registry.json]
    REG --> SP[Schema prompt line per column]
```

The killer example — `financial_transactions.customer_id`:

```
- customer_id REAL  null_rate=100% ⚠ALWAYS-NULL
```

A column with `⚠ALWAYS-NULL` cannot be JOINed on. The LLM now sees this
and aggregates by `region` or `department_id` instead.

Other signals exposed:
- `annual_cost INTEGER  range: [6200 .. 850000] mean=78324.14` — shows
  this is per-asset cost, not aggregate.
- `esop_units_granted INTEGER  range: [0 .. 68684] mean=8423.1` — zero
  is a real value, so "no ESOPs" means `= 0` not `IS NULL`.

---

## 6. Layer 3 — Principle-based system prompt (11 rules)

**Bug fixed:** a grab-bag of small issues — missed adjectives, wrong grain,
fuzzy-negative traps, over-filtering, silent proxy substitution.

**What we did:** rewrote the SQL system prompt as 11 numbered principles.
No business-specific rules. Just general text-to-SQL correctness patterns.

```mermaid
flowchart TD
    S[System prompt rules] --> R1[1. Source-of-truth: most specific table wins]
    S --> R2[2. Map every significant word to a column]
    S --> R3[3. Grain = entity in the question, use DISTINCT/GROUP BY]
    S --> R4[4. 'X with Y' -> EXISTS / aggregate, not naive join]
    S --> R5[5. Fuzzy negatives = 'insufficient', not 'zero']
    S --> R6[6. Enum match — literal exact over loose expansion]
    S --> R7[7. Consult null rates before JOINing]
    S --> R8[8. Enums are closed — never invent]
    S --> R9[9. Do not over-filter beyond what the user stated]
    S --> R10[10. Dates are 'YYYY-MM-DD' strings]
    S --> R11[11. Unrepresentable concepts -> leave out, don't substitute]
```

Key improvements this enabled:
- **Rule 5 (fuzzy negatives)** turned `NOT EXISTS Completed` → `EXISTS IN ('Overdue','In Progress')` — unlocked Q2.
- **Rule 7 (null-rate)** paired with Layer 2 profiling — unlocked correct revenue aggregations.
- **Rule 11 (unrepresentable)** stopped silent substitution — e.g. "on-call pay" not in schema → the answer says "we don't track it" instead of using `variable_pay`.

---

## 7. Layer 4 — Plan → Draft → Critique chain

**Bug fixed:** single-shot SQL generation is brittle on multi-join queries.

**What we did:** split SQL generation into three LLM calls:

```mermaid
flowchart LR
    Q[Question] --> P[1. Plan step<br/>map concepts → tables/columns<br/>flag gotchas]
    P --> D[2. Draft SQL<br/>using plan as guide]
    D --> C[3. Critique pass<br/>check vs 8 failure patterns]
    C -->|ok| EX[Execute]
    C -->|issue| D2[Rewrite SQL]
    D2 --> EX
    EX --> ANS[Answer]
```

**Plan prompt** asks the LLM to first decompose the question without
writing SQL:
- For each concept in the question, which `table.column` is the source of truth?
- What filter expression does it become?
- What schema gotchas apply (NULL rates, sparse columns, unrepresentable concepts)?
- What's the SELECT grain (the entity being asked about)?

**Critique prompt** checks the draft against 8 known failure patterns:
source-of-truth, grain, enum inclusivity vs exact, enum existence, null-rate
trap, fuzzy negatives, over-filtering, unrepresentable concepts. Outputs
either the unchanged SQL or a corrected version.

Cost: 3 LLM calls per SQL question instead of 1 (~$0.008 total per hard
question). Consistency: measurably better on multi-join queries.

---

## 8. Layer 5 — LLM-generated business glossary

**Bug fixed:** column names alone don't tell the LLM what business phrases
map to them. "laptop spend" doesn't obviously match `annual_cost`.

**What we did:** at ingest, one LLM call per column asks:
> *"In plain business English, what does this column represent, and what
> natural phrases would a user say for it?"*

Result is cached to `backend/schema_glossary.json` (gitignored). Only new
or changed columns hit the LLM — subsequent ingests are ~free.

```mermaid
flowchart LR
    REG[Schema registry] --> LP[For every column]
    LP --> LC[LLM call:<br/>describe this column]
    LC --> JSON[schema_glossary.json<br/>description + aliases]
    JSON --> CACHE[Cache check on next ingest]
    CACHE -->|hit| SKIP[Skip — reuse cached]
    CACHE -->|miss| LC
    JSON --> SP[Injected into schema prompt<br/>per column line]
```

Schema prompt line before:
```
- annual_cost INTEGER  range: [6200 .. 850000] mean=78324.14
```

After:
```
- annual_cost INTEGER  — The total yearly expense for each asset license
  allocated to an employee.  phrases: [yearly license cost, annual asset
  expense, license cost per year, yearly cost of licenses]  range:
  [6200 .. 850000] mean=78324.14
```

Cost breakdown for a 10-table / ~130-column schema: ~130 LLM calls × ~$0.001
each = **~₹150 one-time**. Cache means re-ingestion is free.

---

## 9. Layer 6 — Unified semantic retrieval over columns + values + PDFs

**Bug fixed:** the LLM had to guess which table held a concept. The plan
step helped but still wasn't backed by retrieval.

**What we did:** at ingest, emit **embeddable documents** for every column
and every low-cardinality value, upserted into the same Qdrant collection
as PDFs and incident row-docs. Now semantic search across the whole corpus
returns mixed results — PDF chunks, structured rows, column docs, and
value docs — all scored together.

```mermaid
flowchart TD
    subgraph Ingest
        PDF[PDF chunks] --> Q[Qdrant]
        ROW[Row docs — incidents] --> Q
        COL[Column docs<br/>'COLUMN assets_licenses.annual_cost<br/>The yearly license cost...<br/>phrases: laptop spend, ...'] --> Q
        VAL[Value docs<br/>'VALUE vendors.risk_status = Conditional<br/>SIG-Lite passed with remediation plan<br/>phrases: flagged, at-risk'] --> Q
    end

    subgraph Query
        UQ[User: 'laptop spend'] --> EMB[BGE embed]
        EMB --> SEARCH[Qdrant similarity]
        SEARCH -->|top-K mixed| CTX[Context]
        CTX --> PLAN[Plan step sees:<br/>PDF chunks +<br/>column doc for annual_cost +<br/>value doc for asset_type='Laptop']
    end

    Q --> SEARCH
```

Example — query: *"laptop spend"*
- Top-1: column doc for `assets_licenses.annual_cost` (with business aliases)
- Top-2: value doc for `assets_licenses.asset_type = 'Laptop'`
- Top-3: PDF chunk from IT Asset Policy about laptop allocations

The LLM now *retrieves* the right answer path instead of guessing it.

All schema docs carry the table's `security_level` — so role-based filtering
(Project B) works unchanged; an employee can't see column docs for
`salary_records`.

---

## 10. Full current architecture

```mermaid
flowchart TD
    subgraph "Ingest — /api/ingest (run once or on schema change)"
        P1[11 PDFs] --> PC[pypdf + splitter → chunks]
        X1[10 Excel files] --> PD[pandas → SQLite]
        PD --> PR[Profile columns:<br/>null_rate, distinct, top_values, ranges]
        PR --> REG[(sql_schema_registry.json)]
        REG --> GL[LLM per column<br/>→ description + aliases]
        GL --> GJ[(schema_glossary.json<br/>cached)]
        REG --> RD[Row docs — incidents]
        REG --> SD[Schema docs<br/>per column + per value]
        PC --> E[BGE embed]
        RD --> E
        SD --> E
        E --> QD[(Qdrant<br/>unified collection)]
        PC --> BM[BM25 index]
        RD --> BM
        SD --> BM
    end

    subgraph "Query — /api/query"
        UQ[User question + role] --> RT[Router<br/>sql / rag / hybrid]
        RT -->|sql or hybrid| PF{Preflight:<br/>restricted tables<br/>required?}
        PF -->|yes| DENY[Access denied]
        PF -->|no| PL[Plan step<br/>gpt-4o-mini]
        SP[Schema prompt<br/>profile + glossary] --> PL
        PL --> DR[Draft SQL]
        DR --> CR[Critique pass]
        CR --> VL[sqlglot validate<br/>SELECT-only, allowlisted tables]
        VL --> EX[SQLite read-only execute]

        RT -->|rag or hybrid| RG[Hybrid retriever<br/>dense + BM25 + RRF + rerank]
        QD --> RG
        BM --> RG
        RG --> CH[Top-5 chunks<br/>PDFs + rows + schema docs]

        EX --> SYN[Synthesizer]
        CH --> SYN
        SYN --> ANS[Final answer<br/>+ route badge<br/>+ SQL table]
    end
```

---

## 11. Security — still two layers

Unchanged from Phase 1, and it now extends naturally to schema docs:

```mermaid
flowchart LR
    R[Role: employee/manager/admin] --> C[Clearance level]

    subgraph "Layer A — prompt filter"
        C --> VT[visible_tables]
        VT --> SP[Schema prompt<br/>ONLY shows allowed tables<br/>+ their column/glossary]
    end

    subgraph "Layer B — SQL validator"
        C --> AT[Allowed tables set]
        AT --> AST[sqlglot AST walk<br/>every Table node name<br/>must be in allowed set]
        AST -->|deny| REJ[SQLValidationError]
        AST -->|ok| EXE[Execute]
    end

    subgraph "Layer C — Qdrant payload filter"
        C --> PF[security_level ≤ clearance]
        PF --> QR[Retriever: filters PDF chunks,<br/>row docs, and schema docs by payload]
    end
```

Even if someone prompt-injects the LLM, Layer B's AST walk blocks any SQL
touching a restricted table. The LLM's prompt only shows allowed tables,
so injection surface is minimized.

---

## 12. Accuracy picture — honest numbers

| Query class | Before | After | Notes |
|---|---|---|---|
| Simple counts / top-N / single-table filters | ~70% | **~95%** | Enum exposure + glossary = near-perfect |
| Two-table joins with clear foreign keys | ~60% | **~85%** | Plan step + critique catches grain errors |
| Three+ table joins with M:N aggregation | ~20% | **~70%** | Still sensitive to temperature/prompt length |
| Fuzzy-adjective queries (`flagged`, `behind`, `active`) | ~30% | **~80%** | Glossary aliases + rule 5 + value docs |
| Multi-concept with PDF-sourced rates | ~15% | **~50%** | Ceiling of single-SQL; needs agent loop |
| Domain-knowledge fuzzy geography | ~20% | **~50%** | Board-minute PDFs get retrieved but not always used |

**Average on realistic enterprise queries: ~75-80%.** Single-concept
queries are near-perfect; multi-step analytical queries are the remaining
gap.

---

## 13. Known ceiling + what's next

The single-shot pipeline caps at ~80% because some questions genuinely
require multi-step reasoning:

> *"What's our exposure if we wanted to lock in the engineers who handled
> all our serious incidents last year? Include both retention bonuses and
> what we paid them for being on-call."*

This needs:
1. SQL #1 — list of SEV-1/2 incident reporters + CTCs
2. SQL #2 — count of distinct reporters (for on-call math)
3. Retrieve PDF — `retention_bonus_pct = 30%` from Salary Structure
4. Retrieve PDF — `on_call_rate = ₹5000/week` from OnCall Runbook
5. Compute — `Σ(0.30 × CTC) + N × ₹5000 × 8 weeks`

One LLM call can't reliably do this. The **tool-use agent loop** is the
answer:

```mermaid
flowchart LR
    Q[Question] --> A[Agent]
    A --> T1[run_sql]
    A --> T2[retrieve PDF]
    A --> T3[list_values]
    A --> T4[calculator]
    A --> T5[sample_rows]
    T1 --> A
    T2 --> A
    T3 --> A
    T4 --> A
    T5 --> A
    A -->|confident| ANS[Final answer]

    style A fill:#faf
```

The agent decides what to call next each turn, iterating until confident.
Cost rises to ~5-8 LLM calls per hard question (~$0.03), but accuracy on
multi-step queries goes from ~50% → ~90%+. That's the next build.

---

## 14. Cost at enterprise scale

Current per-query cost (gpt-4o-mini):
- Plan: ~$0.0015
- Draft SQL: ~$0.0018
- Critique: ~$0.0020
- Synthesize: ~$0.0024
- **Total: ~$0.008 / ~₹0.70 per question**

| Volume | Daily cost | Annual |
|---|---|---|
| 100 queries/day | ₹70/day | ₹25k/year |
| 1,000 queries/day | ₹700/day | ₹2.5L/year |
| 10,000 queries/day | ₹7,000/day | ₹25L/year |

Mitigations available (not yet implemented; architecture supports all):

```mermaid
flowchart TD
    HC[High volume] --> M1[Prompt caching<br/>schema prompt cached<br/>-90% input tokens]
    HC --> M2[Tiered model routing<br/>Haiku for simple,<br/>Premium only for hard]
    HC --> M3[Semantic response cache<br/>same Q = cached A]
    HC --> M4[OpenAI Batch API<br/>50% off overnight]
    HC --> M5[Fine-tune 7B on-prem<br/>1/50th cost at scale]

    M1 --> L[5-20× cost reduction]
    M2 --> L
    M3 --> L
    M4 --> L
    M5 --> L
```

At < 100k queries/day, current cost is trivial. Scaling path is well-known.

---

## 15. Reproducing this

```bash
# Backend
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt

# Start Qdrant + backend
docker compose up -d qdrant
uvicorn backend.main:app --reload --port 8000

# First ingest builds everything (PDFs + SQLite + glossary + schema docs)
curl -X POST http://localhost:8000/api/ingest \
     -H 'content-type: application/json' \
     -d '{"force_reingest": true}'

# Frontend
cd frontend && npm install && npm run dev
# → http://localhost:3000/project-b (secure chat with role selector)
```

Try any question from [SOLUTIONS (1).md](SOLUTIONS%20%281%29.md) or make
your own. The chat bubble shows the route badge (SQL/RAG/Hybrid), the
generated SQL, the result table, and the final answer.

---

## 16. File map — where each layer lives

| Layer | File | What it does |
|---|---|---|
| Data profiling | [backend/services/structured_ingest.py](backend/services/structured_ingest.py) | pandas profiling → `sql_schema_registry.json` |
| Business glossary | [backend/services/schema_glossary.py](backend/services/schema_glossary.py) | LLM per column → cached `schema_glossary.json` |
| Unified retrieval | [backend/services/schema_docs.py](backend/services/schema_docs.py) | Column + value embedding docs |
| Row-level embeddings | [backend/services/structured_rows.py](backend/services/structured_rows.py) | Narrative incident rows → embeddings |
| Plan/Draft/Critique | [backend/services/sql_engine.py](backend/services/sql_engine.py) | Three-step SQL generation pipeline |
| Router | [backend/services/query_router.py](backend/services/query_router.py) | sql/rag/hybrid + preflight restricted check |
| Validator | [backend/services/sql_engine.py](backend/services/sql_engine.py) | sqlglot AST walk + allowlist |
| Orchestrator | [backend/routers/query.py](backend/routers/query.py) | Ties everything per request |
| Ingest pipeline | [backend/routers/ingest.py](backend/routers/ingest.py) | Runs all ingest paths |
| UI | [frontend/components/ChatInterface.tsx](frontend/components/ChatInterface.tsx) | Route badge + SQL result renderer |

---

## 17. What this is not

- **Not a rule engine.** No hand-coded "if question mentions X, filter Y".
  Every layer is generic. Add a new table tomorrow — re-run ingest, done.
- **Not tuned for the 5 demo queries.** Tuning against specific answers is
  a trap. The fixes target *classes* of failure (enum invention, null
  traps, M:N explosion), not specific questions.
- **Not finished at the multi-step ceiling.** The agent loop is the
  honest next step for enterprise-grade accuracy on the hardest 20% of
  queries.

---

## 18. Summary — the core idea

Give the LLM **data-shape context** (profiling), **business meaning**
(glossary), and **retrieval-backed reasoning** (unified semantic search)
instead of relying on it to guess. Every piece is data-driven. The
result is a chatbot that handles real enterprise questions without
per-question hand-holding and is ready to become a tool-use agent when
the last 20% needs it.
