"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { ChatInterface } from "@/components/ChatInterface";
import { SourcePanel } from "@/components/SourcePanel";
import type { ChunkResult, RetrievalStats } from "@/lib/api";

export default function ProjectAPage() {
  const [sources, setSources] = useState<ChunkResult[]>([]);
  const [stats, setStats] = useState<RetrievalStats | undefined>(undefined);

  return (
    <main className="flex h-screen flex-col bg-[#0a0a0c] text-white">
      <Header />
      <div className="grid flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[3fr_2fr]">
        <ChatInterface
          mode="open"
          onSourcesChange={(s, st) => {
            setSources(s);
            setStats(st as RetrievalStats | undefined);
          }}
        />
        <SourcePanel sources={sources} stats={stats} />
      </div>
    </main>
  );
}

function Header() {
  return (
    <div className="flex items-center justify-between border-b border-white/10 bg-black/40 px-5 py-3">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm text-white/60 transition-colors hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </Link>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-violet-400" />
          <span className="font-semibold">Project A · Open RAG</span>
        </div>
        <span className="hidden text-xs text-white/40 sm:inline">
          All 11 documents · No access control
        </span>
      </div>
      <div className="w-16" />
    </div>
  );
}
