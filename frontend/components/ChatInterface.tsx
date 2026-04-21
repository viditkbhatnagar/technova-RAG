"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Database, FileText, Layers, Send, Sparkles, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AccessDenied } from "@/components/AccessDenied";
import {
  queryRAG,
  type ChunkResult,
  type Mode,
  type QueryRoute,
  type Role,
  type RouteDecision,
  type SqlResult,
} from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

interface ChatInterfaceProps {
  mode: Mode;
  role?: Role | null;
  disabled?: boolean;
  disabledReason?: string;
  onSourcesChange?: (sources: ChunkResult[], stats?: Record<string, unknown>) => void;
  resetKey?: string;
  sessionId?: string | null;
  initialMessages?: ChatMessage[];
  onSessionIdChange?: (id: string) => void;
}

export function ChatInterface({
  mode,
  role,
  disabled,
  disabledReason,
  onSourcesChange,
  resetKey,
  sessionId,
  initialMessages,
  onSessionIdChange,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages || []);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeSessionRef = useRef<string | null>(sessionId || null);

  useEffect(() => {
    activeSessionRef.current = sessionId || null;
  }, [sessionId]);

  useEffect(() => {
    setMessages(initialMessages || []);
    setError(null);
    onSourcesChange?.([], undefined);
  }, [resetKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading || disabled) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await queryRAG({
        query: trimmed,
        mode,
        role: role || undefined,
        session_id: activeSessionRef.current || undefined,
      });
      if (response.session_id && response.session_id !== activeSessionRef.current) {
        activeSessionRef.current = response.session_id;
        onSessionIdChange?.(response.session_id);
      }
      const asst: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        sources: response.sources,
        accessDenied: response.access_denied,
        accessDeniedMessage: response.access_denied_message,
        restrictedDocCount: response.retrieval_stats?.restricted_doc_count as number | undefined,
        timestamp: new Date(),
        routeDecision: response.route ?? null,
        sqlResult: response.sql_result ?? null,
      };
      setMessages((prev) => [...prev, asst]);
      onSourcesChange?.(response.sources, response.retrieval_stats);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col bg-surface-3">
      <ScrollArea className="flex-1">
        <div ref={scrollRef} className="mx-auto w-full max-w-3xl space-y-6 px-6 py-8">
          {messages.length === 0 && !loading ? (
            <EmptyState mode={mode} />
          ) : null}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {loading ? <LoadingBubble /> : null}
          {error ? (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-200">
              {error}
            </div>
          ) : null}
        </div>
      </ScrollArea>
      <div className="border-t border-soft bg-surface-overlay p-4 backdrop-blur-md">
        <form onSubmit={handleSubmit} className="mx-auto flex max-w-3xl items-center gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              disabled
                ? disabledReason || "Input disabled"
                : mode === "secure"
                ? "Ask a question (responses filtered by your clearance)…"
                : "Ask a question about TechNova's documents…"
            }
            disabled={disabled || loading}
            className="flex-1 border-base bg-surface-1 text-strong placeholder:text-faint focus-visible:ring-violet-400/50"
          />
          <Button
            type="submit"
            disabled={disabled || loading || !input.trim()}
            className="bg-violet-500 text-white hover:bg-violet-400"
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}

function EmptyState({ mode }: { mode: Mode }) {
  const samples =
    mode === "open"
      ? [
          "How many days of maternity leave am I entitled to?",
          "What are the on-call escalation procedures?",
          "Summarize the Q4 financial highlights.",
        ]
      : [
          "What is the executive salary structure?",
          "What were the findings of the last security incident?",
          "What is the product roadmap for 2026?",
        ];
  return (
    <div className="flex flex-col items-center gap-4 py-12 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-base bg-surface-1">
        <Sparkles className="h-6 w-6 text-violet-500 dark:text-violet-300" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-strong">
          {mode === "open" ? "Open RAG Chat" : "Secure RAG Chat"}
        </h3>
        <p className="mt-1 max-w-md text-sm text-faint">
          Grounded answers from TechNova&apos;s corpus. Every response is cited from retrieved
          chunks shown on the right.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {samples.map((s) => (
          <span
            key={s}
            className="rounded-full border border-base bg-surface-1 px-3 py-1 text-xs text-muted-fg"
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${
          isUser
            ? "border-violet-400/40 bg-violet-500/20 text-violet-700 dark:text-violet-200"
            : "border-base bg-surface-1 text-muted-fg"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
      </div>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-violet-500/15 text-strong"
            : "border border-base bg-surface-1 text-base-fg"
        }`}
      >
        {message.accessDenied ? (
          <div className="space-y-3">
            <AccessDenied
              message={message.accessDeniedMessage || message.content}
              restrictedDocCount={message.restrictedDocCount}
            />
          </div>
        ) : (
          <div className="space-y-3">
            {message.routeDecision ? <RouteBadge decision={message.routeDecision} /> : null}
            {message.sqlResult ? <SqlResultBlock result={message.sqlResult} /> : null}
            <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-2 prose-headings:text-strong prose-strong:text-strong prose-a:text-violet-500 dark:prose-a:text-violet-300">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function RouteBadge({ decision }: { decision: RouteDecision }) {
  const meta: Record<QueryRoute, { label: string; bg: string; text: string; Icon: typeof Database }> = {
    sql: { label: "SQL", bg: "bg-emerald-500/15 border-emerald-500/40", text: "text-emerald-700 dark:text-emerald-200", Icon: Database },
    rag: { label: "RAG", bg: "bg-blue-500/15 border-blue-500/40", text: "text-blue-700 dark:text-blue-200", Icon: FileText },
    hybrid: { label: "Hybrid", bg: "bg-violet-500/15 border-violet-500/40", text: "text-violet-700 dark:text-violet-200", Icon: Layers },
  };
  const m = meta[decision.route];
  const Icon = m.Icon;
  return (
    <div className={`flex items-center gap-2 rounded-md border px-2 py-1 text-xs ${m.bg} ${m.text}`}>
      <Icon className="h-3.5 w-3.5" />
      <span className="font-medium">{m.label}</span>
      <span className="opacity-70">· {decision.reason}</span>
    </div>
  );
}

function SqlResultBlock({ result }: { result: SqlResult }) {
  if (!result.ok) {
    return (
      <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-800 dark:text-amber-200">
        <div className="font-medium">SQL path failed</div>
        <div className="mt-1 opacity-80">{result.error || "Unknown SQL error."}</div>
      </div>
    );
  }
  const cols = result.columns || [];
  const rows = result.rows || [];
  const showRows = rows.slice(0, 25);
  return (
    <div className="space-y-2 rounded-md border border-base bg-surface-2/60 p-3 text-xs">
      <div className="flex items-center justify-between text-muted-fg">
        <span className="font-medium text-strong">SQL result</span>
        <span>
          {result.row_count} row{result.row_count === 1 ? "" : "s"}
          {result.truncated ? " · truncated" : ""}
          {typeof result.elapsed_ms === "number" ? ` · ${result.elapsed_ms}ms` : ""}
        </span>
      </div>
      {result.sql ? (
        <pre className="overflow-x-auto rounded bg-surface-1 p-2 text-[11px] leading-snug text-muted-fg">
          <code>{result.sql}</code>
        </pre>
      ) : null}
      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-base text-muted-fg">
                {cols.map((c) => (
                  <th key={c} className="px-2 py-1 font-medium">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {showRows.map((r, i) => (
                <tr key={i} className="border-b border-base/40 last:border-0">
                  {cols.map((c) => (
                    <td key={c} className="px-2 py-1 align-top">
                      {formatCell(r[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length > showRows.length ? (
            <div className="pt-1 text-muted-fg">Showing first {showRows.length} of {rows.length}.</div>
          ) : null}
        </div>
      ) : (
        <div className="text-muted-fg">Query returned 0 rows.</div>
      )}
    </div>
  );
}

function formatCell(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toFixed(2).replace(/\.?0+$/, "");
  }
  if (typeof v === "boolean") return v ? "true" : "false";
  return String(v);
}

function LoadingBubble() {
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-base bg-surface-1 text-muted-fg">
        <Sparkles className="h-4 w-4" />
      </div>
      <div className="rounded-2xl border border-base bg-surface-1 px-4 py-3">
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 animate-pulse rounded-full bg-foreground/40 [animation-delay:0ms]" />
          <span className="h-2 w-2 animate-pulse rounded-full bg-foreground/40 [animation-delay:150ms]" />
          <span className="h-2 w-2 animate-pulse rounded-full bg-foreground/40 [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}
