# Master Services Agreement (TEMPLATE)

> **TEMPLATE — not legal advice; counsel review required before execution.**

| Field            | Value                                  |
|------------------|----------------------------------------|
| Owner            | TechNova Legal                         |
| Classification   | Confidential — Customer Shareable      |
| Last Reviewed    | 2026-04-16                             |
| Next Review      | 2026-10-16                             |
| Version          | 1.0                                    |

This Master Services Agreement (this **"Agreement"**) is entered into as of [Effective Date] (the **"Effective Date"**) by and between TechNova, Inc., a [State of Incorporation] corporation with its principal place of business at [TechNova Address] (**"TechNova"**), and [Customer Legal Name], a [Customer Entity Type] with its principal place of business at [Customer Address] (**"Customer"**). TechNova and Customer are each a **"Party"** and collectively the **"Parties"**.

## 1. Definitions

Capitalized terms used in this Agreement have the meanings set forth below or as defined elsewhere in this Agreement.

1.1 **"Affiliate"** means, with respect to a Party, any entity that directly or indirectly controls, is controlled by, or is under common control with such Party.

1.2 **"Authorized User"** means an employee or contractor of Customer or a Customer Affiliate who is authorized by Customer to access the Service, subject to the access controls described in Exhibit A and the Acceptable Use Policy.

1.3 **"Customer Data"** means all data, content, and information, including the eleven (11) fixed corpus PDF documents, chat history, queries, role claims, and derived artifacts (embeddings, chunks, BM25 index, knowledge graph entities), that Customer or its Authorized Users submit to, or that is generated on behalf of Customer by, the Service.

1.4 **"Confidential Information"** means non-public information disclosed by one Party ("Discloser") to the other ("Recipient"), whether orally or in writing, that is designated as confidential or that reasonably should be understood to be confidential given the nature of the information and the circumstances of disclosure. Confidential Information includes the terms of this Agreement, Customer Data, and TechNova's non-public technical documentation and benchmarks.

1.5 **"Documentation"** means TechNova's then-current technical documentation for the Service, including the architecture reference, API contract, and operations runbooks made available at [docs.technova.example] or through the customer portal.

1.6 **"DPA"** means the Data Processing Addendum attached as Exhibit D (referencing the TechNova DPA Template).

1.7 **"Order Form"** means an ordering document executed by the Parties referencing this Agreement that specifies the Service tier, Subscription Term, fees, and any deployment parameters (e.g., Neon region, Qdrant deployment mode).

1.8 **"Output"** means the textual responses, citations, retrieved chunk identifiers, retrieval method indicators, and knowledge graph artifacts returned by the Service in response to Customer queries.

1.9 **"Service"** means the TechNova RAG platform hosted and provided by TechNova, comprising (a) the retrieval-augmented generation backend (FastAPI), (b) the Next.js frontend surfaces including Project A (open chat), Project B (role-gated chat), the /documents surface, the /pipeline visualization surface, and the 3D knowledge graph surface, (c) the /api/* endpoints described in the API Contract, and (d) any updates, enhancements, and related materials provided by TechNova.

1.10 **"Subscription Term"** means the period set forth in the applicable Order Form during which Customer is entitled to access and use the Service.

1.11 **"Sub-processor"** means any third party engaged by TechNova to process Customer Data in connection with the Service, as listed in Exhibit E (Sub-processor List).

1.12 **"SLA"** means the Service Level Agreement attached as Exhibit C.

## 2. Services

2.1 **License Grant.** Subject to Customer's payment of fees and compliance with this Agreement, TechNova grants Customer a non-exclusive, non-transferable, non-sublicensable, worldwide right during the Subscription Term to access and use the Service solely for Customer's internal business purposes and solely in accordance with the Documentation and applicable Order Form.

2.2 **Scope.** Access is limited to the number of Authorized Users, API call volume, corpus size (default: eleven (11) fixed PDFs per deployment), and deployment mode specified in the Order Form. Role-gated access in Project B is governed by the role-clearance matrix maintained by Customer through its authorized administrator.

2.3 **Subscriptions.** The Service is provided on a subscription basis. Unless otherwise specified in the Order Form, the initial Subscription Term commences on the Effective Date.

2.4 **Restrictions.** Customer shall not, and shall not permit any third party to: (a) modify, reverse engineer, decompile, or disassemble the Service or any of its components; (b) use the Service to develop a competing product or service; (c) resell, sublicense, time-share, or use the Service for the benefit of any third party; (d) attempt to bypass or disable the role-based access controls, self-correcting retrieval safeguards, or audit logging; or (e) attempt to extract training data from the underlying foundation models accessed via the Service.

2.5 **Support.** TechNova will provide support for the Service in accordance with the Support SLA and the tier elected in the Order Form.

## 3. Fees and Payment

3.1 **Fees.** Customer shall pay the fees set forth in the applicable Order Form and in Exhibit B (collectively, **"Fees"**). Fees are exclusive of taxes and payable in the currency specified in the Order Form.

3.2 **Invoicing.** Unless otherwise specified, TechNova will invoice Customer annually in advance for subscription Fees and monthly in arrears for any usage-based charges (e.g., OpenAI inference overage above the bundled quota).

3.3 **Payment Terms.** Customer shall pay all invoiced amounts within thirty (30) days of the invoice date (**"Net 30"**), via wire transfer or ACH to the account designated by TechNova.

3.4 **Late Payment.** Undisputed amounts not paid when due shall accrue interest at the lesser of 1.5% per month or the maximum rate permitted by law. TechNova may suspend the Service pursuant to Section 4.4 for non-payment continuing more than thirty (30) days past due, provided TechNova has given at least ten (10) business days' prior written notice.

3.5 **Taxes.** Fees are exclusive of all taxes, levies, and duties other than taxes on TechNova's net income. Customer is responsible for all applicable sales, use, VAT, GST, and withholding taxes.

3.6 **Disputes.** Customer must provide written notice of any invoice dispute within fifteen (15) days of receipt. Undisputed portions of invoices remain payable by the Net 30 due date.

## 4. Term and Termination

4.1 **Initial Term.** This Agreement begins on the Effective Date and continues until all Order Forms have expired or been terminated, unless earlier terminated in accordance with this Section 4.

4.2 **Renewal.** Unless otherwise specified in the Order Form, each Subscription Term will automatically renew for successive twelve (12)-month periods unless either Party gives written notice of non-renewal at least sixty (60) days prior to the end of the then-current Subscription Term.

4.3 **Termination for Cause.** Either Party may terminate this Agreement or any Order Form upon written notice if the other Party (a) materially breaches this Agreement and fails to cure such breach within thirty (30) days after written notice (ten (10) days for payment breaches), or (b) becomes insolvent, files for bankruptcy, or undergoes a general assignment for the benefit of creditors.

4.4 **Suspension.** TechNova may suspend access to the Service, in whole or in part, if (a) Customer's use materially threatens the security, integrity, or availability of the Service or other customers, (b) Customer is in breach of the Acceptable Use Policy, or (c) Customer is more than thirty (30) days past due on undisputed Fees. TechNova will, where reasonably practicable, give Customer prior notice of suspension.

4.5 **Effect of Termination.** Upon termination or expiration: (a) Customer's access to the Service ceases; (b) each Party shall return or destroy the other Party's Confidential Information, subject to customary backup retention; (c) Customer may export Customer Data via the export mechanisms described in the Documentation for a period of thirty (30) days following termination; and (d) TechNova will delete Customer Data, including the corpus mirror, embeddings, BM25 index, chat history, and knowledge graph artifacts, within thirty (30) days after the end of the export window, except as otherwise required by law.

4.6 **Survival.** Sections 1, 3 (for amounts accrued prior to termination), 4.5, 4.6, 5.3, 6, 7, 8, 9, 10 (to the extent applicable to Customer Data retained during wind-down), 13, 14, and 15 survive termination.

## 5. Warranties

5.1 **Mutual Warranties.** Each Party represents and warrants that (a) it is duly organized and validly existing, (b) it has full power and authority to enter into this Agreement, and (c) its execution and performance of this Agreement will not violate any other agreement to which it is a party.

5.2 **TechNova Service Warranty.** TechNova warrants that, during the Subscription Term, the Service will perform in all material respects in accordance with the Documentation. Customer's sole remedy and TechNova's sole liability for breach of this warranty is that TechNova will use commercially reasonable efforts to correct the non-conformity or, if correction is not commercially reasonable, terminate the affected Order Form and refund any prepaid, unused Fees.

5.3 **Customer Warranties.** Customer represents and warrants that (a) it has obtained all rights, consents, and legal bases necessary to upload, process, and grant TechNova the rights to process the corpus PDFs and any personal data contained therein; (b) Customer's use of the Service complies with all applicable laws; and (c) Customer will maintain an accurate role-clearance mapping in Project B and will not assert a role claim that exceeds the Authorized User's actual authorization.

5.4 **Disclaimer.** EXCEPT AS EXPRESSLY SET FORTH IN THIS SECTION 5, THE SERVICE IS PROVIDED **"AS IS"** AND TECHNOVA DISCLAIMS ALL OTHER WARRANTIES, EXPRESS OR IMPLIED, INCLUDING WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT, AND ANY WARRANTY THAT OUTPUT WILL BE ACCURATE, COMPLETE, OR SUITABLE FOR ANY SPECIFIC PURPOSE. CUSTOMER ACKNOWLEDGES THAT THE SERVICE USES PROBABILISTIC LARGE LANGUAGE MODELS AND THAT OUTPUT MAY CONTAIN ERRORS OR OMISSIONS.

## 6. Indemnification

6.1 **TechNova IP Indemnity.** TechNova shall defend Customer against any third-party claim alleging that Customer's authorized use of the Service infringes such third party's patent, copyright, trademark, or misappropriates a trade secret (an **"IP Claim"**), and shall indemnify Customer against damages and costs (including reasonable attorneys' fees) finally awarded against Customer by a court of competent jurisdiction or agreed in settlement by TechNova. TechNova's obligations do not apply to claims arising from (i) Customer Data, (ii) modifications to the Service not made by TechNova, (iii) combination of the Service with non-TechNova products where the Service alone would not infringe, or (iv) use of the Service not in accordance with the Documentation or Agreement.

6.2 **Remedies.** If the Service is or, in TechNova's opinion, is likely to become the subject of an IP Claim, TechNova may, at its option: (a) procure the right to continue using the Service, (b) modify the Service to be non-infringing, or (c) terminate the affected Order Form and refund any prepaid, unused Fees.

6.3 **Customer Indemnity.** Customer shall defend TechNova against any third-party claim arising out of or relating to (a) Customer Data, including any claim that Customer Data infringes third-party rights or violates applicable law, (b) Customer's violation of the Acceptable Use Policy, or (c) Customer's assertion of an inaccurate role claim resulting in unauthorized disclosure.

6.4 **Procedure.** The indemnified Party shall promptly notify the indemnifying Party of the claim, grant sole control of the defense and settlement (provided no settlement may impose non-monetary obligations on the indemnified Party without its consent), and provide reasonable cooperation at the indemnifying Party's expense.

## 7. Limitation of Liability

7.1 **Exclusion of Damages.** EXCEPT FOR THE EXCLUDED CLAIMS IN SECTION 7.3, NEITHER PARTY SHALL BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR FOR LOSS OF PROFITS, REVENUE, DATA, OR BUSINESS OPPORTUNITY, ARISING OUT OF OR RELATED TO THIS AGREEMENT, WHETHER IN CONTRACT, TORT, OR OTHERWISE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

7.2 **Cap on Liability.** EXCEPT FOR THE EXCLUDED CLAIMS IN SECTION 7.3, EACH PARTY'S AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT SHALL NOT EXCEED THE FEES PAID OR PAYABLE BY CUSTOMER TO TECHNOVA UNDER THE APPLICABLE ORDER FORM IN THE TWELVE (12) MONTHS IMMEDIATELY PRECEDING THE EVENT GIVING RISE TO THE CLAIM.

7.3 **Excluded Claims.** The limitations in Sections 7.1 and 7.2 do not apply to (a) breach of Section 8 (Confidentiality), (b) indemnification obligations under Section 6, (c) Customer's obligation to pay undisputed Fees, (d) either Party's gross negligence or willful misconduct, or (e) liability that cannot be limited under applicable law.

## 8. Confidentiality

8.1 **Obligation.** The Recipient shall (a) use Confidential Information only to perform its obligations or exercise its rights under this Agreement, (b) protect Confidential Information with the same degree of care it uses for its own confidential information of similar importance (and no less than reasonable care), and (c) disclose Confidential Information only to its Representatives who have a need to know and who are bound by confidentiality obligations at least as protective as those herein.

8.2 **Exclusions.** Confidential Information does not include information that (a) is or becomes publicly available without breach of this Agreement, (b) was known to Recipient prior to disclosure, (c) is rightfully received from a third party without restriction, or (d) is independently developed without use of the Discloser's Confidential Information.

8.3 **Compelled Disclosure.** If Recipient is legally compelled to disclose Confidential Information, it shall, where permitted, provide prompt notice to Discloser and reasonably cooperate with any effort by Discloser to seek a protective order.

## 9. Intellectual Property

9.1 **TechNova IP.** As between the Parties, TechNova and its licensors own all right, title, and interest in and to the Service, including the retrieval pipeline, the hybrid retriever (RRF fusion algorithm, cross-encoder reranking logic), the self-correcting retrieve mechanism, the knowledge graph construction methodology, and all Documentation. No rights are granted to Customer except as expressly set forth in this Agreement.

9.2 **Customer Data Ownership.** As between the Parties, Customer retains all right, title, and interest in and to Customer Data. Customer grants TechNova a limited, non-exclusive, worldwide, royalty-free license to host, process, transmit, and display Customer Data solely as necessary to provide the Service and perform TechNova's obligations under this Agreement.

9.3 **Outputs.** Subject to Customer's compliance with this Agreement and payment of Fees, as between the Parties, Customer owns the Output. TechNova hereby assigns, and shall cause its personnel to assign, to Customer all right, title, and interest TechNova may have in the Output. Customer acknowledges that Output is generated probabilistically and may be similar or identical to Output generated for other customers from similar queries.

9.4 **Feedback.** Customer may, but is not required to, provide TechNova with suggestions, enhancement requests, or other feedback regarding the Service (**"Feedback"**). Customer grants TechNova a perpetual, irrevocable, worldwide, royalty-free, sublicensable license to use Feedback for any purpose, including improving the Service, without any attribution or compensation to Customer.

9.5 **No Model Training on Customer Data.** TechNova shall not use Customer Data to train, fine-tune, or otherwise improve any foundation model, retrieval model, or reranker model. TechNova's contractual arrangements with OpenAI incorporate OpenAI's default API policy that API inputs and outputs are not used to train OpenAI models.

## 10. Data Protection

10.1 The DPA attached as Exhibit D is incorporated into this Agreement by reference and governs TechNova's processing of personal data on Customer's behalf.

10.2 Customer acknowledges that personal data may be processed by the Sub-processors listed in Exhibit E, including OpenAI (LLM inference), Neon (managed Postgres for chat history and corpus mirror), Qdrant Solutions GmbH (if Qdrant Cloud option is selected), Vercel (frontend hosting), and Hugging Face (model distribution at startup only, no runtime Customer Data).

10.3 In the event of conflict between the body of this Agreement and the DPA with respect to personal data processing, the DPA prevails.

## 11. Insurance

During the Subscription Term, TechNova shall maintain, at its own expense, insurance coverage no less than:

| Coverage                                   | Minimum Limit                         |
|--------------------------------------------|---------------------------------------|
| Commercial General Liability               | USD 2,000,000 per occurrence          |
| Technology Errors & Omissions / Cyber      | USD 5,000,000 per claim and aggregate |
| Workers' Compensation                      | As required by applicable law         |
| Employer's Liability                       | USD 1,000,000                         |

TechNova shall furnish certificates of insurance upon Customer's reasonable written request, no more often than annually.

## 12. Compliance

12.1 **Export Controls.** Each Party shall comply with all applicable export, re-export, and import laws, including the U.S. Export Administration Regulations and sanctions administered by the U.S. Office of Foreign Assets Control. Customer shall not export or re-export the Service, or any Customer Data containing technical data subject to export controls, to any person or destination prohibited by applicable law.

12.2 **Sanctions.** Each Party represents that it is not, and is not owned or controlled by any person or entity that is, the subject of comprehensive economic sanctions administered by the United States, the United Nations, the European Union, or the United Kingdom.

12.3 **Anti-Corruption.** Each Party shall comply with the U.S. Foreign Corrupt Practices Act, the UK Bribery Act 2010, and all other applicable anti-corruption laws.

## 13. Notices

All notices required under this Agreement shall be in writing and delivered to the addresses set forth in the preamble (for legal notices) or the Order Form (for operational notices), by (a) personal delivery, (b) certified or registered mail, return receipt requested, (c) overnight courier with tracking, or (d) email to [legal@technova.example] (for TechNova) and [Customer Legal Email] (for Customer), with confirmation of delivery. Notices are effective upon receipt.

## 14. Governing Law and Dispute Resolution

14.1 **Governing Law.** This Agreement is governed by the laws of the [Jurisdiction — e.g., State of Delaware, USA], without regard to its conflict-of-laws rules. The U.N. Convention on Contracts for the International Sale of Goods does not apply.

14.2 **Dispute Resolution.** The Parties shall first attempt to resolve any dispute through good-faith negotiation between executives with authority to settle. If the dispute is not resolved within thirty (30) days, it shall be submitted to binding arbitration administered by [AAA / ICC / JAMS] under its then-current rules, seated in [City, Jurisdiction], and conducted in English. Each Party retains the right to seek injunctive or other equitable relief in any court of competent jurisdiction to protect its intellectual property or confidential information.

14.3 **Class Action Waiver.** Each Party waives any right to participate in a class, collective, or representative action.

## 15. General Provisions

15.1 **Entire Agreement.** This Agreement, including all Exhibits and Order Forms, constitutes the entire agreement between the Parties regarding the subject matter and supersedes all prior or contemporaneous agreements, written or oral.

15.2 **Amendments.** No amendment is binding unless in writing signed by authorized representatives of both Parties.

15.3 **Severability.** If any provision is held unenforceable, the remaining provisions remain in full force.

15.4 **Assignment.** Neither Party may assign this Agreement without the other's prior written consent, except that either Party may assign without consent to a successor in connection with a merger, acquisition, or sale of all or substantially all of its assets, provided the assignee assumes all obligations hereunder.

15.5 **Force Majeure.** Neither Party is liable for delay or failure to perform due to causes beyond its reasonable control, including acts of God, war, terrorism, epidemic or pandemic conditions, civil unrest, labor disputes, or outages of telecommunications or third-party cloud infrastructure, provided the affected Party uses commercially reasonable efforts to mitigate.

15.6 **Independent Contractors.** The Parties are independent contractors; nothing creates any partnership, joint venture, agency, or employment relationship.

15.7 **No Third-Party Beneficiaries.** Except for the indemnified parties under Section 6, there are no third-party beneficiaries.

15.8 **Counterparts; Electronic Signature.** This Agreement may be executed in counterparts (including via electronic signature), each of which is an original and together constitute one instrument.

## Exhibits

### Exhibit A — Service Description

The Service comprises: (a) the TechNova RAG hybrid retrieval pipeline (dense BGE embeddings in Qdrant + BM25 with Reciprocal Rank Fusion at k=60, cross-encoder reranking, top-5 selection, gpt-4o-mini generation); (b) Project A (open chat over the eleven (11) fixed corpus PDFs); (c) Project B (role-gated chat, with dual pre-filter enforcement at dense and BM25 stages, self-correcting retrieval, role clearance matrix managed by Customer); (d) the /documents corpus browser; (e) the /pipeline visualization; (f) the 3D knowledge graph surface; and (g) all /api/* endpoints specified in the API Contract, including /api/ingest, /api/query, /api/status, and /api/graph. Deployment options: (i) TechNova-hosted SaaS; or (ii) customer-hosted with Qdrant self-hosted in Customer VPC.

### Exhibit B — Fees

As specified in the applicable Order Form. Fee components typically include: (i) platform subscription by tier (Business, Enterprise, Enterprise+); (ii) bundled OpenAI inference quota with overage pricing; (iii) optional Qdrant Cloud uplift; (iv) optional Neon region uplift (e.g., eu-central-1, ap-southeast-1); (v) professional services for onboarding and corpus ingestion.

### Exhibit C — Service Level Agreement

Refer to the TechNova SLA/SLO document (current version: SLA_SLO.md) as attached or referenced in the Order Form. Service credits and availability targets apply per the terms of that document.

### Exhibit D — Data Processing Addendum

Refer to the TechNova DPA Template (current version: DPA_TEMPLATE.md). The DPA is incorporated into this Agreement by reference.

### Exhibit E — Sub-processor List

Refer to the TechNova Sub-processors document (current version: SUBPROCESSORS.md) listing OpenAI L.L.C., Neon Inc., Qdrant Solutions GmbH (if applicable), Vercel Inc., and Hugging Face Inc. Changes governed by Section 8 of the DPA.

## Signature Block

**TechNova, Inc.**

By: _________________________________
Name: [TechNova Signatory]
Title: [Title]
Date: _______________________________

**[Customer Legal Name]**

By: _________________________________
Name: [Customer Signatory]
Title: [Title]
Date: _______________________________

## Revision History

| Version | Date       | Author         | Summary         |
|---------|------------|----------------|-----------------|
| 1.0     | 2026-04-16 | TechNova Legal | Initial release |
