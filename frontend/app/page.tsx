import { LandingCard } from "@/components/LandingCard";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-app">
      <div className="pointer-events-none absolute inset-0">
        <div
          className="absolute left-1/2 top-0 h-[600px] w-[600px] -translate-x-1/2 rounded-full blur-[120px]"
          style={{ background: "var(--app-bg-image-1)" }}
        />
        <div
          className="absolute bottom-0 right-0 h-[500px] w-[500px] rounded-full blur-[120px]"
          style={{ background: "var(--app-bg-image-2)" }}
        />
        <div
          className="absolute left-0 top-1/2 h-[400px] w-[400px] rounded-full blur-[120px]"
          style={{ background: "var(--app-bg-image-3)" }}
        />
      </div>

      <div className="absolute right-5 top-5 z-10">
        <ThemeToggle />
      </div>

      <div className="relative mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-16 sm:py-24">
        <header className="mb-14 text-center sm:mb-20">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-base bg-surface-1 px-3 py-1 text-xs text-muted-fg backdrop-blur-md">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Hybrid retrieval · BM25 + Dense · Cross-encoder reranking
          </div>
          <h1 className="text-balance text-4xl font-semibold tracking-tight text-strong sm:text-6xl">
            TechNova RAG Platform
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-balance text-base text-muted-fg sm:text-lg">
            A grounded, role-aware retrieval system over 11 TechNova documents. Chat openly,
            chat securely, or explore the knowledge graph in 3D.
          </p>
        </header>

        <div className="grid flex-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          <LandingCard
            icon="💬"
            title="Open RAG"
            description="Chat with all 11 TechNova documents. Hybrid retrieval with dense + BM25 search, RRF fusion, and cross-encoder reranking."
            href="/project-a"
            accent="#8b5cf6"
          />
          <LandingCard
            icon="🛡️"
            title="Secure RAG"
            description="Role-based document access. Employees, managers, and admins see different answers based on security clearance."
            href="/project-b"
            accent="#f59e0b"
          />
          <LandingCard
            icon="🕸️"
            title="Knowledge Graph"
            description="Explore entities, relationships, and connections across all documents in an interactive 3D visualization."
            href="/knowledge-graph"
            accent="#06b6d4"
          />
          <LandingCard
            icon="📚"
            title="Document Explorer"
            description="Browse every PDF in the corpus, drill into chunks, and inspect what's mirrored to Postgres for the Neon portal."
            href="/documents"
            accent="#10b981"
          />
          <LandingCard
            icon="⚙️"
            title="Pipeline Visualizer"
            description="Watch a query flow through Embed → Dense + BM25 → RRF → Rerank → LLM in 3D. Static diagram + live trace."
            href="/pipeline"
            accent="#ec4899"
          />
        </div>

        <footer className="mt-14 text-center text-xs text-ghost sm:mt-20">
          FastAPI · Qdrant · BGE embeddings · spaCy NER · gpt-4o-mini
        </footer>
      </div>
    </main>
  );
}
