# TechNova RAG — Operational Runbooks

**Owner:** TechNova Platform Engineering / SRE
**Classification:** INTERNAL
**Last Reviewed:** 2026-04-16
**Next Review:** 2026-10-16
**Version:** 1.0

---

## How to use this document

Each runbook is scoped to one symptom or class of failure. Runbooks are written so that any engineer in the on-call rotation can execute them without prior context on the incident. The standard structure is:

- **Trigger / Alert** — what fires this runbook
- **Severity** — Sev 1 (page), Sev 2 (urgent ticket), Sev 3 (ticket)
- **Detection** — where the signal comes from
- **Triage** — 2–5 minutes of scoping before intervention
- **Fix steps** — numbered, deterministic
- **Verification** — how to know it worked
- **Rollback** — how to undo if fix causes a new problem
- **Related alerts** — signals that may co-fire
- **Post-incident tasks** — non-urgent cleanup

All commands assume the operator is running against the production cluster. Development URLs (e.g. `http://localhost:8000`) are included when the runbook may be executed in dev for rehearsal.

---

## R-01 — Ingest failure

**Trigger / Alert:** `technova_ingest_total{status="error"}` increments; `/api/ingest` returns 5xx; CI ingest job fails.

**Severity:** Sev 2 (no ingest in progress blocks new corpus, but existing corpus continues to serve).

**Detection:**
- PagerDuty alert "TechNova — ingest error"
- Backend logs: `ERROR backend.routers.ingest` exception
- `/api/status` shows `chunks_indexed` below expected baseline after an ingest attempt

**Triage (under 5 min):**
1. Classify the subclass:
   - **Loader exception** (pypdf): often a malformed or encrypted PDF in `docs/`. Backend log shows `pypdf.errors.PdfReadError`.
   - **Embedder OOM**: backend container killed, `dmesg` shows OOMKilled, or Python traceback includes `torch.cuda.OutOfMemoryError` (CPU will show `MemoryError`).
   - **Qdrant insert error**: logs show `UnexpectedResponse` or `ConnectionError` from the qdrant_client.
2. Check if this is a first-time ingest or a re-ingest. First-time ingest failures are usually config-related; re-ingest failures are usually infra-related.
3. Confirm with `curl http://localhost:8000/api/status`.

**Fix steps:**

*Loader exception:*
1. Identify the offending PDF from the traceback (last filename logged before the exception).
2. Open the PDF locally; if it is encrypted or corrupt, quarantine it by removing from `docs/` and the `DOCUMENT_METADATA` entry in `backend/config.py`.
3. Re-run ingest:
   `curl -X POST http://localhost:8000/api/ingest -H 'content-type: application/json' -d '{}'`
4. File a ticket to replace the PDF.

*Embedder OOM:*
1. Reduce batch size in `backend/services/embedder.py` (lower `batch_size` to 16 or 8).
2. Restart backend.
3. Re-run ingest.
4. If production, scale replica memory allocation and revert batch size once confirmed.

*Qdrant insert error:*
1. Verify Qdrant reachable: `curl ${QDRANT_URL}/collections`.
2. If unreachable, run R-02.
3. If reachable but returning errors, check `/api/status` for collection existence; if missing, let ingest recreate it.
4. Re-run ingest.

**Verification:**
- `curl http://localhost:8000/api/status | jq '.chunks_indexed'` returns non-zero and matches expectations (~400 for current corpus).
- Run one canary query; `sources` is non-empty.

**Rollback:** Ingest is idempotent; there is no rollback required. If the new state is worse than the old, restore the Qdrant snapshot per DR_BCP section 5.

**Related alerts:** R-02 (Qdrant unavailable), R-07 (BM25 pickle corruption).

**Post-incident tasks:**
- If loader exception, track PDF replacement in ticket.
- If OOM, consider adding a chunked-embedder mode for large PDFs.

---

## R-02 — Qdrant unavailable

**Trigger / Alert:** `technova_qdrant_up` = 0; repeated 503s from `/api/query`; backend logs show `ConnectionError` or `httpx.ConnectError` targeting `${QDRANT_URL}`.

**Severity:** Sev 1 (query blocked).

**Detection:**
- PagerDuty alert "TechNova — Qdrant unreachable"
- `/api/status` returns `{qdrant_available: false}`
- Synthetic probe 503s across the fleet

**Triage:**
1. Check the Qdrant Cloud status page (or cluster node health for self-host).
2. Test connectivity from a backend pod: `curl -v ${QDRANT_URL}/readyz`.
3. Check for recent Qdrant config changes (deploy history).

**Fix steps:**
1. If Qdrant Cloud is reporting an outage, post to StatusPage and wait; confirm backend is returning 503 to callers (not 500).
2. If self-hosted and the node is down, restart: `docker compose restart qdrant` (dev) or the orchestrator equivalent (prod).
3. If disk is full on the Qdrant node (`df -h` shows 100%), prune old snapshots from `/qdrant/snapshots/` older than 30 days.
4. If the collection is missing, run R-05 (full re-ingest) or DR_BCP section 5 (snapshot restore).
5. Verify payload indexes on `security_level` and `doc_slug` after any restore.

**Verification:**
- `curl ${QDRANT_URL}/collections/technova_docs` returns status `green`
- Two consecutive synthetic probes pass
- `/api/status` reports `qdrant_available: true`

**Rollback:** Restoring from snapshot is non-destructive; no rollback required.

**Related alerts:** R-01, R-05.

**Post-incident tasks:**
- Confirm snapshot schedule is running.
- If recurrence, escalate to Qdrant Cloud support with incident ID.

---

## R-03 — OpenAI API outage or rate limit

**Trigger / Alert:** `technova_openai_errors_total{status="5xx"}` or `{status="429"}` exceeds threshold; user reports of missing `answer` field.

**Severity:** Sev 2 (degraded, not down — backend serves retrieval-only).

**Detection:**
- Backend logs: repeated `openai.APIError` or `openai.RateLimitError`
- `/api/query` responses show `answer: null` with non-empty `sources`
- OpenAI status page red

**Triage:**
1. Classify: outage (OpenAI status page) vs. rate limit (our usage spiked) vs. auth (key revoked/expired).
2. Check `technova_openai_tokens_total` over the last hour vs. baseline.

**Fix steps:**

*Outage:*
1. Pin StatusPage banner ("LLM generation temporarily unavailable; retrieval results still returned").
2. Enable frontend flag `NEXT_PUBLIC_DISABLE_ANSWER=true` (or rely on frontend auto-hide when `answer` is null).
3. Wait for OpenAI recovery; post hourly updates.

*Rate limit:*
1. Check which tier we are on (`curl https://api.openai.com/v1/dashboard/rate_limits` with the project key).
2. If legitimate traffic spike, request a rate-limit increase from OpenAI (same day for Tier 3+).
3. Enable request queueing in `backend/services/generator.py` (feature flag `OPENAI_QUEUE=true`).
4. Reduce `top_k_final` from 5 to 3 temporarily to shrink prompts.

*Auth:*
1. See R-06 for credential rotation.

**Verification:**
- `technova_openai_errors_total` rate returns below threshold for 15 minutes
- Canary query returns a non-null `answer`
- User reports stop

**Rollback:** Revert `top_k_final` and disable queueing once recovered.

**Related alerts:** R-06.

**Post-incident tasks:**
- If recurrence, file roadmap ticket to accelerate vLLM adapter (v1.2).
- Update capacity model if we are structurally near rate limits.

---

## R-04 — Stuck query (>30s)

**Trigger / Alert:** `technova_query_duration_seconds_bucket` p99 exceeds 30s sustained; user reports a hanging browser request.

**Severity:** Sev 2.

**Detection:**
- User report via support
- Backend logs show a pending request without response for >30s
- ALB 504 gateway timeout count elevated

**Triage:**
1. Identify the stuck request's stage from Prometheus stage histograms (`stage=embed|dense|bm25|rrf|rerank|generate`).
2. Likely culprits in order of frequency: `generate` (OpenAI slow), `rerank` (CPU saturation on rerank model), `dense` (Qdrant slow).

**Fix steps:**
1. If `generate` is the bottleneck: run R-03 checks; enable OpenAI request timeout (set `request_timeout=10` in generator if currently unbounded).
2. If `rerank` is the bottleneck: check backend CPU — `kubectl top pod` or equivalent. Scale replicas out. Verify no background ingest is running (ingest competes for CPU).
3. If `dense` is the bottleneck: run R-02 triage steps; consider if Qdrant is under compaction load.
4. Kill any ingest job that is holding GIL/CPU during user traffic peaks.
5. Roll the oldest backend replica (stuck requests may be trapped in a single pod's worker).

**Verification:**
- p99 latency returns below 5s for 30 minutes
- No 504s from ALB for 15 minutes

**Rollback:** Scale-out is not destructive.

**Related alerts:** R-02, R-03.

**Post-incident tasks:**
- If rerank is a recurring bottleneck, file ticket to move reranker to a dedicated node.

---

## R-05 — Vector-store corruption / full re-ingest

**Trigger / Alert:** Query quality regression detected; Qdrant reports inconsistent segments; BM25/Qdrant mismatch detected by probe.

**Severity:** Sev 2 (degraded correctness).

**Detection:**
- Probe mismatch: a query returns a BM25 hit whose `chunk_id` is not present in Qdrant (or vice versa)
- `/api/status` reports unexpected `chunks_indexed`
- User reports wrong answers

**Triage:**
1. Attempt a snapshot restore first (DR_BCP section 5) — faster if the corruption is recent.
2. Only run full re-ingest if snapshots are also compromised, or the corpus has been modified.

**Fix steps:**
1. Take a fresh snapshot of the current (corrupt) state for forensic analysis:
   `curl -X POST ${QDRANT_URL}/collections/technova_docs/snapshots -H "api-key: ${QDRANT_KEY}"`
2. Execute full re-ingest:
   `curl -X POST http://localhost:8000/api/ingest -H 'content-type: application/json' -d '{"force_reingest": true}'`
3. Wait for completion (~30–60s for current corpus). Watch logs for loader, chunker, embedder, store.
4. Verify `/api/status` shows expected `chunks_indexed` and `bm25_indexed`.
5. Confirm BM25 pickle was rewritten: `ls -la backend/bm25_index.pkl` — mtime should be within the last minute.
6. Confirm graph JSON was rewritten: `ls -la backend/graph_data.json`.
7. Restart backend replicas so `app.state` singletons pick up the new artifacts.

**Verification:**
- All 10 canary queries return correct top-1 source
- Access-denied probes all correct for Project B
- `sources[].retrieval_method` distribution shows mix of `dense`, `bm25`, `hybrid`

**Rollback:** Snapshot restore per DR_BCP section 5 if the re-ingest itself was worse than the prior state.

**Related alerts:** R-01, R-02, R-07.

**Post-incident tasks:**
- Root-cause the corruption source (bad deploy? partial ingest? manual Qdrant edit?)
- If corpus was the cause, update ingest integrity checks.

---

## R-06 — Credential rotation

**Trigger / Alert:** Scheduled quarterly rotation; suspected compromise; employee offboarding with secret access.

**Severity:** Sev 3 for scheduled, Sev 1 for suspected compromise.

**Detection:** Scheduled via calendar; or security incident report.

**Triage:**
- Identify which credential: `OPENAI_API_KEY`, `DATABASE_URL`, Qdrant API key.
- Confirm rotation path (Doppler versioning ensures a rollback if rotation fails).

**Fix steps:**

*OPENAI_API_KEY:*
1. Provision a new key in the OpenAI organization console; label with issue date and rotation cycle.
2. Update the secret in Doppler: `doppler secrets set OPENAI_API_KEY=<new>`.
3. Trigger a rolling restart of backend replicas (they read env at startup).
4. Verify with a canary query that `answer` is non-null.
5. Wait 1 hour for in-flight requests; revoke the old key in the OpenAI console.

*DATABASE_URL:*
1. In Neon console, rotate the database password (Neon issues a new connection string).
2. Update Doppler `DATABASE_URL` with the new string.
3. Rolling restart of backend replicas.
4. Verify via `curl http://localhost:8000/api/sessions` that Postgres is reachable (returns an empty or populated list, not 5xx).

*Qdrant API key:*
1. In Qdrant Cloud console, issue a new API key with the same scopes.
2. Update Doppler `QDRANT_API_KEY`.
3. Rolling restart.
4. Verify `curl http://localhost:8000/api/status` reports `qdrant_available: true`.
5. Revoke the old key after 1 hour.

**Verification:**
- `technova_query_total{status="2xx"}` rate steady
- `technova_openai_errors_total{status="401"}` = 0 after rotation
- No 5xx spike during rolling restart

**Rollback:** Doppler keeps the prior secret; `doppler secrets rollback <name>` restores it.

**Related alerts:** R-03.

**Post-incident tasks:**
- Log rotation in the secrets audit spreadsheet.
- Confirm next rotation date in calendar (+90 days).

---

## R-07 — BM25 pickle corruption

**Trigger / Alert:** Backend startup fails with pickling error; retriever falls back to dense-only; `retrieval_method` values missing `bm25` and `hybrid`.

**Severity:** Sev 2 (retrieval quality degraded).

**Detection:**
- Startup log: `pickle.UnpicklingError` or `EOFError` on `backend/bm25_index.pkl`
- Metric `technova_bm25_fallback_total` nonzero (v1.1)

**Triage:**
1. Confirm pickle exists: `ls -la backend/bm25_index.pkl`.
2. If empty or missing, something truncated it. Check disk space and most recent deploy.

**Fix steps:**
1. Delete the corrupt pickle: `rm backend/bm25_index.pkl`.
2. Trigger full re-ingest: `curl -X POST http://localhost:8000/api/ingest -H 'content-type: application/json' -d '{"force_reingest": true}'`.
3. Restart backend replicas to rehydrate `app.state.bm25`.

**Verification:**
- Two canary queries return at least one `sources[].retrieval_method == "bm25"` or `"hybrid"`
- Pickle file present with current mtime

**Rollback:** None required (the pickle is derivable).

**Related alerts:** R-01, R-05.

**Post-incident tasks:**
- If recurrence, evaluate moving BM25 index to a backed store (Elasticsearch — v1.3 roadmap).

---

## R-08 — Access-denied rate spike (potential reconnaissance)

**Trigger / Alert:** `technova_access_denied_total` rate exceeds 5x the 7-day baseline; sustained over 10 minutes.

**Severity:** Sev 2 (security signal).

**Detection:**
- PagerDuty alert "TechNova — access-denied spike"
- Security dashboard shows denied queries clustered on one role, session, or IP

**Triage:**
1. Identify the distribution: one user, one role, one IP, or spread? Pull from logs:
   structured JSON logs filtered by `event=access_denied`.
2. Inspect query patterns — benign (user hunting for info) vs. probing (enumeration of restricted keywords).
3. Correlate with IdP events for the same session.

**Fix steps:**
1. If one user account: check IdP recent logins; if anomalous, suspend the account and contact Security.
2. If spread across IPs: enable rate limiting on `/api/query` at the ingress (`50 req/min` per IP) if not already active.
3. If a known benign cause (e.g. new employee exploring), contact the user directly.
4. Capture a sample of the denied queries and the role used for the post-incident review.

**Verification:**
- Denied rate returns to baseline over 15 minutes
- No restricted content leaked (confirm via audit — access-denied correctness probe passes)

**Rollback:** Account unsuspension once cleared by Security.

**Related alerts:** None direct; may correlate with IdP failed-login alerts.

**Post-incident tasks:**
- Document the incident in the security log.
- Evaluate whether synonym expansion in `backend/services/security.py` should be tuned to avoid false positives.

---

## R-09 — Neon Postgres failover

**Trigger / Alert:** `technova_postgres_write_errors_total` sustained; `/api/sessions` returns 5xx.

**Severity:** Sev 2 (chat history degraded; query path still works).

**Detection:**
- PagerDuty alert "TechNova — Postgres write errors"
- Backend logs show `asyncpg.exceptions.ConnectionDoesNotExistError` or `ServerShutdownError`
- `/api/sessions` returns 5xx

**Triage:**
1. Check Neon status page.
2. Check for recent Neon compute scale-to-zero (some Business tiers auto-sleep).

**Fix steps:**
1. If scale-to-zero, a fresh request will wake the compute (~2–5s). Confirm by retry.
2. If region outage, follow DR_BCP section 4.2 regional failover for Postgres.
3. If persistent write errors but reads work, enable read-only mode (feature flag `CHAT_READONLY=true`); users will see "history temporarily read-only".

**Verification:**
- `/api/sessions` returns 2xx
- A test session round-trip succeeds

**Rollback:** Disable the `CHAT_READONLY` flag once writes recover.

**Related alerts:** None; Postgres failure is isolated from query path by design.

**Post-incident tasks:**
- If scale-to-zero is chronic, upgrade Neon compute plan for production.

---

## R-10 — Frontend deploy rollback

**Trigger / Alert:** Error rate from RUM spikes post-deploy; synthetic probe frontend test fails; user reports after a deploy.

**Severity:** Sev 2.

**Detection:**
- RUM `js_error_rate` > 1% for 5 minutes after a deploy
- Vercel deploy logs show build success but runtime errors in browser console
- User reports of broken UI

**Triage:**
1. Confirm the correlation with the most recent Vercel deploy (`vercel ls` + timestamps).
2. Check browser console for error — `Next.js` runtime error, hydration mismatch, API contract break.

**Fix steps:**
1. In Vercel project settings, promote the previous production deploy to active:
   `vercel promote <previous-deploy-url>` (or click "Promote to Production" in the dashboard).
2. Confirm DNS / routing has updated (typically immediate on Vercel).
3. Notify engineering channel and mark the offending deploy as broken in Vercel.
4. File a ticket to root-cause before re-deploy.

**Verification:**
- RUM `js_error_rate` returns to baseline within 10 minutes
- Manual walk-through of `/`, `/project-a`, `/project-b`, `/knowledge-graph`, `/documents` succeeds

**Rollback:** The rollback IS the recovery. If the previous deploy is also broken, roll back further.

**Related alerts:** None direct.

**Post-incident tasks:**
- Add a regression test covering the broken path.
- Confirm Next.js 16 compatibility — the repo is on a recent version; consult `node_modules/next/dist/docs/` before fixing.

---

## Appendix — Quick health checks

These commands should be memorized by every on-call engineer.

| Check | Command |
|---|---|
| Backend liveness | `curl http://localhost:8000/api/status` |
| Qdrant liveness | `curl ${QDRANT_URL}/readyz` |
| Postgres liveness | `curl http://localhost:8000/api/sessions` |
| Force re-ingest | `curl -X POST http://localhost:8000/api/ingest -H 'content-type: application/json' -d '{"force_reingest": true}'` |
| Normal ingest | `curl -X POST http://localhost:8000/api/ingest -H 'content-type: application/json' -d '{}'` |
| Canary query (Project A) | `curl -X POST http://localhost:8000/api/query -H 'content-type: application/json' -d '{"query": "What is the onboarding process?"}'` |
| Canary query (Project B, restricted) | `curl -X POST http://localhost:8000/api/query -H 'content-type: application/json' -d '{"query": "What is our incident response playbook?", "role": "intern"}'` |

---

## Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Platform Engineering | Initial release |
