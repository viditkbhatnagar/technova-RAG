# TechNova RAG Onboarding Playbook

Audience: TechNova Customer Success Managers, Solutions Engineers, Security Engineers, and customer-side project leads | Version: 1.0 | Last Updated: 2026-04-16

This playbook structures a new-customer onboarding over four weeks, from kickoff to general availability. It is written for deployments where TechNova RAG will run in the customer's infrastructure (private VPC or managed Docker host) with their own corpus, over their own role model. The goal at the end of Week 4 is a signed-off, pilot-tested deployment with documented admin ownership and a published feedback loop.

## 1. Overview and objectives

You are delivering four things:

1. **A running environment** — backend, Qdrant, Neon Postgres, and frontend, wired to the customer's identity provider.
2. **An ingested corpus** — the customer's PDFs with correct classifications, validated by an acceptance test.
3. **A trained user base** — 10–20 pilot users across roles, plus a GA rollout for the rest of the population.
4. **Operational handover** — an admin who knows the runbook, a monitoring baseline, and a clear escalation path.

Each week has a **gate**. You do not advance until the gate passes, because downstream work compounds on upstream mistakes.

| Week | Theme | Gate |
|---|---|---|
| 1 | Kickoff and setup | Environment reachable; identity integration designed |
| 2 | Corpus and role validation | Ingest complete; access-control tests pass |
| 3 | Pilot | 10+ pilot users active; feedback triaged |
| 4 | GA launch | Admin trained; sign-off signed |

## 2. Week 1 — Kickoff and setup

### 2.1 Kickoff call (Day 1)

A single 90-minute session with the customer lead, their admin-to-be, a security stakeholder, and the TechNova CSM. Agenda:

- Review scope: surfaces enabled (Project A, Project B, knowledge graph, documents browser, pipeline visualizer).
- Confirm infrastructure target (managed Docker VM, the customer's Kubernetes, or their cloud managed services).
- Identify the identity provider (Okta, Entra, Google Workspace) and the mapping from IdP groups to TechNova roles.
- Agree the initial corpus size (typical pilot: 10–30 PDFs) and the sensitive subset that will need RESTRICTED classification.
- Share the four-week schedule and name the owner on each side for each gate.

Deliverable: a signed one-pager restating scope, roles, and timeline.

### 2.2 Environment provisioning (Days 2–4)

The solutions engineer provisions:

- **Backend host**: a VM or managed container runtime with 8+ GB RAM and Python 3.12.
- **Qdrant**: either in Docker on the backend host, or managed Qdrant Cloud.
- **Neon Postgres**: a project in the customer's Neon org; capture `DATABASE_URL` for chat history and the documents mirror.
- **Frontend**: Vercel deployment or a second container on the backend host.
- **Secrets**: `OPENAI_API_KEY`, `DATABASE_URL`, `QDRANT_URL`, and any IdP client secrets, stored in the customer's secret manager.

By end of day 4, `curl <host>/api/status` should return a live response (with `ingest_complete: false` — expected at this stage).

### 2.3 SSO integration design (Days 3–5)

The target state is SSO-fronted in Week 4. Week 1 produces the design:

- **OIDC/OAuth flow** diagram with the IdP, a reverse proxy (Cloudflare Access or similar), and the backend.
- **Group-to-role mapping**: IdP groups → TechNova `employee` / `manager` / `admin`. Default-deny for unmapped groups.
- **Fallback** for week 2–3 where SSO may not yet be live: IP allow-list + basic-auth bastion, with the demo-grade role-in-body still honoured internally.

Deliverable: an approved SSO design document (lives in `access-and-identity/SSO_SCIM_PLAN.md`).

### 2.4 Role mapping workshop (Day 5)

A 60-minute working session with the customer's security team. Output:

- Confirmed list of IdP groups in scope.
- A mapping table for each group to one of the three TechNova roles.
- A list of edge cases (contractors, board members, auditors) and how they map.
- A plan for quarterly audit of the mapping.

### 2.5 Week 1 gate

- [ ] Backend, Qdrant, and Postgres are reachable from the customer's network.
- [ ] `GET /api/status` returns 200.
- [ ] SSO design is approved and scheduled for implementation.
- [ ] Role mapping is documented and signed off by security.

If any item is red, Week 2 does not start. Slipping Week 2 by a few days is cheaper than ingesting a corpus under the wrong role model.

## 3. Week 2 — Corpus ingest and role validation

### 3.1 Corpus intake (Day 6)

The customer uploads their PDFs to a private S3 bucket or an SFTP drop. Solutions engineering:

- Inventories the files, produces a spreadsheet: filename, owner, proposed `doc_slug`, proposed `domain`, proposed `security_level`, proposed `security_label`.
- Flags any file that duplicates an existing one, is encrypted, is not machine-readable (scanned image PDFs need OCR — out of scope for v1.0), or exceeds 300 pages.
- Sends the spreadsheet to the customer for approval.

### 3.2 Classification workshop (Days 7–8)

A 2-hour meeting with the customer's legal, security, and HR leads. The agenda walks each document and assigns:

- `PUBLIC` (0): safe to share externally.
- `INTERNAL` (1): employees and above.
- `CONFIDENTIAL` (2): managers and above.
- `RESTRICTED` (3): admins only.

Default to the **more restrictive** option when in doubt. Downgrading is a one-line metadata change; a leak is a remediation project.

Deliverable: a signed classification matrix stored in the customer's governance log.

### 3.3 Run ingest (Day 9)

Solutions engineering copies the PDFs to `docs/`, updates `DOCUMENT_METADATA` in `backend/config.py`, and runs:

```bash
curl -X POST https://<host>/api/ingest \
  -H 'content-type: application/json' \
  -d '{"force_reingest": true}'
```

Confirm the response reports the expected document count and chunk count. Confirm `/documents` lists each file with the correct label.

### 3.4 Acceptance tests (Day 10)

Two test suites, run manually by the solutions engineer with the customer's admin observing.

**Golden-query suite — 10 queries per role (30 total).** The customer supplies the queries during Week 1; each one has an expected answer and a pointer to the source chunk. The test passes if 8 of 10 per role return an answer that cites the expected source.

**Adversarial access-control suite.** For every RESTRICTED document, craft a query that maps squarely onto its content and run it as each role:

- Employee role → must return access-denied.
- Manager role → must return access-denied (for RESTRICTED) or the answer (for CONFIDENTIAL).
- Admin role → must return the answer.

Document the matrix. Any failure is a gate blocker.

### 3.5 Week 2 gate

- [ ] Ingest complete; chunk and graph counts match expectation.
- [ ] Golden-query suite passes at >=80% per role.
- [ ] Access-control matrix passes 100%.
- [ ] Classification matrix signed off.

## 4. Week 3 — Pilot

### 4.1 Pilot group selection

10–20 users, distributed across the three roles:

- 5–8 employees (cover 2–3 departments).
- 3–5 managers.
- 2–3 admins (at least one from security).

Choose users who will actually try the tool. Reluctant pilots produce no feedback.

### 4.2 Pilot kickoff (Day 11)

A 45-minute walkthrough: what the tool does, how to ask good questions, how to report bad answers, how to read citations, and where to find the feedback form. Share the `USER_GUIDE.md` ahead of time.

### 4.3 Daily office hours (Days 11–15)

30 minutes each day, drop-in, run by the solutions engineer. Common topics:

- "Why didn't my query find X?" — almost always a classification mismatch or a phrasing issue.
- "This answer looks wrong." — feedback goes to triage.
- "Can I see the roadmap?" — scope-and-access conversation.

### 4.4 Feedback capture and triage

Every reported bad answer gets one of four labels:

| Label | Meaning | Action |
|---|---|---|
| Retrieval miss | Expected chunk not retrieved | Add to regression set; tune retrieval if repeated |
| Generation error | Retrieval OK, answer wrong | Review prompt template; retrain prompt with examples |
| Classification dispute | Access-denied where user expected access | Escalate to data governance |
| Out-of-scope | Corpus doesn't cover it | Log as potential corpus addition |

Triage a batch of feedback at the end of each day. If the same complaint surfaces from three independent users, fix in place before continuing.

### 4.5 Iteration

Based on triage, you may need to:

- Adjust the prompt template in `backend/services/generator.py`.
- Reclassify one or two documents.
- Add synonyms to the self-correcting loop's `_SYNONYMS` list in `backend/services/security.py` for domain-specific vocabulary.
- Re-ingest with tuned chunk size if retrieval is consistently surface-level.

Each change is documented in the customer's change log.

### 4.6 Week 3 gate

- [ ] 10+ pilot users active (measured by sessions in the `/api/sessions` history).
- [ ] Feedback triage backlog is empty at end of week.
- [ ] No unresolved classification disputes.
- [ ] Pilot lead signs off on readiness for GA.

## 5. Week 4 — GA launch

### 5.1 User training session (Day 16)

A 60-minute session for the full user base. The pilot users attend as advocates. Cover:

- The two chat surfaces (Project A / Project B) and when to use each.
- The knowledge graph and the documents browser.
- Access-denied, what it means, how to escalate.
- Feedback flow.

Record the session for async consumption.

### 5.2 Admin handover (Day 17)

A half-day session with the customer's admin. Walk through:

- `ADMIN_GUIDE.md` end to end.
- Running ingest on a schedule or on-demand.
- Reading logs, watching `/api/status`, monitoring Qdrant and Postgres.
- Adding, removing, and reclassifying documents.
- Deleting sessions for retention and GDPR.
- The backup plan: Qdrant snapshots, Neon PITR, git for corpus.

Hand over credentials rotating the TechNova SA keys back to customer ownership.

### 5.3 Runbook walkthrough (Day 18)

Walk through the incident runbook: what to do when ingest fails, Qdrant disconnects, answers drift, or the generator key is revoked. Confirm the escalation path is in the customer's on-call schedule.

### 5.4 Support escalation path (Day 19)

Document:

- Tier 1: customer admin handles day-to-day.
- Tier 2: TechNova CSM handles bugs, feature requests, classification changes.
- Tier 3: TechNova Solutions Engineering for infrastructure and model-tier issues.

SLAs: Tier 2 acknowledges within 1 business day; Tier 3 acknowledges within 4 business hours for P1.

### 5.5 Formal sign-off (Day 20)

A short meeting with the customer lead, CSM, and admin. Confirm:

- Environment healthy, acceptance matrix green.
- Users trained; feedback loop active.
- Admin owns the runbook and has practised a re-ingest.
- Support path is active.

Both sides sign a one-pager acknowledging GA. Move the customer to steady-state.

### 5.6 Week 4 gate

- [ ] Training session delivered; recording published.
- [ ] Admin handover signed.
- [ ] Support escalation path documented and active.
- [ ] GA sign-off signed by both sides.

## 6. RACI matrix

| Activity | Customer | TechNova CSM | TechNova SE | TechNova Security |
|---|---|---|---|---|
| Kickoff | A | R | C | I |
| Environment provisioning | C | I | R | A |
| SSO design | A | C | R | C |
| Role mapping | A | C | C | R |
| Corpus intake and classification | A | C | R | C |
| Ingest | I | I | R | I |
| Acceptance tests | C | C | R | A |
| Pilot recruitment | R | A | C | I |
| Pilot office hours | I | C | R | I |
| Feedback triage | C | R | A | I |
| User training | A | R | C | I |
| Admin handover | R | C | A | I |
| GA sign-off | A | R | C | C |

Key: **R**esponsible, **A**ccountable, **C**onsulted, **I**nformed.

## 7. Milestones and gates (summary)

| Milestone | When | Blocks |
|---|---|---|
| Environment reachable | End of Week 1 | Week 2 ingest |
| Classification signed | Mid Week 2 | Ingest |
| Access-control matrix green | End of Week 2 | Pilot |
| Feedback backlog empty | End of Week 3 | GA training |
| Admin handover signed | Mid Week 4 | GA sign-off |
| GA sign-off | End of Week 4 | Steady state |

Do not ship early. An onboarding that slips by a week because of a classification dispute is a success; an onboarding that hits GA with the wrong role mapping is a breach waiting to happen.

## 8. Common risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Classification disputes | High | Medium | Run the classification workshop upfront, with legal and security in the room. Default to more restrictive. |
| SSO integration delays | Medium | High | Approve the SSO design in Week 1. Run pilot behind VPN + role-in-body during Week 2–3. Cut over in Week 4. |
| Pilot adoption lag | Medium | High | Pick engaged pilots. Run daily office hours. Make the feedback form 30 seconds long. |
| Corpus too small or stale | Low | Medium | Work with the customer in Week 1 to surface the top 20 PDFs. Plan a corpus refresh cycle. |
| Hallucinations on edge queries | Medium | Medium | Capture every one during the pilot; refine prompt and reranker during Week 3 iteration. |
| Admin churn post-handover | Low | High | Train two admins, not one. Record the handover session. |

## 9. Ongoing (month 2+)

Onboarding ends at GA, but the relationship doesn't.

- **Monthly review** — 30 minutes with the customer lead and admin: usage metrics, top feedback themes, corpus additions requested.
- **Quarterly role audit** — re-run the role mapping against the current IdP groups. Retire stale groups; confirm contractor and auditor mappings.
- **Quarterly classification audit** — sample 10 documents; confirm classifications still reflect business reality.
- **Annual corpus refresh** — full re-ingest after bulk document updates. Plan for 2 hours of downtime plus an acceptance re-run.
- **Upgrade cadence** — patches as released; minor version upgrades monthly; major version upgrades with a 4-week planning window per `VERSIONING_POLICY.md`.

## Revision history

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Documentation | Initial release |
