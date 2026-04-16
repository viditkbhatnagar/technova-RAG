# TechNova RAG — Acceptable Use Policy

| Field            | Value                                  |
|------------------|----------------------------------------|
| Owner            | TechNova Legal / Trust & Safety        |
| Classification   | Public — Customer Shareable            |
| Last Reviewed    | 2026-04-16                             |
| Next Review      | 2026-10-16                             |
| Version          | 1.0                                    |

## (a) Scope

This Acceptable Use Policy (**"AUP"**) governs the use of the TechNova RAG platform (the **"Service"**), including the backend FastAPI application and its `/api/*` endpoints, the Next.js frontend surfaces (Project A, Project B, `/documents`, `/pipeline`, `/knowledge-graph`), and any embedded components such as the hybrid retrieval pipeline, the self-correcting retrieval logic, and the knowledge graph.

The AUP applies to:

1. Customers and Customer Affiliates who have entered into a Master Services Agreement (**"MSA"**) with TechNova;
2. Authorized Users (employees, contractors, or agents of a Customer) who access the Service;
3. Anyone who accesses the Service, whether TechNova-hosted or customer-hosted, under any evaluation, pilot, proof-of-concept, or production arrangement; and
4. Integrators who build clients or systems that interact with the `/api/*` endpoints.

Compliance with this AUP is a condition of access. Where Customer hosts the Service (e.g., with self-hosted Qdrant in a Customer VPC), Customer remains responsible for enforcing this AUP against its Authorized Users.

## (b) Prohibited Uses

You may not use the Service, and may not permit any other person to use the Service, to:

### (b.1) Bypass or Subvert Access Controls

- Attempt to bypass, disable, or manipulate the role-based access controls of Project B, including but not limited to modifying the `role` claim outside the authorization channel, exploiting the client to send a role value that exceeds the Authorized User's clearance, or attempting to confuse the dual pre-filter (applied at both the Qdrant dense stage and the BM25 stage).
- Attempt to circumvent the self-correcting retrieval safeguard that returns an access-denied response when a strong restricted match exists outside the user's clearance.
- Attempt to access `chunk_id` values, `doc_slug` values, or any chunk payload metadata corresponding to a higher security tier than the Authorized User's clearance.
- Use the `/documents` surface, the corpus mirror in Neon, the knowledge graph at `/knowledge-graph`, or any ingestion artifact (BM25 pickle, Qdrant collection) to reconstruct content the Authorized User is not authorized to view.

### (b.2) Abuse Infrastructure and Rate Limits

- Submit automated high-volume queries beyond the rate limits specified in the applicable Order Form or the published default (refer to the API Contract).
- Initiate repeated `/api/ingest` calls intended to exhaust TechNova's embedding and reranking capacity.
- Run sustained load testing against the production Service without TechNova's prior written authorization; load testing is available in a dedicated testing environment upon request.
- Use the Service to distribute denial-of-service or amplification traffic, or to mine cryptocurrency.

### (b.3) Reverse Engineering and Model Extraction

- Reverse-engineer, decompile, or disassemble any component of the Service.
- Attempt to reconstruct, infer, or reverse the security-classification scheme or the `DOCUMENT_METADATA` mapping from the Service's responses, including through systematic comparison of Project A and Project B outputs for identical queries.
- Attempt to elicit training data, weights, or model internals from the underlying foundation model (`gpt-4o-mini`) through prompt injection, jailbreaks, or chain-of-thought probing.
- Use the Service primarily to build a competing retrieval-augmented generation product or dataset, or to create benchmarks intended to be published without TechNova's written consent.

### (b.4) Unauthorized Content Inputs

- Upload to the corpus any personally identifiable information (**"PII"**) of individuals other than Customer's employees or contractors without a lawful basis and appropriate notice to those individuals under applicable privacy law.
- Upload classified government information, export-controlled technical data subject to restrictions the Service does not satisfy, or content whose processing by OpenAI, Neon, Qdrant (if Cloud), or Vercel would violate applicable law.
- Upload content that infringes third-party intellectual property rights, defames any person, constitutes child sexual abuse material, or contains malware.
- Upload content that violates U.S., EU, UK, or UN sanctions regimes or that originates from or is destined for an embargoed jurisdiction.

### (b.5) High-Risk and Regulated Decisions

- Use Service Output to make, in whole or in substantial part, adverse employment decisions (hiring, termination, compensation, disciplinary action, performance rating) in any jurisdiction where such decisions require a meaningful human review step — including, in particular, uses that would qualify as "high-risk AI systems" under the EU Artificial Intelligence Act, without implementing the human-oversight, transparency, and record-keeping obligations required by that law.
- Use Service Output to provide legal, medical, financial, or psychological advice to any person who is not an employee of Customer and has not been informed that the advice is AI-generated and subject to human review.
- Use Service Output as the sole or determinative basis for decisions affecting individuals' access to credit, housing, insurance, education, essential public services, or law-enforcement outcomes.

### (b.6) Platform Integrity

- Introduce viruses, worms, or other malicious code into the Service or its dependencies (e.g., poisoned PDFs designed to exploit `pypdf`).
- Falsify, forge, or strip audit-log metadata, `chunk_id` values, or retrieval-method indicators (`dense`, `bm25`, `hybrid`) in responses.
- Impersonate another user, Customer, or TechNova personnel.

## (c) Prompt Injection and Adversarial Probing

### (c.1) Prohibition on Unauthorized Adversarial Probing

Unauthorized adversarial probing of the Service — including crafting queries specifically intended to (i) cause the LLM to ignore system instructions, (ii) exfiltrate restricted chunks across the role boundary, (iii) cause the self-correcting retrieval loop to misclassify a query, or (iv) induce hallucinated citations — is prohibited.

### (c.2) Authorized Security Research

TechNova welcomes responsible security research. Security testing, penetration testing, red-teaming, and model-vulnerability research against the Service require **prior written approval** from TechNova's Security team. Approval will scope the testing to a dedicated environment and specify rules of engagement. Vulnerability disclosures should be sent to [security@technova.example]. TechNova operates a coordinated-disclosure program and will not pursue legal action against researchers who comply with the approved scope.

### (c.3) Customer-Originated Red-Teaming

Customers may conduct red-team exercises within their own tenant, provided such exercises do not (i) breach the tenant isolation boundary, (ii) generate traffic that impacts other tenants, or (iii) attempt to extract data about other tenants. Customers must notify TechNova at [security@technova.example] at least five (5) business days in advance.

## (d) Responsible Use

### (d.1) Output Verification

Service Output is generated by probabilistic large language models and may contain errors, omissions, or fabricated citations. Authorized Users are expected to:

1. Treat Output as a starting point, not a final answer, for any decision of material consequence;
2. Verify cited sources by opening the underlying document at the citation location (page number, chunk ID) surfaced in the response;
3. Escalate suspected hallucinations, stale content, or security-classification errors to Customer's designated administrator, who may report to TechNova.

### (d.2) AI Disclosure

Where applicable law requires disclosure that a response was generated by AI (for example, under the EU AI Act Article 50 or analogous consumer-facing transparency laws), Customer is responsible for ensuring such disclosure is made to the Authorized User or downstream recipient.

### (d.3) Alignment with Customer Policy

Each Customer must publish an internal usage policy that aligns with this AUP and its own data-handling, recordkeeping, and AI-governance policies. TechNova provides the Acceptable Use Policy and the End-User Guidance document as starting points.

## (e) Data Input Restrictions

1. **Personal data of non-employees.** Do not upload corpus content that contains personal data of individuals other than Customer's employees or contractors without a documented lawful basis under applicable privacy law and, where required, appropriate notice to the affected individuals.
2. **Special categories of personal data.** Do not upload data constituting special categories under GDPR Article 9 (e.g., health data, biometric data for identification, data revealing racial or ethnic origin) unless Customer has obtained a valid legal basis and has notified TechNova in writing.
3. **Classified government information.** Do not upload information bearing a formal government classification that TechNova's hosting environment is not accredited to handle.
4. **Export-controlled technical data.** Do not upload content subject to export-control restrictions (EAR, ITAR, UK Strategic Export Control Lists, EU Dual-Use Regulation) the Service is not certified to process. Customer is responsible for classifying content before upload.
5. **Third-party confidential information.** Do not upload confidential information of third parties unless Customer is contractually permitted to process that information through cloud services and through sub-processors including OpenAI, Neon, and — where applicable — Qdrant Cloud and Vercel.

## (f) Consequences of Violation

TechNova may, in its reasonable discretion and subject to the suspension provisions of the MSA:

1. **Warn** — issue a written warning to Customer identifying the violation.
2. **Throttle** — temporarily reduce rate limits or disable specific `/api/*` endpoints (for example, suspending `/api/ingest` while preserving `/api/query`).
3. **Suspend** — suspend access to the Service in whole or in part for the Customer or specific Authorized Users.
4. **Terminate** — terminate the Agreement or an affected Order Form for material breach pursuant to Section 4 of the MSA (see Section (i) of this AUP).
5. **Refer** — refer the matter to law enforcement or regulators where TechNova reasonably believes referral is required or appropriate.

TechNova will, where reasonably practicable and not inconsistent with a legal or security imperative, notify Customer before taking any suspension or termination action, and will give Customer an opportunity to cure consistent with the MSA.

## (g) Reporting Abuse

Suspected AUP violations should be reported to:

- **Email:** [abuse@technova.example]
- **Security issues:** [security@technova.example] (PGP key available on request)
- **Trust & Safety escalation for Customer administrators:** the named Customer Success Manager listed in the Order Form, or [trust@technova.example]

Reports should include the time of the incident, the affected surface (Project A, Project B, `/knowledge-graph`, `/documents`, `/pipeline`, or a specific `/api/*` endpoint), the request correlation ID if available, and a description of the observed behavior.

## (h) Updates to this AUP

TechNova may update this AUP from time to time. Non-material updates (clarifications, typo corrections) take effect immediately upon publication. Material updates will be published at least **thirty (30) days** before they take effect, with notice delivered via the customer portal and to the primary Customer contact on file. Continued use after the effective date constitutes acceptance.

Customers may subscribe to AUP update notifications at the same channel used for Sub-processor updates (see SUBPROCESSORS.md Section (f)).

## (i) Relationship to the MSA

This AUP is incorporated into the MSA by reference. A material violation of this AUP is a material breach of the MSA and is subject to the termination-for-cause provisions of MSA Section 4.3 and the suspension provisions of MSA Section 4.4. Where the AUP and the MSA conflict, the MSA prevails with respect to fees, liability, and dispute resolution; this AUP prevails with respect to conduct.

## Revision History

| Version | Date       | Author         | Summary         |
|---------|------------|----------------|-----------------|
| 1.0     | 2026-04-16 | TechNova Legal | Initial release |
