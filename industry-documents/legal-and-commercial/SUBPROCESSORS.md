# TechNova RAG — Sub-processor Register

| Field            | Value                                  |
|------------------|----------------------------------------|
| Owner            | TechNova Legal / DPO                   |
| Classification   | Public — Customer Shareable            |
| Last Reviewed    | 2026-04-16                             |
| Next Review      | 2026-10-16                             |
| Version          | 1.0                                    |

## (a) Overview and Change-Notice Commitment

This document lists all third-party Sub-processors that TechNova, Inc. (**"TechNova"**) engages to Process Customer Personal Data in connection with the TechNova RAG platform (the **"Service"**). It is maintained in accordance with Article 28(4) of the GDPR and the corresponding provisions of the UK GDPR and the Swiss FADP, and is cross-referenced from Annex III of the TechNova Data Processing Addendum.

**Change-notice commitment.** TechNova will provide Customers with at least **thirty (30) days' prior written notice** before authorizing any new Sub-processor or materially changing the scope of an existing Sub-processor's Processing. Notice will be delivered by:

1. Updating this register (with a new Version in the Revision History);
2. Sending a notification to the primary Customer contact on file; and
3. Publishing to the subscription list at [subprocessors.technova.example/subscribe] (see Section (f)).

**Objection right.** Customers may object in writing on reasonable data-protection grounds within the 30-day notice period, in which case the Parties will work in good faith to resolve the objection. If resolution is not possible, Customer may terminate the affected Order Form for cause under Section 4.3 of the Master Services Agreement without penalty, and TechNova will refund prepaid, unused Fees for the terminated portion.

## (b) Active Sub-processors

The following Sub-processors are authorized as of 2026-04-16.

| # | Name                          | Role                                                    | Data Processed                                                                                                    | Purpose                                                                         | Location / Region                                                 | Transfer Mechanism                                                       | DPA Link                                                      | Certifications                                                                 | Last Review |
|---|-------------------------------|---------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|-------------------------------------------------------------------|--------------------------------------------------------------------------|---------------------------------------------------------------|--------------------------------------------------------------------------------|-------------|
| 1 | OpenAI, L.L.C.                | LLM inference provider                                   | User query text; retrieved top-5 chunk texts; system prompt; role claim (as part of prompt only where relevant)    | Generate the natural-language answer for `/api/query` using the `gpt-4o-mini` model | USA (api.openai.com)                                              | EU SCCs Module Two (via TechNova as exporter); UK IDTA where applicable  | https://openai.com/policies/data-processing-addendum          | SOC 2 Type II; ISO 27001; ISO 27017; ISO 27018; CSA STAR                       | 2026-04-16  |
| 2 | Neon, Inc.                    | Managed Postgres database                                | Chat sessions, chat messages, corpus mirror (documents + chunks tables), role claims, user IDs                     | Persistent storage for chat history and corpus mirror behind the `/documents` surface | Customer-selected: us-east-1, eu-central-1, or ap-southeast-1     | EU SCCs Module Two (for non-EU transfers); EU adequacy (eu-central-1)    | https://neon.tech/dpa                                         | SOC 2 Type II                                                                  | 2026-04-16  |
| 3 | Qdrant Solutions GmbH         | Managed vector database (OPTIONAL — Qdrant Cloud tier)   | Vector embeddings of chunks; chunk payload metadata (chunk_id, doc_slug, security level, page numbers, text)       | Dense retrieval stage of the hybrid pipeline (applicable only if Customer elects Qdrant Cloud over self-hosted) | Customer-selected EU or US region                                 | EU SCCs Module Two (US region); EU adequacy (EU region)                  | https://qdrant.tech/legal/dpa/                                | ISO 27001; SOC 2 Type II (in progress)                                         | 2026-04-16  |
| 4 | Vercel, Inc.                  | Frontend hosting (Edge network)                          | Static frontend assets; landing-page HTML; HTTP request metadata (IP, user agent) for edge routing                  | Delivery of the Next.js frontend for `/`, `/project-a`, `/project-b`, `/knowledge-graph`, `/documents`, `/pipeline` | Global Edge; origin in USA                                        | EU SCCs Module Two                                                       | https://vercel.com/legal/dpa                                  | SOC 2 Type II; ISO 27001; PCI DSS (for billing systems, not customer data)     | 2026-04-16  |
| 5 | Hugging Face, Inc.            | Model distribution (startup only)                        | Public model artifacts downloaded by the backend at service startup; no runtime Customer Data                      | One-time retrieval of `BAAI/bge-base-en-v1.5`, `cross-encoder/ms-marco-MiniLM-L-6-v2`, and spaCy `en_core_web_sm` | USA                                                               | EU SCCs Module Two (no runtime Personal Data transfer)                   | https://huggingface.co/terms-of-service (DPA on request)      | SOC 2 Type II                                                                  | 2026-04-16  |

### Deployment-Mode Notes

- **Self-hosted Qdrant (default).** When Customer elects the default deployment where Qdrant runs inside the Customer VPC as the `qdrant/qdrant` container image (Apache-2.0), Qdrant Solutions GmbH is **not** a Sub-processor with respect to that Customer. Row 3 applies only when Qdrant Cloud is elected in the Order Form.
- **OpenAI inference toggle.** If an Order Form disables OpenAI inference (e.g., for deployments that prefer returning the assembled prompt and retrieved chunks without generation), Row 1 does not apply to that deployment. In that mode, the knowledge graph also falls back to co-occurrence edges rather than LLM-derived edges.

## (c) Data-Minimization Summary — What Sub-processors Do NOT Receive

TechNova has designed the Service so that each Sub-processor receives only the data strictly necessary for its function. In particular:

| Sub-processor       | Does NOT receive                                                                                                                              |
|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| OpenAI              | Full corpus content; any chunks below the user's role clearance; vector embeddings; BM25 index; chat history of other users; raw PDF bytes     |
| Neon                | Raw PDF bytes; vector embeddings (those live in Qdrant); real-time query content except as persisted to chat history tables                    |
| Qdrant (Cloud)      | Raw PDF bytes; OpenAI prompts or responses; user account credentials; chat history                                                             |
| Vercel              | Any corpus content beyond the public landing page; chat messages; queries; role claims (API calls go directly from browser to FastAPI backend) |
| Hugging Face        | Anything at all other than standard public artifact requests at startup; no queries, chunks, or Customer Data                                  |

TechNova's contractual configuration with OpenAI relies on OpenAI's default API policy that API inputs and outputs are not used to train OpenAI models. Customers eligible for OpenAI's zero-retention abuse-monitoring arrangement may request that TechNova configure their deployment accordingly; in the absence of such arrangement, OpenAI's default 30-day abuse-monitoring retention applies.

## (d) Planned Changes

The following additions are on TechNova's roadmap and will be notified per Section (a) before going live. Their inclusion here is informational only and does not constitute Processing authorization until notice is issued.

| Planned Version | Proposed Sub-processor                                                 | Proposed Role                                                  | Expected Data                                          |
|-----------------|------------------------------------------------------------------------|----------------------------------------------------------------|--------------------------------------------------------|
| v1.1            | [Observability vendor TBD — e.g., Datadog, Inc. or Grafana Labs]       | Application performance monitoring, error tracking             | Service logs, error traces, request metadata; no Customer corpus content |
| v1.2            | [PII redaction vendor TBD — e.g., Microsoft Presidio managed service or equivalent] | Pre-inference redaction of direct identifiers in queries/chunks | Query text and chunk text during redaction only        |

## (e) Change History

| Version | Date       | Change                                            | Notice Method                      |
|---------|------------|---------------------------------------------------|------------------------------------|
| 1.0     | 2026-04-16 | Initial publication of Sub-processor register     | Register published; subscribers notified |

## (f) Notification Sign-Up

Customers, Authorized Users, and prospective Customers may subscribe to receive automatic notice of Sub-processor changes at:

**[subprocessors.technova.example/subscribe]**

Subscribers will be notified at least thirty (30) days before any authorized change takes effect, consistent with Section 8.2 of the Data Processing Addendum.

## Revision History

| Version | Date       | Author         | Summary         |
|---------|------------|----------------|-----------------|
| 1.0     | 2026-04-16 | TechNova Legal | Initial release |
