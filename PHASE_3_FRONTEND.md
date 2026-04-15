# PHASE_3_FRONTEND.md — Next.js Frontend (3 Pages)

> **Claude Code Chat 3.** Read MASTER_CONTEXT.md, CONVENTIONS.md, and API_CONTRACT.md first.
> **Depends on:** Phase 1 backend must be running. Phase 2 (graph) should be done for the graph page, but the chat pages work independently.

---

## Objective

Build the complete Next.js frontend with three pages accessible from a landing page:
1. **Landing Page** — Three cards to navigate to each feature
2. **Project A** — Open RAG chat interface (no roles)
3. **Project B** — Secure RAG chat with role selection
4. **Knowledge Graph** — Interactive 3D visualization

---

## Setup

```bash
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir=false --import-alias="@/*"
cd frontend
npx shadcn@latest init
npx shadcn@latest add button card input badge separator scroll-area select dialog
npm install react-force-graph-3d three @types/three
```

**`frontend/.env.local`:**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Page-by-Page Specification

### Landing Page (`app/page.tsx`)

**Layout:** Full-screen centered layout with project title and three cards in a row (responsive: stacks on mobile).

**Content:**
- Header: "TechNova RAG Platform" + brief subtitle
- Three cards, each with:
  - Icon/emoji
  - Title
  - 2-line description
  - "Explore →" button linking to the page

**Card 1 — Project A:**
- Title: "Open RAG"
- Description: "Chat with all 11 TechNova documents. Hybrid retrieval with dense + BM25 search, RRF fusion, and cross-encoder reranking."
- Route: `/project-a`

**Card 2 — Project B:**
- Title: "Secure RAG"
- Description: "Role-based document access. Employees, managers, and admins see different answers based on security clearance."
- Route: `/project-b`

**Card 3 — Knowledge Graph:**
- Title: "Knowledge Graph"
- Description: "Explore entities, relationships, and connections across all documents in an interactive 3D visualization."
- Route: `/knowledge-graph`

**Design direction:**
- Dark theme preferred (dark background, light text)
- Clean, minimal, professional
- Tailwind + shadcn/ui cards
- Subtle gradient or glass effect on cards
- No stock images, no illustrations — typography and spacing do the work

---

### Project A Page (`app/project-a/page.tsx`)

**Layout:** Two-panel layout.
- Left (60%): Chat interface
- Right (40%): Source panel showing retrieved chunks

**Chat Interface (`components/ChatInterface.tsx`):**
- Message history (user messages right-aligned, assistant left-aligned)
- Input bar at bottom with send button
- Loading state with animated dots
- Messages render markdown (for formatted LLM responses)
- Props: `mode: "open" | "secure"`, optional `role`

**On submit:**
1. Add user message to chat history
2. Show loading state
3. Call `POST /api/query` with `{"query": "...", "mode": "open"}`
4. Display answer in chat
5. Update source panel with retrieved chunks

**Source Panel (`components/SourcePanel.tsx`):**
- List of retrieved chunks, each showing:
  - Document name (badge)
  - Page number
  - Security level (color-coded badge: green=PUBLIC, blue=INTERNAL, orange=CONFIDENTIAL, red=RESTRICTED)
  - Relevance score (progress bar or number)
  - Retrieval method badge (Dense / BM25 / Hybrid)
  - Expandable chunk text (truncated by default, click to expand)
- Retrieval stats at top: total results, avg score, retrieval time

**Back button** at top linking to landing page.

---

### Project B Page (`app/project-b/page.tsx`)

**Layout:** Same two-panel layout as Project A, but with a role selector at the top.

**Role Selector (`components/RoleSelector.tsx`):**
- Three buttons or a dropdown: Employee / Manager / Admin
- Show clearance level and accessible doc count:
  - Employee: "Clearance Level 1 · 5 documents"
  - Manager: "Clearance Level 2 · 8 documents"
  - Admin: "Clearance Level 3 · 11 documents"
- Role must be selected before chatting (disable chat input until role selected)
- Changing role clears chat history (different context)

**Access Denied UX (`components/AccessDenied.tsx`):**
When `access_denied: true` in the API response:
- Show the LLM's access-denied message
- Show a warning banner: "⚠️ Relevant information exists in {count} restricted document(s)"
- Suggest: "Contact your department head for elevated access"
- Visually distinct from normal responses (yellow/amber warning styling)

**On submit:**
1. Same as Project A, but include `mode: "secure"` and `role: selectedRole`
2. If response has `access_denied: true`, show AccessDenied component
3. Otherwise, show normal answer + sources

**Source panel** is identical to Project A but security badges are more prominent (since this page is about access control).

---

### Knowledge Graph Page (`app/knowledge-graph/page.tsx`)

**Layout:** Full-screen 3D graph with a floating info panel.

**Graph Viewer (`components/GraphViewer.tsx`):**
- Uses `react-force-graph-3d` (or `ForceGraph3D` component)
- Fetches data from `GET /api/graph` on mount
- Loading state while graph loads

**Node styling:**
- **Document nodes:** Large (size 15), colored by security level:
  - PUBLIC: green
  - INTERNAL: blue
  - CONFIDENTIAL: orange
  - RESTRICTED: red
- **Chunk nodes:** Medium (size 5), gray, slightly transparent
- **Entity nodes:** Small (size 8), colored by entity type:
  - PERSON: purple
  - POLICY: teal
  - AMOUNT/MONEY: gold
  - DATE/DURATION: cyan
  - DEPARTMENT/ORG: pink
  - ROLE_LEVEL: white

**Edge styling:**
- contains (doc→chunk): thin, gray, low opacity
- mentions (chunk→entity): thin, dashed
- relationship (entity→entity): thicker, colored, with label on hover

**Interactions:**
- Click node → floating info panel shows node details (name, type, text preview for chunks, metadata)
- Hover node → highlight connected edges
- Zoom, rotate, pan (built into react-force-graph-3d)
- Optional: filter panel to show/hide node types or security levels

**Info Panel (floating, top-right):**
- Appears when a node is clicked
- Shows: node name, type, metadata
- For chunks: shows full text + parent doc
- For entities: shows mention count + which docs contain it
- For documents: shows page count, security level, domain
- Close button to dismiss

**Stats bar (bottom):**
- Total documents, chunks, entities, relationships
- From `stats` in the API response

---

## Shared Components

### `lib/api.ts`
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface QueryRequest {
  query: string;
  mode: "open" | "secure";
  role?: "employee" | "manager" | "admin";
  top_k?: number;
}

export interface ChunkResult {
  chunk_id: string;
  text: string;
  score: number;
  doc_name: string;
  page_number: number;
  security_level: number;
  retrieval_method: string;
}

export interface QueryResponse {
  answer: string;
  sources: ChunkResult[];
  prompt_assembled: string;
  retrieval_stats: Record<string, any>;
  access_denied: boolean;
  access_denied_message: string | null;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: Record<string, any>;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "document" | "chunk" | "entity";
  [key: string]: any;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  label: string;
}

export async function queryRAG(params: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${API_URL}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function fetchGraph(): Promise<GraphData> {
  const res = await fetch(`${API_URL}/api/graph`);
  if (!res.ok) throw new Error("Failed to load knowledge graph");
  return res.json();
}

export async function fetchStatus(): Promise<any> {
  const res = await fetch(`${API_URL}/api/status`);
  return res.json();
}

export async function triggerIngest(): Promise<any> {
  const res = await fetch(`${API_URL}/api/ingest`, { method: "POST" });
  return res.json();
}
```

### `lib/types.ts`
Re-export types from api.ts if needed, or add frontend-only types:
```typescript
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChunkResult[];
  accessDenied?: boolean;
  accessDeniedMessage?: string;
  timestamp: Date;
}
```

---

## Acceptance Criteria

- [ ] Landing page renders with 3 cards, each linking to correct route
- [ ] Project A: can type query, get answer, see sources with scores in side panel
- [ ] Project A: retrieval method badges show correctly (Dense/BM25/Hybrid)
- [ ] Project B: must select role before chatting
- [ ] Project B: employee asking "salary bands" gets access-denied UI
- [ ] Project B: admin asking same question gets real answer
- [ ] Project B: changing role clears chat
- [ ] Knowledge Graph: 3D graph renders with all node types visible
- [ ] Knowledge Graph: clicking a node shows info panel
- [ ] Knowledge Graph: can zoom, rotate, pan
- [ ] Responsive on mobile (cards stack, panels collapse)
- [ ] All API errors show user-friendly messages (not raw stack traces)

---

## Files Created

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                    # Landing page
│   ├── project-a/
│   │   └── page.tsx
│   ├── project-b/
│   │   └── page.tsx
│   └── knowledge-graph/
│       └── page.tsx
├── components/
│   ├── ChatInterface.tsx
│   ├── SourcePanel.tsx
│   ├── RoleSelector.tsx
│   ├── AccessDenied.tsx
│   ├── GraphViewer.tsx
│   └── LandingCard.tsx
└── lib/
    ├── api.ts
    └── types.ts
```
