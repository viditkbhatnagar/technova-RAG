"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { ChatInterface } from "@/components/ChatInterface";
import { ChatSidebar } from "@/components/ChatSidebar";
import { SourcePanel } from "@/components/SourcePanel";
import { RoleSelector } from "@/components/RoleSelector";
import { getSession, type ChunkResult, type RetrievalStats, type Role } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

export default function ProjectBPage() {
  const [role, setRole] = useState<Role | null>(null);
  const [sources, setSources] = useState<ChunkResult[]>([]);
  const [stats, setStats] = useState<RetrievalStats | undefined>(undefined);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [seedMessages, setSeedMessages] = useState<ChatMessage[]>([]);
  const [resetKey, setResetKey] = useState("none");
  const [refreshKey, setRefreshKey] = useState(0);

  function startNew() {
    setSeedMessages([]);
    setSessionId(null);
    setSources([]);
    setStats(undefined);
    setResetKey(`new-${role || "none"}-${Date.now()}`);
  }

  function handleRoleChange(next: Role) {
    if (next === role) return;
    setRole(next);
    startNew();
  }

  const loadSession = useCallback(async (id: string) => {
    const data = await getSession(id);
    if (!data) return;
    if (data.role && data.role !== role) {
      setRole(data.role);
    }
    const seed: ChatMessage[] = data.messages.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      sources: m.sources,
      accessDenied: m.access_denied,
      accessDeniedMessage: m.access_denied_message,
      timestamp: new Date(m.created_at),
    }));
    setSeedMessages(seed);
    setSessionId(id);
    setResetKey(id);
    const lastAssistant = [...data.messages].reverse().find((m) => m.role === "assistant");
    setSources(lastAssistant?.sources || []);
    setStats(lastAssistant?.retrieval_stats as RetrievalStats | undefined);
  }, [role]);

  useEffect(() => {
    if (sessionId) setRefreshKey((k) => k + 1);
  }, [sessionId]);

  return (
    <main className="flex h-screen flex-col bg-[#0a0a0c] text-white">
      <Header />
      <div className="border-b border-white/10 bg-black/30 px-5 py-3">
        <RoleSelector role={role} onChange={handleRoleChange} />
      </div>
      <div className="grid flex-1 grid-cols-[16rem_minmax(0,1fr)] overflow-hidden lg:grid-cols-[16rem_3fr_2fr]">
        <ChatSidebar
          mode="secure"
          activeSessionId={sessionId}
          refreshKey={refreshKey}
          onSelect={loadSession}
          onNew={startNew}
        />
        <ChatInterface
          mode="secure"
          role={role}
          disabled={!role}
          disabledReason="Select a role above to start chatting"
          sessionId={sessionId}
          initialMessages={seedMessages}
          resetKey={resetKey}
          onSessionIdChange={(id) => {
            setSessionId(id);
            setRefreshKey((k) => k + 1);
          }}
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
