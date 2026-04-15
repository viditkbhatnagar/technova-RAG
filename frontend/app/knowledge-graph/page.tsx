import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { GraphViewer } from "@/components/GraphViewer";

export default function KnowledgeGraphPage() {
  return (
    <main className="flex h-screen flex-col bg-black text-white">
      <div className="flex items-center justify-between border-b border-white/10 bg-black/80 px-5 py-3 backdrop-blur-md">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-white/60 transition-colors hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
            <span className="font-semibold">Knowledge Graph</span>
          </div>
          <span className="hidden text-xs text-white/40 sm:inline">
            Click a node for details · drag to rotate · scroll to zoom
          </span>
        </div>
        <div className="w-16" />
      </div>
      <div className="relative flex-1 overflow-hidden">
        <GraphViewer />
      </div>
    </main>
  );
}
