# Data Processing Addendum (TEMPLATE)

> **TEMPLATE — not legal advice; counsel review required before execution.**

| Field            | Value                                  |
|------------------|----------------------------------------|
| Owner            | TechNova Legal / DPO                   |
| Classification   | Confidential — Customer Shareable      |
| Last Reviewed    | 2026-04-16                             |
| Next Review      | 2026-10-16                             |
| Version          | 1.0                                    |

This Data Processing Addendum (**"DPA"**) forms part of, and is incorporated into, the Master Services Agreement (the **"Agreement"**) entered into between TechNova, Inc. (**"TechNova"** or **"Processor"**) and [Customer Legal Name] (**"Customer"** or **"Controller"**). This DPA applies to the extent TechNova Processes Personal Data on behalf of Customer in connection with the Service. In the event of conflict between this DPA and the Agreement with respect to the Processing of Personal Data, this DPA prevails.

## 1. Definitions

1.1 Capitalized terms not defined in this DPA have the meanings given in the Agreement.

1.2 **"Applicable Data Protection Law"** means all laws and regulations applicable to the Processing of Personal Data under the Agreement, including (a) Regulation (EU) 2016/679 (**"GDPR"**), (b) the UK Data Protection Act 2018 and the UK GDPR, (c) the Swiss Federal Act on Data Protection (**"FADP"**), (d) the California Consumer Privacy Act as amended by the CPRA (**"CCPA"**), and (e) any other applicable privacy law.

1.3 **"Controller"**, **"Processor"**, **"Data Subject"**, **"Personal Data"**, **"Processing"**, **"Supervisory Authority"**, and **"Personal Data Breach"** have the meanings set forth in Applicable Data Protection Law.

1.4 **"Restricted Transfer"** means a transfer of Personal Data to a country that does not benefit from an adequacy decision under GDPR Article 45 (or the equivalent under UK or Swiss law).

1.5 **"SCCs"** means the Standard Contractual Clauses for the transfer of Personal Data to third countries approved by the European Commission in Decision 2021/914 of 4 June 2021.

1.6 **"Sub-processor"** means any third party engaged by TechNova to Process Personal Data on Customer's behalf, as listed in Annex III.

1.7 **"UK IDTA"** means the International Data Transfer Addendum to the EU SCCs issued by the UK Information Commissioner's Office.

## 2. Subject Matter and Duration

2.1 The subject matter of the Processing is TechNova's provision of the Service to Customer under the Agreement.

2.2 This DPA is effective on the Effective Date of the Agreement and remains in force for the term of the Agreement, plus any period during which TechNova retains Customer Personal Data pursuant to Section 15.

## 3. Nature and Purpose of Processing

3.1 TechNova Processes Personal Data for the purpose of providing a retrieval-augmented generation (**"RAG"**) platform that enables Authorized Users to query a fixed corpus of internal documents through Project A (open chat) and Project B (role-gated chat).

3.2 The Processing activities include: ingestion of corpus PDFs into embeddings, BM25 index, and the knowledge graph; storage of chat sessions and messages in Neon Postgres; transmission of queries and retrieved top-5 chunks to OpenAI for inference; storage of vectors in Qdrant (self-hosted in Customer VPC by default, or in Qdrant Cloud if elected); frontend delivery via Vercel; and one-time model downloads from Hugging Face Hub at service startup.

## 4. Categories of Personal Data

The Personal Data Processed under this DPA may include the following categories, depending on the content Customer chooses to upload and the manner in which Authorized Users interact with the Service:

| Category                               | Examples                                                                                 |
|----------------------------------------|------------------------------------------------------------------------------------------|
| Corpus content (Customer-supplied)     | Employee names, job titles, org-chart relationships, role assignments                    |
| Corpus content — RESTRICTED tier       | Compensation data, severance terms, performance review narratives, internal incident logs|
| User interaction data                  | Queries, chat session identifiers, chat message history, role claim strings              |
| Authentication / technical metadata    | IP address, user agent, timestamps, request correlation IDs                               |
| Audit log data                         | Access-denied events, retrieval method (dense / bm25 / hybrid), reranker scores, self-correction triggers |

TechNova does not intentionally Process special categories of data (GDPR Article 9). Customer is responsible for ensuring that corpus uploads do not include special-category data unless a valid legal basis exists and Customer has notified TechNova in writing.

## 5. Categories of Data Subjects

| Category                               | Description                                                                     |
|----------------------------------------|---------------------------------------------------------------------------------|
| Corpus subjects                        | Customer's employees, contractors, and other individuals named in the corpus PDFs |
| End users                              | Authorized Users who interact with the Service through Project A or Project B   |
| Third parties incidentally referenced  | Individuals named incidentally within corpus content (e.g., vendor contacts)    |

## 6. Roles of the Parties

6.1 **Controller / Processor.** With respect to Personal Data Processed under the Agreement, Customer is the Controller and TechNova is the Processor. Where Customer acts as a processor for a third party, TechNova is a sub-processor and Customer shall ensure that its agreement with the third-party controller authorizes the engagement of TechNova.

6.2 **TechNova as Controller.** TechNova acts as an independent Controller solely with respect to (a) account and billing data of Customer's authorized administrators, (b) TechNova-side service telemetry that does not contain Customer Data, and (c) security logs retained by TechNova for fraud prevention and platform integrity. Such Processing is governed by TechNova's Privacy Notice and not by this DPA.

## 7. Processor Obligations

7.1 **Documented Instructions.** TechNova shall Process Personal Data only on documented instructions from Customer, which include this DPA, the Agreement, the Documentation, and any additional written instructions agreed in writing. TechNova shall immediately inform Customer if, in its opinion, an instruction infringes Applicable Data Protection Law.

7.2 **Confidentiality.** TechNova shall ensure that persons authorized to Process Personal Data are bound by confidentiality obligations or are under an appropriate statutory obligation of confidentiality.

7.3 **Security.** TechNova shall implement and maintain the technical and organizational measures described in Annex II.

7.4 **Assistance.** Taking into account the nature of the Processing, TechNova shall assist Customer, by appropriate technical and organizational measures and insofar as possible, in fulfilling Customer's obligations to respond to Data Subject requests under Articles 12–22 GDPR and to comply with Articles 32–36 GDPR.

7.5 **Breach Notification.** TechNova shall notify Customer without undue delay, and in any event within seventy-two (72) hours, after becoming aware of a Personal Data Breach affecting Customer Personal Data.

7.6 **Audits.** TechNova shall make available to Customer all information necessary to demonstrate compliance with the obligations in Article 28 GDPR and shall allow for and contribute to audits, including inspections, conducted by Customer or a mutually agreed auditor, subject to Section 14.

7.7 **Return and Deletion.** At Customer's choice and upon termination or expiration of the Agreement, TechNova shall return or delete Customer Personal Data in accordance with Section 15.

## 8. Sub-processors

8.1 **General Authorization.** Customer grants TechNova general written authorization to engage the Sub-processors listed in Annex III. Customer may subscribe to updates at [subprocessors.technova.example/subscribe] to receive notice of proposed changes.

8.2 **Notice of Changes.** TechNova shall notify Customer at least thirty (30) days prior to authorizing a new Sub-processor or materially changing the role of an existing Sub-processor.

8.3 **Objection.** Customer may object in writing on reasonable data-protection grounds within the thirty (30)-day notice period. The Parties shall work in good faith to resolve the objection. If resolution is not possible, Customer may terminate the affected Order Form without penalty, and TechNova shall refund prepaid, unused Fees.

8.4 **Flow-Down.** TechNova shall enter into a written agreement with each Sub-processor that imposes data-protection obligations no less protective than those in this DPA and that is sufficient to meet the requirements of Article 28(4) GDPR. TechNova remains liable to Customer for each Sub-processor's performance of its data-protection obligations.

## 9. International Transfers

9.1 **Transfer Mechanisms.** Where a Restricted Transfer occurs, the Parties agree to rely on the SCCs and any supplementary measures as follows:

(a) **EU Transfers — Controller-to-Processor (Module Two).** The SCCs Module Two are incorporated by reference, with:
  - Clause 7 (docking clause): **applicable**.
  - Clause 9 (sub-processors): **Option 2 (general written authorization)**, with a 30-day prior notice period per Section 8.2 of this DPA.
  - Clause 11 (redress): the optional independent dispute resolution mechanism is **not elected**.
  - Clause 17 (governing law): laws of the **Republic of Ireland**.
  - Clause 18 (forum): courts of **Ireland**.
  - Annex I.A (parties): as set forth in the Agreement.
  - Annex I.B (description of transfer): as set forth in Annex I of this DPA.
  - Annex I.C (supervisory authority): **Irish Data Protection Commission**.
  - Annex II (technical and organizational measures): as set forth in Annex II of this DPA.
  - Annex III (sub-processors): as set forth in Annex III of this DPA.

(b) **UK Transfers.** The UK IDTA applies to Restricted Transfers subject to UK GDPR. Table references in the UK IDTA are completed by reference to the corresponding Annexes of this DPA.

(c) **Swiss Transfers.** For transfers subject to the FADP, the SCCs apply with modifications: references to GDPR are deemed to include the FADP, the Swiss Federal Data Protection and Information Commissioner is the competent supervisory authority for FADP-governed data, and references to "Member State" do not prevent Data Subjects in Switzerland from exercising rights in their place of habitual residence.

9.2 **Supplementary Measures.** TechNova shall implement supplementary technical measures including encryption in transit (TLS 1.2 or higher), encryption at rest (AES-256), and access controls described in Annex II, and shall notify Customer if it receives a legally binding request for disclosure of Personal Data from a public authority unless prohibited by law.

## 10. Security Measures — See Annex II

TechNova maintains the technical and organizational measures set forth in Annex II, which apply to all Processing of Customer Personal Data.

## 11. Data Subject Rights

11.1 Taking into account the nature of the Processing, TechNova shall assist Customer, by appropriate technical and organizational measures, in responding to requests by Data Subjects to exercise their rights under Applicable Data Protection Law, including rights of access, rectification, erasure, restriction, portability, and objection.

11.2 If a Data Subject contacts TechNova directly regarding Customer Personal Data, TechNova shall, unless legally prohibited, redirect the request to Customer without undue delay and shall not respond substantively absent Customer's documented instruction.

11.3 TechNova shall respond to Customer requests for assistance under this Section 11 within thirty (30) days, or sooner where required by Applicable Data Protection Law.

## 12. Breach Notification

12.1 TechNova shall notify Customer without undue delay, and in any event within seventy-two (72) hours, after becoming aware of a Personal Data Breach, via email to the Customer Security Contact designated in the Order Form, with a follow-up to [Customer Legal Email].

12.2 The notification shall include, to the extent known: (a) nature of the Personal Data Breach, including categories and approximate number of Data Subjects and records concerned; (b) name and contact details of TechNova's Data Protection Officer or other contact point; (c) likely consequences; (d) measures taken or proposed to address the Personal Data Breach and to mitigate its adverse effects. Where information is not available at the time of initial notification, TechNova shall provide updates without undue delay as information becomes available.

12.3 TechNova shall cooperate with Customer to investigate and remediate the Personal Data Breach and shall maintain records of the incident in accordance with Annex II.

## 13. Records of Processing

TechNova shall maintain records of Processing activities carried out on behalf of Customer in accordance with GDPR Article 30(2) and make such records available to Customer or a competent Supervisory Authority on reasonable request.

## 14. Audits

14.1 **Third-Party Reports.** TechNova shall make available to Customer, on request no more often than annually, copies of TechNova's then-current third-party audit reports, including SOC 2 Type II (once available) and any penetration-testing summary letters.

14.2 **Customer Audits.** Where third-party reports are insufficient to demonstrate compliance, Customer may, upon thirty (30) days' prior written notice and no more often than once per twelve (12) months (except where required following a Personal Data Breach or by a Supervisory Authority), conduct an audit of TechNova's data-protection practices. Audits shall be conducted during normal business hours, at Customer's expense, subject to reasonable confidentiality undertakings, and shall not unreasonably interfere with TechNova's operations.

14.3 **Supervisory Authority Audits.** TechNova shall cooperate with Supervisory Authority audits to the extent required by Applicable Data Protection Law.

## 15. Return and Deletion

15.1 Upon termination or expiration of the Agreement, Customer may, at its choice within thirty (30) days, (a) export Customer Personal Data via the mechanisms described in the Documentation, or (b) instruct TechNova in writing to delete Customer Personal Data.

15.2 Unless Customer instructs otherwise in writing within thirty (30) days of termination, TechNova shall delete Customer Personal Data from all production systems (including Qdrant collections, BM25 index files, Neon databases for chat history and corpus mirror, and knowledge graph artifacts) within thirty (30) days after the end of the export window.

15.3 Backups shall be overwritten in the ordinary course of TechNova's backup rotation, not to exceed ninety (90) days after deletion from production.

15.4 TechNova shall provide written confirmation of deletion upon Customer's request.

15.5 Notwithstanding the foregoing, TechNova may retain Personal Data to the extent required by applicable law, provided such Personal Data remains subject to the confidentiality and security obligations of this DPA.

## 16. Liability

16.1 Each Party's liability under this DPA is subject to the limitations of liability set forth in the Agreement, except to the extent limiting such liability is not permitted under Applicable Data Protection Law.

16.2 Where the SCCs apply, liability under Clause 12 of the SCCs is subject to the cap set forth in the Agreement to the maximum extent permitted by law.

## 17. Standard Contractual Clauses — Reference Section

Where a Restricted Transfer to a third country occurs, the Parties hereby enter into the SCCs Module Two (Controller-to-Processor), which are incorporated into this DPA by reference and completed as set forth in Section 9.1. The execution of the Agreement constitutes execution of the SCCs by the respective Parties. The UK IDTA and Swiss modifications are similarly incorporated where applicable.

---

## Annex I — Description of Processing

### A. List of Parties

**Data Exporter:** [Customer Legal Name], [Customer Address]. Role: Controller. Contact: [Customer Privacy Contact].

**Data Importer:** TechNova, Inc., [TechNova Address]. Role: Processor. Contact: [privacy@technova.example]. Data Protection Officer: [TechNova DPO Name].

### B. Description of Transfer

| Element                                        | Detail                                                                         |
|------------------------------------------------|--------------------------------------------------------------------------------|
| Categories of Data Subjects                    | See Section 5                                                                  |
| Categories of Personal Data                    | See Section 4                                                                  |
| Special categories                             | Not intentionally processed                                                    |
| Frequency of transfer                          | Continuous (for queries, chat history); one-off (for corpus ingestion)         |
| Nature of Processing                           | Hosting, storage, retrieval, embedding, indexing, LLM inference                |
| Purpose                                        | Provision of the Service per the Agreement                                     |
| Retention                                      | Duration of Agreement plus deletion windows per Section 15                     |
| Onward transfers to sub-processors             | Per Annex III                                                                  |

### C. Competent Supervisory Authority

For SCCs Module Two, the competent Supervisory Authority is the Irish Data Protection Commission, unless Customer's establishment or designated lead authority under GDPR Article 56 dictates otherwise.

---

## Annex II — Technical and Organizational Security Measures

TechNova has implemented and shall maintain the following measures, which are reviewed at least annually:

### A. Technical Measures

1. **Encryption in Transit.** TLS 1.2 or higher for all public-facing endpoints and inter-service communication, including (a) browser-to-Vercel, (b) Vercel-to-FastAPI backend, (c) backend-to-OpenAI (api.openai.com), (d) backend-to-Neon Postgres (TLS + SNI), (e) backend-to-Qdrant, and (f) Hugging Face Hub downloads at startup.
2. **Encryption at Rest.** AES-256 for all persistent data stores, including Neon Postgres volumes, Qdrant collection data, and backup artifacts.
3. **Role-Based Access Control (Dual Pre-Filter).** For Project B, the role-clearance filter is applied at **both** retrieval stages — Qdrant dense search filter and BM25 allowed-chunk-ID filter — before any scoring or ranking occurs. Restricted chunks never enter the scoring pool.
4. **Self-Correcting Retrieval Safeguards.** When accessible retrieval is weak but a strong restricted match exists, the system surfaces a standardized access-denied response rather than leaking restricted content.
5. **Audit Logging.** Structured logs capture access-denied events, retrieval method (dense / bm25 / hybrid), reranker scores, and self-correction triggers. Logs are retained per TechNova's logging policy.
6. **Dependency Scanning.** Automated vulnerability scanning of Python and Node dependencies on each release, with prioritized remediation of high-severity CVEs.
7. **Secrets Management.** Credentials (OpenAI API key, Neon connection string, Qdrant API key) are stored in a managed secret store and never committed to source control; `.env` files are excluded from version control.
8. **Network Segmentation.** Production workloads are isolated from development and testing environments; Qdrant self-hosted deployments reside within the Customer VPC.
9. **Backups.** Automated backups of Neon Postgres with point-in-time recovery; backup retention aligned with the deletion windows of Section 15.

### B. Organizational Measures

1. **Access Controls.** Least-privilege access to production systems; administrative access protected by multi-factor authentication; periodic access reviews at least quarterly.
2. **Background Checks.** TechNova conducts pre-employment background checks on personnel with access to production systems, to the extent permitted by applicable law.
3. **Security Training.** All personnel complete onboarding and annual security awareness training covering phishing, data handling, and incident response.
4. **Incident Response.** Documented incident-response plan with defined roles, communication tree, and post-incident review; breach-notification processes per Section 12.
5. **Change Management.** Code changes reviewed before merge; production deployments tracked and reversible.
6. **Vendor Management.** Sub-processors evaluated for security posture and contractually bound by flow-down obligations per Section 8.4.
7. **Data Minimization.** The Service transmits only the top-5 retrieved chunks and the Authorized User's query to OpenAI; full corpus content is never transmitted in a single request.

---

## Annex III — Sub-processors

For the authoritative, up-to-date list, see SUBPROCESSORS.md. The following Sub-processors are authorized as of the Last Reviewed date of this DPA:

| Sub-processor                  | Role                          | Data Processed                                               | Location                       | Transfer Mechanism                        |
|--------------------------------|-------------------------------|--------------------------------------------------------------|--------------------------------|-------------------------------------------|
| OpenAI, L.L.C.                 | LLM inference (gpt-4o-mini)   | User query + retrieved top-5 chunks                          | USA                            | SCCs Module Three (C2P via TechNova)      |
| Neon, Inc.                     | Managed Postgres              | Chat sessions, messages, corpus mirror (documents, chunks)   | Region per Order Form          | SCCs Module Two / adequacy (if EU region) |
| Qdrant Solutions GmbH          | Managed vector DB (if elected)| Vector embeddings, chunk payloads                            | Region per Order Form          | SCCs Module Two / EU adequacy             |
| Vercel, Inc.                   | Frontend hosting (Edge)       | Page HTML, non-personal static assets (no corpus content)    | Global Edge / USA              | SCCs Module Two                           |
| Hugging Face, Inc.             | Model distribution only       | None at runtime; startup model downloads only                | USA                            | SCCs Module Two (no runtime PD)           |

## Revision History

| Version | Date       | Author         | Summary         |
|---------|------------|----------------|-----------------|
| 1.0     | 2026-04-16 | TechNova Legal | Initial release |
