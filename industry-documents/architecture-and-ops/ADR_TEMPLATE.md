# TechNova RAG — Architecture Decision Record Template

**Owner:** TechNova Platform Engineering
**Classification:** INTERNAL
**Last Reviewed:** 2026-04-16
**Next Review:** 2026-10-16
**Version:** 1.0

---

## How to use this template

TechNova RAG uses Architecture Decision Records (ADRs) in the style of Michael Nygard ("Documenting Architecture Decisions", 2011) to capture significant technical decisions together with the forces that drove them. ADRs are the durable memory of "why we did it this way" — they outlive the authors and they are the first reference for anyone considering a change.

### When to write an ADR

Write an ADR when a decision:

- Changes the shape of the system (a new module boundary, a new external dependency, a replacement of an existing one).
- Makes a trade-off visible to future contributors (cost/latency/flexibility).
- Is likely to be questioned later ("why didn't we use X?").
- Affects cross-team contracts (API shape, data schema, security model).

You do not need an ADR for small, reversible implementation choices (choice of library for JSON parsing, naming of an internal helper). Use code comments and PR descriptions for those.

### One decision, one ADR

Each ADR captures exactly one decision. If a PR touches three decisions, it produces three ADRs. This is not overhead — it is how the document becomes searchable and citable.

### Never edit a past ADR — supersede it

ADRs are append-only. If a decision changes, write a new ADR that references the old one in its Context section and set the old ADR's status to `Superseded by ADR_NNNN`. The old ADR is not deleted; it is the record of what we used to believe and why we changed our minds.

Minor edits are allowed for: typos, broken links, clarification that does not change the substance. Add a row to the ADR's own revision history for any such change.

### Filename convention

`ADR_{NNNN}_{short_slug}.md` where `NNNN` is a zero-padded four-digit sequence number and `short_slug` is lowercase underscored. Examples:

- `ADR_0001_hybrid_retrieval_with_rrf.md`
- `ADR_0002_bge_base_embeddings.md`
- `ADR_0007_qdrant_over_pgvector.md`

Numbers are never reused. If an ADR is withdrawn before acceptance, its number is burned.

### Status lifecycle

```
Proposed → Accepted → (Deprecated | Superseded by ADR_NNNN)
```

- **Proposed**: drafted in a PR; open for comment.
- **Accepted**: merged and in force.
- **Deprecated**: the decision is no longer recommended but not yet replaced.
- **Superseded by ADR_NNNN**: replaced by a newer decision; pointer required.

---

## Template

Copy everything between the fences below into the new ADR file and fill in each section. Keep sections even if they are short — writing "n/a" is more informative than omitting the section.

````markdown
# ADR_NNNN — <short title>

**Status:** Proposed | Accepted <date> | Deprecated | Superseded by ADR_MMMM

**Deciders:** <names or roles>

**Date:** YYYY-MM-DD

---

## Context

<What is the forcing function? What constraint, failure, or opportunity led to this decision? Include:
- the observable problem
- the constraints that bound the solution (regulatory, latency, cost, skills)
- the state of the system when the decision was made
- links to tickets, prior art, and relevant code
>

## Decision

<What did we decide to do? One sentence, then the supporting detail.
Be specific: name the library, the algorithm, the parameter values. This section is the artifact future readers cite.>

## Consequences

### Positive

- <What gets better>
- <What new capability is unlocked>

### Negative

- <What gets worse>
- <What debt is taken on>

### Neutral

- <What shifts without getting better or worse>
- <What new ongoing work is implied>

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| <option A> | <brief reason> |
| <option B> | <brief reason> |
| <option C> | <brief reason> |

## References

- <link to PR>
- <link to design doc>
- <link to external paper or documentation>
- <link to superseded ADR, if any>

## Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | YYYY-MM-DD | <author> | Initial |
````

---

## Sample filled-in ADR

The stub below shows the structural shape of a well-formed ADR. It is illustrative only — for the first real ADR, see `ADR_0001_hybrid_retrieval_with_rrf.md` in this directory.

````markdown
# ADR_0099 — Example: Cache OpenAI responses for identical queries

**Status:** Proposed

**Deciders:** SRE on-call, Platform Engineering Lead

**Date:** 2026-05-01

---

## Context

Observability shows that ~8% of `/api/query` requests in production are exact-duplicate queries within a 24h window (same text, same role). Each duplicate incurs full OpenAI cost (~$0.000405) and full generation latency (~640 ms p50). Internal compliance has confirmed that caching is acceptable provided the cache is scoped per-role and respects access-denied invariants.

Forcing function: Q3 cost review flagged the OpenAI line as 55% of Medium-tier spend; duplicate query cost alone is ~4% of total spend.

## Decision

Introduce a read-through cache for LLM responses keyed on `(sha256(query_text), role, corpus_version)`. Storage backend is Redis 7 with a 24h TTL. Cache is populated in `backend/services/generator.py` after a successful OpenAI response. Cache is invalidated on corpus re-ingest via corpus_version bump.

## Consequences

### Positive

- Saves ~4% of OpenAI spend at Medium tier; ~$16/month.
- Reduces end-to-end latency for duplicates from ~1.4s to ~50ms.
- Makes load-test behavior more predictable.

### Negative

- Adds Redis as a new operational dependency.
- Cache staleness risk if corpus_version bump is missed during ingest.
- Adds per-query key hashing (negligible CPU).

### Neutral

- Access-denied results are also cached; this is correct behavior.
- Telemetry must distinguish cache-hit from cache-miss latency.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Cache at Vercel edge | Can't key on role without leaking role to client. |
| OpenAI native prompt caching | Covers the static prefix, not the full response; useful but complementary, not a replacement. |
| No cache | Leaves ~4% of spend on the table. |

## References

- Ticket TR-412
- `backend/services/generator.py`
- OpenAI prompt caching docs (https://platform.openai.com/docs/guides/prompt-caching)

## Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-05-01 | J. Smith | Initial proposal |
````

---

## ADR index maintenance

The list of accepted ADRs is maintained in this directory. When proposing a new ADR:

1. Pick the next available sequence number (run `ls ADR_*.md | sort` and add one).
2. Create the file.
3. Link it from `HIGH_LEVEL_DESIGN.md` section 7 if the decision rises to HLD-relevance.
4. Request review from at least one engineer who was not the author.
5. Merge the PR only after status is `Accepted`.

---

## Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Platform Engineering | Initial release |
