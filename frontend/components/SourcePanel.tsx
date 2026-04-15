"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, FileText, Clock, BarChart3 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { ChunkResult, RetrievalStats } from "@/lib/api";
import { SECURITY_COLORS } from "@/lib/types";

interface SourcePanelProps {
  sources: ChunkResult[];
  stats?: RetrievalStats;
  emptyLabel?: string;
}

function methodBadgeClass(method: string): string {
  const m = method.toLowerCase();
  if (m === "dense") return "bg-sky-500/15 text-sky-300 border-sky-500/40";
  if (m === "bm25") return "bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-500/40";
  return "bg-violet-500/15 text-violet-300 border-violet-500/40";
}

function methodLabel(method: string): string {
  const m = method.toLowerCase();
  if (m === "dense") return "Dense";
  if (m === "bm25") return "BM25";
  return "Hybrid";
}

export function SourcePanel({ sources, stats, emptyLabel }: SourcePanelProps) {
  return (
    <div className="flex h-full min-h-0 flex-col border-l border-white/10 bg-black/30">
      <div className="shrink-0 border-b border-white/10 px-5 py-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-white/70">
          Retrieved Sources
        </h2>
        {stats && sources.length > 0 ? (
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
            <StatPill icon={<FileText className="h-3 w-3" />} label="Results" value={String(sources.length)} />
            <StatPill
              icon={<BarChart3 className="h-3 w-3" />}
              label="Avg Score"
              value={
                typeof stats.avg_rerank_score === "number"
                  ? stats.avg_rerank_score.toFixed(2)
                  : "—"
              }
            />
            <StatPill
              icon={<Clock className="h-3 w-3" />}
              label="Time"
              value={
                typeof stats.retrieval_time_ms === "number"
                  ? `${stats.retrieval_time_ms}ms`
                  : "—"
              }
            />
          </div>
        ) : null}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        <div className="space-y-3 p-5">
          {sources.length === 0 ? (
            <div className="flex h-full min-h-[200px] flex-col items-center justify-center text-center text-sm text-white/40">
              <FileText className="mb-2 h-8 w-8 opacity-40" />
              <p>{emptyLabel || "Ask a question to see retrieved sources."}</p>
            </div>
          ) : (
            sources.map((src, idx) => <SourceCard key={src.chunk_id} source={src} index={idx} />)
          )}
        </div>
      </div>
    </div>
  );
}

function StatPill({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-md border border-white/10 bg-white/5 px-2 py-1.5">
      <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-white/40">
        {icon}
        {label}
      </div>
      <div className="mt-0.5 font-mono text-sm text-white/90">{value}</div>
    </div>
  );
}

function SourceCard({ source, index }: { source: ChunkResult; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const sec = SECURITY_COLORS[source.security_level] ?? SECURITY_COLORS[1];
  const truncated = source.text.length > 180 ? source.text.slice(0, 180) + "…" : source.text;
  const scorePct = Math.min(100, Math.max(0, source.score * 100));

  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-3 transition-colors hover:border-white/20">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="secondary" className="bg-white/10 font-mono text-[10px] text-white/60">
            #{index + 1}
          </Badge>
          <Badge variant="outline" className="max-w-[180px] truncate border-white/20 text-xs text-white/80">
            {source.doc_name}
          </Badge>
          <Badge variant="outline" className="border-white/20 text-[10px] text-white/60">
            p.{source.page_number}
          </Badge>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <Badge className={`${sec.bg} ${sec.text} ${sec.border} border text-[10px] font-semibold`}>
          {sec.label}
        </Badge>
        <Badge variant="outline" className={`${methodBadgeClass(source.retrieval_method)} border text-[10px]`}>
          {methodLabel(source.retrieval_method)}
        </Badge>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="font-mono text-[10px] text-white/50">
            {source.score.toFixed(3)}
          </span>
        </div>
      </div>
      <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-white/5">
        <div
          className="h-full rounded-full bg-gradient-to-r from-violet-500 to-sky-500"
          style={{ width: `${scorePct}%` }}
        />
      </div>
      <Separator className="my-2.5 bg-white/10" />
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-white/75">
        {expanded ? source.text : truncated}
      </p>
      {source.text.length > 180 ? (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 inline-flex items-center gap-1 text-xs text-white/50 transition-colors hover:text-white/90"
        >
          {expanded ? (
            <>
              <ChevronUp className="h-3 w-3" /> Show less
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3" /> Show more
            </>
          )}
        </button>
      ) : null}
    </div>
  );
}
