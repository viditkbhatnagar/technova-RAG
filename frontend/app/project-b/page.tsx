"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { ChatInterface } from "@/components/ChatInterface";
import { SourcePanel } from "@/components/SourcePanel";
import { RoleSelector } from "@/components/RoleSelector";
import type { ChunkResult, RetrievalStats, Role } from "@/lib/api";

export default function ProjectBPage() {
  const [role, setRole] = useState<Role | null>(null);
  const [sources, setSources] = useState<ChunkResult[]>([]);
  const [stats, setStats] = useState<RetrievalStats | undefined>(undefined);

  function handleRoleChange(next: Role) {
    if (next === role) return;
    setRole(next);
    setSources([]);
    setStats(undefined);
  }

  return (
    <main className="flex h-screen flex-col bg-[#0a0a0c] text-white">
      <Header />
      <div className="border-b border-white/10 bg-black/30 px-5 py-3">
        <RoleSelector role={role} onChange={handleRoleChange} />
      </div>
      <div className="grid flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[3fr_2fr]">
        <ChatInterface
          mode="secure"
          role={role}
          disabled={!role}
          disabledReason="Select a role above to start chatting"
          resetKey={role || "none"}
          onSourcesChange={(s, st) => {
            setSources(s);
            setStats(st as RetrievalStats | undefined);
          }}
        />
        <SourcePanel
          sources={sources}
          stats={stats}
          emptyLabel={
            role
              ? "Ask a question to see retrieved sources."
              : "Select a role above — sources are filtered by your clearance."
          }
        />
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
          <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
          <span className="font-semibold">Project B · Secure RAG</span>
        </div>
        <span className="hidden text-xs text-white/40 sm:inline">
          Role-based access · Security pre-filter
        </span>
      </div>
      <div className="w-16" />
    </div>
  );
}
