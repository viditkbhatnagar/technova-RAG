"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { ChatInterface } from "@/components/ChatInterface";
import { ChatSidebar } from "@/components/ChatSidebar";
import { SourcePanel } from "@/components/SourcePanel";
import { ThemeToggle } from "@/components/ThemeToggle";
import { getSession, type ChunkResult, type RetrievalStats } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

export default function ProjectAPage() {
  const [sources, setSources] = useState<ChunkResult[]>([]);
  const [stats, setStats] = useState<RetrievalStats | undefined>(undefined);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [seedMessages, setSeedMessages] = useState<ChatMessage[]>([]);
  const [resetKey, setResetKey] = useState("new");
  const [refreshKey, setRefreshKey] = useState(0);

  const loadSession = useCallback(async (id: string) => {
    const data = await getSession(id);
    if (!data) return;
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
  }, []);

  function startNew() {
    setSeedMessages([]);
    setSessionId(null);
    setSources([]);
    setStats(undefined);
    setResetKey(`new-${Date.now()}`);
  }

  useEffect(() => {
    if (sessionId) setRefreshKey((k) => k + 1);
  }, [sessionId]);

  return (
    <main className="flex h-screen flex-col bg-app text-base-fg">
      <Header />
      <div className="grid flex-1 grid-cols-[16rem_minmax(0,1fr)] overflow-hidden lg:grid-cols-[16rem_3fr_2fr]">
        <ChatSidebar
          mode="open"
          activeSessionId={sessionId}
          refreshKey={refreshKey}
          onSelect={loadSession}
          onNew={startNew}
        />
        <ChatInterface
          mode="open"
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
        <SourcePanel sources={sources} stats={stats} />
      </div>
    </main>
  );
}

function Header() {
  return (
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
          <span className="h-1.5 w-1.5 rounded-full bg-violet-400" />
          <span className="font-semibold">Project A · Open RAG</span>
        </div>
        <span className="hidden text-xs text-faint sm:inline">
          All 11 documents · No access control
        </span>
      </div>
      <ThemeToggle />
    </div>
  );
}
