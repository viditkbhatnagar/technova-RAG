"use client";

import { useCallback, useEffect, useState } from "react";
import { MessageSquarePlus, MessagesSquare, Trash2, Loader2 } from "lucide-react";
import {
  deleteSession,
  listSessions,
  type Mode,
  type SessionSummary,
} from "@/lib/api";

interface ChatSidebarProps {
  mode: Mode;
  activeSessionId: string | null;
  refreshKey?: number;
  onSelect: (sessionId: string) => void;
  onNew: () => void;
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diff = Math.max(0, Date.now() - then);
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

export function ChatSidebar({
  mode,
  activeSessionId,
  refreshKey,
  onSelect,
  onNew,
}: ChatSidebarProps) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listSessions(mode, 50);
      setSessions(data);
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => {
    refresh();
  }, [refresh, refreshKey]);

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    if (!confirm("Delete this conversation?")) return;
    const ok = await deleteSession(id);
    if (ok) {
      setSessions((s) => s.filter((x) => x.id !== id));
      if (id === activeSessionId) onNew();
    }
  }

  return (
    <aside className="flex h-full min-h-0 w-64 flex-col border-r border-soft bg-surface-overlay">
      <div className="shrink-0 border-b border-soft p-3">
        <button
          type="button"
          onClick={onNew}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-base bg-surface-1 px-3 py-2 text-sm font-medium text-base-fg transition-colors hover:bg-surface-2 hover:text-strong"
        >
          <MessagesSquare className="h-4 w-4" />
          New chat
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-8 text-xs text-faint">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Loading…
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-10 px-4 text-center text-xs text-faint">
            <MessagesSquare className="h-6 w-6 opacity-50" />
            <p>No conversations yet. Send a message to start one.</p>
          </div>
        ) : (
          <ul className="space-y-1 p-2">
            {sessions.map((s) => {
              const active = s.id === activeSessionId;
              return (
                <li
                  key={s.id}
                  className={`group relative flex items-start gap-2 rounded-md text-sm transition-colors ${
                    active
                      ? "bg-violet-500/15 text-strong"
                      : "text-base-fg hover:bg-surface-1"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => onSelect(s.id)}
                    className="flex min-w-0 flex-1 items-start gap-2 rounded-md px-2.5 py-2 pr-8 text-left"
                  >
                    <MessageSquarePlus
                      className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${
                        active ? "text-violet-500 dark:text-violet-300" : "text-faint"
                      }`}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-xs leading-tight text-base-fg">
                        {s.title || "(untitled)"}
                      </span>
                      <span className="mt-0.5 flex items-center gap-2 text-[10px] text-faint">
                        <span>{relativeTime(s.updated_at)}</span>
                        {s.role ? (
                          <span className="rounded bg-surface-2 px-1 py-px text-[9px] uppercase tracking-wider">
                            {s.role}
                          </span>
                        ) : null}
                        <span>· {s.message_count} msg</span>
                      </span>
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={(e) => handleDelete(e, s.id)}
                    className="invisible absolute right-1.5 top-1.5 rounded p-1 text-faint transition-colors hover:bg-surface-2 hover:text-red-500 dark:hover:text-red-300 group-hover:visible"
                    aria-label="Delete conversation"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
