import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { GraphViewer } from "@/components/GraphViewer";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function KnowledgeGraphPage() {
  return (
    <main className="flex h-screen flex-col bg-app text-base-fg">
      <div className="flex items-center justify-between border-b border-soft bg-surface-overlay px-5 py-3 backdrop-blur-md">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-muted-fg transition-colors hover:text-strong"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm text-strong">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
            <span className="font-semibold">Knowledge Graph</span>
          </div>
          <span className="hidden text-xs text-faint sm:inline">
            Click a node for details · drag to rotate · scroll to zoom
          </span>
        </div>
        <ThemeToggle />
      </div>
      <div className="relative flex-1 overflow-hidden">
        <GraphViewer />
      </div>
    </main>
  );
}
