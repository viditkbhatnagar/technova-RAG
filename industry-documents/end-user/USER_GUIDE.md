# TechNova RAG User Guide

Audience: TechNova employees, managers, and administrators using the chat and knowledge-graph surfaces | Version: 1.0 | Last Updated: 2026-04-16

This guide shows you how to use TechNova RAG to find answers inside TechNova's internal documents. You do not need to know anything about machine learning to follow it. If you can use a search box, you can use this tool.

## 1. What TechNova RAG is

TechNova RAG is a search-and-answer tool that reads your internal PDFs and answers your questions in plain English, with citations back to the source.

The corpus is fixed at 11 documents — the HR handbook, the IT policy, the platform architecture, the on-call runbook, the training compliance doc, the Q4 financial report, the 2026 product roadmap, the vendor contracts, the salary structure, the board minutes, and the security incident report. TechNova RAG does not read the public internet, does not read your email, and does not read any document that isn't in this corpus.

When you ask a question, the system finds the most relevant passages across the documents you're allowed to see, passes them to a language model, and gives you an answer grounded in those passages. Every answer shows you exactly which chunks it came from so you can verify before acting.

## 2. Getting started

Open the app at your TechNova URL (internally, `http://localhost:3000` in dev). You land on a short explainer page with two entry points:

- **Project A — Open chat.** Use this for everyday questions over documents available in the open mode. It is the right choice 80% of the time.
- **Project B — Secure chat.** Use this when your question touches confidential or restricted material and you need the system to scope answers to your role.

There is also a **Knowledge Graph** link in the nav for visual exploration of how the documents connect, and — if your admin has enabled it — a **Documents** browser for reading source PDFs chunk-by-chunk.

Pick Project A the first time. You'll recognize when you need Project B.

## 3. Asking good questions

The quality of your answer depends much more on how you ask than on anything else. Three rules cover most of what matters:

### 3.1 Be specific. Terseness is not efficiency.

One-word queries ("PTO?", "budget?") force the retriever to guess at your intent and usually surface generic material. Full-sentence queries let the retriever match precise passages.

| Low-signal | High-signal |
|---|---|
| "PTO?" | "What is the PTO policy for a new joiner in the London office?" |
| "incidents" | "What was the root cause of the March 2026 security incident?" |
| "salary" | "What is the salary band for a Staff Engineer in the US?" |
| "laptop" | "How do I request a replacement laptop under the IT asset policy?" |

### 3.2 Include the context the retriever can't guess

If you care about a region, role, quarter, or document type, say so. The retriever cannot read your mind, but it can filter on what you type.

### 3.3 Ask one thing at a time, then follow up

Compound questions split the retriever's attention. Instead of "What's the PTO policy and how do I request a new laptop and who approves travel?", ask them in sequence. Use the chat history to branch into sub-questions; the system keeps recent turns in context.

If an answer feels off, reply with a clarification ("I meant the London office, not New York") rather than starting a new thread. The retriever will re-query with the refined intent.

## 4. Reading an answer

Every answer has three parts:

1. **The generated answer** — a natural-language paragraph or list.
2. **Inline citations** — numbered references such as `[1]` that map to the sources panel.
3. **Retrieved sources** — a scrollable panel on the right showing each chunk the model saw, with its document name, page number, and a `hybrid` / `dense` / `bm25` tag that indicates which retrieval path found it.

Hover or click a citation to jump to the source chunk. If the answer paraphrases, open the source and read the original — for anything consequential, the source is ground truth, not the summary.

A few conventions to know:

- `hybrid` means both dense embeddings and BM25 keyword search surfaced this chunk. These are usually the strongest citations.
- `dense` means only the semantic embedder found it — good for paraphrased or conceptually adjacent content.
- `bm25` means only keyword search found it — good for exact phrases, IDs, or rare terminology.
- The panel scrolls. If you see fewer than five chunks, scroll down; some environments clip the list.

## 5. When you see an access-denied message

Occasionally you will ask a question and get a reply like:

> "This question matches content that requires a higher clearance level than your current role. Please contact your department head to request access."

This is not a bug. It means the system found strong matches in a document class your role can't see (for example, an employee asking about board minutes). The system does not show you the content, and it does not show you which document matched — only that a match exists that you cannot access.

If you legitimately need the answer:

1. Identify the business reason (audit, compliance ask, your manager requested it).
2. Ask your department head or the document owner for temporary elevated access.
3. An administrator can either reclassify the document or grant your role a higher clearance — both are tracked through the governance workflow.

Do not try to rephrase your question to evade the filter. Restricted content is filtered at both retrieval stages; no amount of rewording will bypass it.

## 6. Project A vs Project B

| | Project A (Open) | Project B (Secure) |
|---|---|---|
| Audience | Everyone | Everyone, with role selector |
| Scope | Documents available in open mode | Documents at or below your clearance |
| Role selector | No | Yes — employee / manager / admin |
| Use for | General questions, training, runbook lookups | Salary, roadmap, board, incidents |
| Access-denied behaviour | Not applicable (open scope) | Enforced with role pre-filter |

Rule of thumb: **if your question touches money, people, or strategy, use Project B.** Technical and procedural questions are fine in Project A.

A few scenarios:

- *"What's the escalation path for a Sev-1 incident?"* → Project A (it's in the on-call runbook, INTERNAL).
- *"What's the total Q4 revenue?"* → Project B as manager (it's in the Q4 Financial Report, CONFIDENTIAL).
- *"What was discussed in the December board meeting?"* → Project B as admin (RESTRICTED).
- *"How do I enrol in compliance training?"* → Project A (PUBLIC).

## 7. Chat history

Your conversations appear in the sidebar if your admin has enabled history (it requires a Postgres connection server-side).

- Click a past session to resume it. The system re-hydrates the full transcript, including citations.
- Click the delete icon to remove a session permanently. Deletion is immediate and cannot be undone — use this for sensitive exploratory questions you do not want persisted.
- Session titles are generated from your first turn. You can rename them from the kebab menu.

Your history is visible to you only. Administrators can delete any session for retention or GDPR reasons, but they do not see transcripts through the user-facing UI.

## 8. Knowledge Graph

Open `/knowledge-graph` to see a 3D force-directed map of the entities (people, products, teams, vendors, policies) the system extracted from the corpus, with edges drawn from chunk co-occurrence.

What you can do:

- **Rotate** by click-dragging the background.
- **Zoom** with scroll or pinch.
- **Click a node** to focus on it and highlight its neighbours. The side panel lists the chunks this entity appears in.
- **Click an edge** to see the relationship: the two entities, the document they co-occurred in, and the chunk text that justifies the link.

The graph is great for discovery questions you can't phrase as a search:

- *"What does the 2026 roadmap touch?"* — click the **Product Roadmap** node; explore the highlighted neighbours.
- *"Which teams show up in the on-call runbook?"* — click the runbook node; the team entities light up.
- *"Is there an overlap between vendor contracts and the security incident?"* — look for a shared neighbour.

The graph is built from the same ingest that powers chat, so if a document is not in the corpus, it is not in the graph.

## 9. What not to do

A few guardrails that protect you and the organisation:

- **Don't paste PII that doesn't belong here.** Customer data, payment details, or personal identifiers should not be sent through this tool unless they already exist in the corpus. The system does not need them to answer policy or procedural questions.
- **Don't try to bypass access controls.** Rephrasing a question to coax out restricted content is both ineffective and a policy violation.
- **Don't rely on answers for adverse decisions.** Legal, medical, HR terminations, disciplinary actions, and performance reviews must be grounded in the source documents and reviewed by a human. The tool is a research aid, not a decision-maker.
- **Don't share your session links externally.** Sessions contain your queries and the answers you received, including any citations.

## 10. Limitations

Be honest with yourself about what the tool can and cannot do.

- **English only.** Queries and documents are assumed English. Mixed-language content may retrieve but generate awkwardly.
- **Fixed corpus.** The 11 PDFs defined by your deployment are the entire universe. The tool does not crawl the web, ingest Slack, or read Confluence.
- **Answers can be wrong.** Retrieval can miss; the LLM can paraphrase sloppily; a chunk can be cited without being the best answer. Always verify anything that matters against the source.
- **Stale data.** The corpus is only as fresh as the last ingest. If HR updated the PTO policy yesterday and the admin hasn't re-ingested, you will get yesterday's answer. Check the document's updated-at in `/documents` if you're unsure.
- **No external actions.** The tool answers questions. It does not file tickets, book time off, order laptops, or change records in other systems.
- **Numeric reasoning is shallow.** If the answer requires arithmetic across tables, treat the result as a starting point and check the math against the source.

## 11. Giving feedback

Bad answers are the single most useful thing you can report. Every correction improves the tool for everyone.

To report an issue, include:

1. **The query, verbatim.**
2. **The role you selected** (if Project B).
3. **A screenshot of the answer and the sources panel.**
4. **What the correct answer should have been, with a pointer to the source chunk** if you know it.

Send to your TechNova RAG admin contact or file a ticket in the internal tracker. The admin team triages feedback weekly: bad retrievals become regression queries in the golden-set, classification disputes go to data governance, and hallucinations become generator-prompt adjustments.

## Revision history

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Documentation | Initial release |
