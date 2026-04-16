# TechNova RAG — Support SLA

| Field            | Value                                  |
|------------------|----------------------------------------|
| Owner            | TechNova Customer Success / Engineering|
| Classification   | Public — Customer Shareable            |
| Last Reviewed    | 2026-04-16                             |
| Next Review      | 2026-10-16                             |
| Version          | 1.0                                    |

This Support SLA sets out TechNova's commitments for technical support for the TechNova RAG platform (the **"Service"**). It is incorporated into the Master Services Agreement by reference (see MSA Exhibit C) and operates alongside the availability commitments in SLA_SLO.md. Where a conflict exists between this document and the Order Form, the Order Form prevails for the Customer it governs.

## (a) Support Tiers

Support is delivered in four tiers. A Customer's tier is specified in the Order Form and may be changed at renewal.

| Tier          | Eligibility                                                                                                                     | Intended For                                         |
|---------------|---------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|
| Community     | Open-source or evaluation deployments; non-paying users                                                                         | Evaluators, community contributors, internal R&D     |
| Business      | Paid subscription with standard SLA; single production deployment                                                               | Small production teams                               |
| Enterprise    | Paid subscription with enhanced SLA; up to three (3) production deployments across regions                                       | Enterprises with 24/7 production requirements        |
| Enterprise+   | Paid subscription with premium SLA; unlimited production deployments; dedicated Customer Success Manager and named Support POD  | Regulated industries, mission-critical deployments   |

## (b) Severity Definitions

Severity classifies the impact of an issue, independent of tier. Customer selects severity when filing; TechNova may reclassify upon triage, with reasons recorded in the ticket.

| Severity | Name     | Definition                                                                                                                                                                                                 | Examples                                                                                                                                                                               |
|----------|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| P1       | Critical | Production outage, data loss, data corruption, security breach in progress, or exposure of RESTRICTED content outside the role boundary. No workaround available.                                          | `/api/query` returns 5xx for all tenants; Project B leaks a RESTRICTED chunk; Neon region unreachable; Qdrant collection loss; confirmed unauthorized access.                            |
| P2       | High     | Major feature unavailable or significantly degraded; significant performance degradation (e.g., p95 latency > 2x SLO for ≥ 15 min); workaround is impractical.                                              | Reranker crash; BM25 index corrupt requiring re-ingest; self-correcting retrieval loop disabled; knowledge graph empty after ingest; `/api/ingest` failing with unclear error.          |
| P3       | Medium   | Non-critical bug that does not prevent production use; workaround exists.                                                                                                                                  | Frontend layout regression on `/pipeline`; occasional cold-start slowness on `/api/graph`; citation rendering glitch in Markdown output; inaccurate knowledge-graph edge weights.       |
| P4       | Low      | Cosmetic issue, documentation gap, or enhancement request.                                                                                                                                                 | Typo in Documentation; request for additional metadata in `/api/status`; feature request for new role in role matrix.                                                                   |

## (c) Response-Time SLA Matrix

"**Response**" means the first substantive acknowledgment from a TechNova Support engineer (not an automated receipt) confirming receipt, initial severity assessment, and next-step plan.

Response times are measured from the moment the ticket is created in TechNova's ticket portal or the appropriate email/Slack alias for the tier.

| Severity | Community           | Business (Business Hours)         | Enterprise (24/7/365)     | Enterprise+ (24/7/365)    |
|----------|---------------------|-----------------------------------|---------------------------|---------------------------|
| P1       | Best effort         | 1 business hour                   | 30 minutes                | **15 minutes**            |
| P2       | Best effort         | 4 business hours                  | 2 hours                   | 1 hour                    |
| P3       | Best effort         | 1 business day                    | 1 business day            | 4 business hours          |
| P4       | Best effort         | 3 business days                   | 2 business days           | 1 business day            |

## (d) Resolution Target Matrix

"**Resolution**" means one of: (i) a permanent fix deployed; (ii) a workaround accepted in writing by Customer; or (iii) agreement to defer the fix to a later release with an ETA. Resolution targets are **targets**, not guarantees; service credits (Section (j)) are based on response-time SLA misses, not resolution misses.

| Severity | Community      | Business                        | Enterprise                           | Enterprise+                          |
|----------|----------------|---------------------------------|--------------------------------------|--------------------------------------|
| P1       | Best effort    | 1 business day                  | 8 hours (continuous)                 | **4 hours (continuous)**             |
| P2       | Best effort    | 3 business days                 | 2 business days                      | 1 business day                       |
| P3       | Best effort    | 15 business days                | 10 business days                     | 5 business days                      |
| P4       | Best effort    | Next major release (best effort)| Next major release (best effort)     | Prioritized per quarterly roadmap    |

## (e) Support Channels by Tier

| Channel                              | Community | Business                 | Enterprise         | Enterprise+         |
|--------------------------------------|-----------|--------------------------|--------------------|---------------------|
| Ticket portal (support.technova.example) | Yes       | Yes                      | Yes                | Yes                 |
| Email (support@technova.example)     | Yes       | Yes                      | Yes                | Yes                 |
| Community forum (community.technova.example) | Yes       | Yes                      | Yes                | Yes                 |
| Slack Connect (shared channel)       | No        | No                       | No                 | **Yes**             |
| Phone (P1-only hotline)              | No        | No                       | No                 | **Yes**             |
| Named Customer Success Manager       | No        | No                       | No                 | **Yes**             |
| Named Support POD (primary / backup) | No        | No                       | Optional (add-on)  | **Yes**             |
| Quarterly Business Review            | No        | Annual                   | Quarterly          | Quarterly           |

## (f) Business Hours Definition

"**Business hours**" are defined per region and align with local federal banking calendars:

| Region | Business Hours (Local)            | Coverage Notes                                                               |
|--------|-----------------------------------|------------------------------------------------------------------------------|
| US     | 08:00 – 18:00 Pacific Time, Mon–Fri | Federal US holidays excluded                                                 |
| EU     | 09:00 – 18:00 Central European Time, Mon–Fri | German federal holidays observed                                             |
| APAC   | 09:00 – 18:00 Singapore Time, Mon–Fri | Singapore national holidays observed                                         |

Enterprise and Enterprise+ P1/P2 coverage is **24/7/365**, irrespective of region. Business-tier response targets quoted in "business hours" apply in the region on the Order Form. If a P1 is raised outside Business-tier business hours, response timing is measured from the start of the next business day in the applicable region.

## (g) Escalation Path

Unresolved tickets follow the standard escalation ladder:

1. **L1 — Support Engineer.** Triage, initial diagnosis, known-issue matching, workaround provision.
2. **L2 — Senior Support Engineer.** Reproducing issues, reading structured audit logs, inspecting retrieval traces (`retrieval_method`, reranker scores, self-correction flags), working with the customer's role matrix.
3. **L3 — Engineering On-Call.** Issues in the retrieval pipeline (Qdrant, BM25, hybrid fusion, reranker), ingestion (`/api/ingest`), OpenAI integration, Neon schema, knowledge-graph construction; issues requiring code changes.
4. **VP Engineering.** Persistent P1 not resolved within 2× the target; security incidents; cross-functional escalations.
5. **CTO / CEO.** Reserved for executive-level escalations (breach disclosure coordination, regulatory inquiries, major customer incidents).

Customer may request escalation at any time via ticket comment or the Slack Connect channel (Enterprise+). Enterprise+ customers have a named CSM who owns escalation on their behalf.

## (h) Exclusions

Support obligations do not apply to, and response/resolution clocks pause during:

1. **Customer-caused issues.** Misconfiguration, misuse, or violations of the Acceptable Use Policy; modifications to the Service not made or authorized by TechNova; problems caused by Customer-supplied role-clearance mappings or document-metadata overrides.
2. **Third-party outages.** Outages of OpenAI (api.openai.com), Neon, Qdrant Cloud, Vercel, Hugging Face Hub, or the Customer's own VPC or network. OpenAI-side latency and availability incidents are tracked separately from TechNova SLOs and are visible on [status.technova.example] as upstream-dependency incidents. Where OpenAI confirms an incident, TechNova will coordinate customer communications but is not obligated to refund for the upstream impact beyond what is contractually guaranteed to TechNova by the upstream.
3. **Force majeure.** As defined in the MSA.
4. **Disabled or unsupported deployments.** Deployments running outside the supported matrix in the Documentation (e.g., unsupported Python versions, unsupported container runtimes, self-hosted Qdrant versions below the minimum in the release notes).
5. **Beta / experimental features.** Any surface or endpoint labeled "beta," "experimental," or "preview" in the Documentation is supported on a best-effort basis only.
6. **Requests for legal or regulatory advice.** Support engineers will not opine on legal classification, regulatory treatment, or acceptability of outputs under any regulatory regime.

## (i) Monthly Support Metrics Reporting

For Enterprise and Enterprise+ Customers, TechNova delivers a monthly support report within ten (10) business days of month-end, including:

- Ticket volume by severity and channel;
- Response-time compliance against SLA (mean, p50, p95);
- Resolution-time performance against targets;
- Top recurring issue categories;
- Upstream-dependency incidents attributed to OpenAI, Neon, Qdrant Cloud, or Vercel;
- Retrieval-pipeline health summary (dense/BM25/hybrid split; self-correction trigger rate; access-denied event rate);
- Any SLA credits owed (see Section (j)).

Business Customers receive an annual support summary at renewal.

## (j) SLA Credits for Response-Time Misses

Credits for missed **response-time** SLAs are calculated on the same grid as the **availability** credits in SLA_SLO.md and are applied against the next invoice. Refer to SLA_SLO.md for the percentage table and the credit-request mechanics; the grid is reproduced and cross-checked there to ensure consistency.

Summary of mechanics:

1. Customer must request credits in writing within thirty (30) days of the missed SLA.
2. Credits are capped at twenty percent (20%) of the monthly Fees for the affected Service in any given month, regardless of how many SLA misses occurred.
3. Credits are Customer's sole and exclusive remedy for SLA misses, subject to the termination-for-chronic-miss provisions in the MSA and SLA_SLO.md.
4. A missed **response-time** SLA does not compound with an **availability** SLA miss — the greater of the two credits applies for that month.

## (k) Maintenance and Release Windows

TechNova schedules maintenance to minimize Customer impact:

| Type                             | Notice Period                      | Window                                                         |
|----------------------------------|------------------------------------|----------------------------------------------------------------|
| Emergency maintenance            | As soon as reasonably practicable | Minimal; documented post-hoc in status page                     |
| Routine maintenance (non-breaking)| **30 days'** prior notice         | Off-peak per region; Sunday 02:00–06:00 local by default         |
| Breaking release (API or schema) | **90 days'** prior notice          | Coordinated with affected Customers; migration guide provided    |
| Security patches                 | ASAP (may supersede other notice)  | Timed to minimize exposure; post-hoc notice where urgent        |

**Breaking changes.** Breaking changes to `/api/*` endpoints, the chunk payload contract (see CONVENTIONS.md), the role-clearance matrix schema, the BM25 pickle format, or any response type mirrored in `frontend/lib/types.ts` are subject to the 90-day notice requirement and will be accompanied by a written migration guide.

Customers may request individual maintenance windows (for example, to avoid an earnings blackout period) via their CSM (Enterprise+) or the ticket portal.

## (l) On-Call Rotation Summary

TechNova maintains a follow-the-sun on-call rotation covering P1 incidents 24/7/365 for Enterprise and Enterprise+ Customers:

| Shift     | Time Zone Coverage            | Primary Location         |
|-----------|-------------------------------|--------------------------|
| Americas  | 16:00 – 00:00 UTC             | US                       |
| EMEA      | 08:00 – 16:00 UTC             | EU                       |
| APAC      | 00:00 – 08:00 UTC             | Singapore                |

Each shift has a primary on-call Support engineer and a backup, plus an L3 Engineering on-call for pipeline, ingestion, and security incidents. Paging occurs via the ticket portal automatically for P1 tickets and via the phone hotline (Enterprise+) directly. Response SLAs apply continuously across handoffs.

## Revision History

| Version | Date       | Author         | Summary         |
|---------|------------|----------------|-----------------|
| 1.0     | 2026-04-16 | TechNova Legal | Initial release |
