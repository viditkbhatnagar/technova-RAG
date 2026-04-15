"use client";

import ReactMarkdown from "react-markdown";
import { Cpu, FileText, Globe, Server, Sparkles, Timer, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { SECURITY_COLORS } from "@/lib/types";
import type { PipelineCandidate, PipelineStage, PipelineTrace } from "@/lib/api";

interface StagePanelProps {
  selectedStage: PipelineStage | null;
  selectedCandidate: { cand: PipelineCandidate; stageId: string } | null;
  trace: PipelineTrace | null;
  onClose: () => void;
}

export function StagePanel({
  selectedStage,
  selectedCandidate,
  trace,
  onClose,
}: StagePanelProps) {
  if (selectedCandidate) {
    return <CandidateView cand={selectedCandidate.cand} stageId={selectedCandidate.stageId} onClose={onClose} />;
  }
  if (selectedStage) {
    return <StageView stage={selectedStage} trace={trace} onClose={onClose} />;
  }
  return <Empty trace={trace} />;
}

function StageView({
  stage,
  trace,
  onClose,
}: {
  stage: PipelineStage;
  trace: PipelineTrace | null;
  onClose: () => void;
}) {
  const live = trace?.stages as Record<string, unknown> | undefined;
  const stageData = (live?.[stage.id] ?? null) as Record<string, unknown> | null;
  const elapsed =
    typeof stageData?.elapsed_ms === "number" ? (stageData.elapsed_ms as number) : null;
  const candidates =
    (stageData?.candidates as PipelineCandidate[] | undefined) ??
    ((stage.id === "final" ? (stageData?.top_k as PipelineCandidate[] | undefined) : undefined) ??
      []);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex items-start justify-between gap-2 border-b border-soft p-4">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wider text-faint">stage</div>
          <div
            className="mt-0.5 truncate text-base font-semibold"
            style={{ color: stage.color }}
          >
            {stage.label}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1 text-faint transition-colors hover:bg-surface-2 hover:text-strong"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        <p className="text-sm text-muted-fg">{stage.description}</p>
        <div className="grid grid-cols-2 gap-2">
          {stage.model ? (
            <Field icon={<Cpu className="h-3 w-3" />} label="Model" value={stage.model} />
          ) : null}
          <Field
            icon={stage.runs_locally ? <Server className="h-3 w-3" /> : <Globe className="h-3 w-3" />}
            label="Runs"
            value={stage.runs_locally ? "local" : "remote"}
          />
          {elapsed !== null ? (
            <Field icon={<Timer className="h-3 w-3" />} label="Elapsed" value={`${elapsed}ms`} />
          ) : null}
          {typeof stageData?.device === "string" ? (
            <Field label="Device" value={stageData.device as string} />
          ) : null}
          {typeof stageData?.vector_dim === "number" ? (
            <Field label="Vector dim" value={String(stageData.vector_dim)} />
          ) : null}
          {typeof stageData?.k === "number" ? (
            <Field label="RRF k" value={String(stageData.k)} />
          ) : null}
          {typeof stageData?.overlap_count === "number" ? (
            <Field label="Overlap" value={String(stageData.overlap_count)} />
          ) : null}
        </div>
        {stage.id === "llm" && trace ? (
          <div className="rounded-lg border border-base bg-surface-1 p-3">
            <div className="text-[10px] uppercase tracking-wider text-faint">
              {trace.stages.llm.used ? `Answer (${trace.stages.llm.model})` : "Assembled prompt (LLM not configured)"}
            </div>
            <p className="mt-2 max-h-64 overflow-y-auto whitespace-pre-wrap text-sm text-base-fg">
              {trace.stages.llm.answer || "—"}
            </p>
          </div>
        ) : null}
        {stage.id === "security" && trace ? (
          <SecurityDetail trace={trace} />
        ) : null}
        {candidates.length > 0 ? (
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-wider text-faint">
                {stage.id === "final" ? "Top-K cited" : "Candidates"}
              </span>
              <span className="font-mono text-[10px] text-faint">
                {candidates.length}
              </span>
            </div>
            <div className="space-y-2">
              {candidates.map((c, i) => (
                <CandidateRow key={`${c.chunk_id}-${i}`} cand={c} index={i} />
              ))}
            </div>
          </div>
        ) : trace ? (
          <p className="text-xs text-faint">No per-stage candidates for this stage.</p>
        ) : null}
      </div>
    </div>
  );
}

function CandidateView({
  cand,
  stageId,
  onClose,
}: {
  cand: PipelineCandidate;
  stageId: string;
  onClose: () => void;
}) {
  const sec = SECURITY_COLORS[cand.security_level] ?? SECURITY_COLORS[1];
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex items-start justify-between gap-2 border-b border-soft p-4">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wider text-faint">
            chunk · {stageId}
          </div>
          <div className="mt-0.5 truncate text-base font-semibold text-strong">
            {cand.doc_name}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1 text-faint transition-colors hover:bg-surface-2 hover:text-strong"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge className={`${sec.bg} ${sec.text} ${sec.border} border text-[10px] font-semibold`}>
            {sec.label}
          </Badge>
          <Badge variant="outline" className="border-base font-mono text-[10px] text-muted-fg">
            p.{cand.page_number}
          </Badge>
          <Badge variant="outline" className="border-base font-mono text-[10px] text-muted-fg">
            score {cand.score.toFixed(3)}
          </Badge>
          {cand.retrieval_method ? (
            <Badge variant="outline" className="border-base font-mono text-[10px] text-muted-fg">
              {cand.retrieval_method}
            </Badge>
          ) : null}
        </div>
        <Separator className="bg-base" />
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-base-fg">
          {cand.text_preview}
        </p>
        <p className="font-mono text-[10px] text-ghost">{cand.chunk_id}</p>
      </div>
    </div>
  );
}

function SecurityDetail({ trace }: { trace: PipelineTrace }) {
  const sec = trace.stages.security;
  if (!sec) return null;
  if (!sec.active) {
    return (
      <div className="rounded-lg border border-base bg-surface-1 p-3 text-xs text-muted-fg">
        Security gate is <span className="text-strong">inactive</span> — open mode runs the
        full corpus through dense + BM25 with no clearance pre-filter.
      </div>
    );
  }
  const denied = trace.access_denied;
  return (
    <div className="space-y-3">
      <div
        className={`rounded-lg border p-3 text-sm ${
          denied
            ? "border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-100"
            : "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-100"
        }`}
      >
        <div className="text-[10px] uppercase tracking-wider opacity-70">
          {denied ? "access denied" : "security pre-filter active"}
        </div>
        <div className="mt-1 font-mono text-xs">
          role: <span className="font-semibold">{sec.role}</span>
          <span className="opacity-60"> · clearance ≤ {sec.clearance}</span>
        </div>
        {sec.allowed_chunk_count !== null ? (
          <div className="mt-0.5 font-mono text-[11px] opacity-80">
            {sec.allowed_chunk_count} accessible chunks
          </div>
        ) : null}
        {trace.access_denied_message ? (
          <p className="mt-2 text-xs">{trace.access_denied_message}</p>
        ) : null}
      </div>
      {sec.restricted_probe ? (
        <div className="rounded-lg border border-base bg-surface-1 p-3">
          <div className="text-[10px] uppercase tracking-wider text-faint">
            restricted probe (informational, never returned)
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] text-muted-fg">
            <div>
              <div className="text-faint">restricted matches</div>
              <div className="font-mono text-strong">{sec.restricted_probe.count}</div>
            </div>
            <div>
              <div className="text-faint">top cosine</div>
              <div className="font-mono text-strong">{sec.restricted_probe.top_cosine.toFixed(3)}</div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function CandidateRow({ cand, index }: { cand: PipelineCandidate; index: number }) {
  const sec = SECURITY_COLORS[cand.security_level] ?? SECURITY_COLORS[1];
  return (
    <div className="rounded-md border border-base bg-surface-1 p-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[10px] text-faint">#{index + 1}</span>
            <span className="truncate text-xs font-medium text-strong">{cand.doc_name}</span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-1">
            <Badge className={`${sec.bg} ${sec.text} ${sec.border} border text-[9px]`}>
              {sec.label}
            </Badge>
            <span className="font-mono text-[10px] text-faint">p.{cand.page_number}</span>
          </div>
        </div>
        <span className="font-mono text-[11px] text-base-fg">{cand.score.toFixed(3)}</span>
      </div>
      <p className="mt-1.5 line-clamp-2 text-[11px] text-muted-fg">{cand.text_preview}</p>
    </div>
  );
}

function Field({
  icon,
  label,
  value,
}: {
  icon?: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-base bg-surface-1 px-2.5 py-2">
      <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-faint">
        {icon}
        {label}
      </div>
      <div className="mt-0.5 truncate font-mono text-xs text-strong">{value}</div>
    </div>
  );
}

function Empty({ trace }: { trace: PipelineTrace | null }) {
  if (!trace) {
    return (
      <div className="flex h-full flex-col items-start gap-3 p-5 text-sm text-muted-fg">
        <div className="text-[10px] uppercase tracking-wider text-faint">Pipeline</div>
        <p>
          Type a question above and click <span className="font-semibold text-strong">Run</span>.
          Once a trace finishes, you&apos;ll see the LLM&apos;s answer and the cited chunks here,
          and you can click any stage in the 3D scene to drill into per-stage details.
        </p>
      </div>
    );
  }
  return <ResultSummary trace={trace} />;
}

function ResultSummary({ trace }: { trace: PipelineTrace }) {
  const top = trace.stages.final.top_k ?? [];
  const llm = trace.stages.llm;
  const docs = Array.from(
    new Map(top.map((c) => [c.doc_slug, c] as const)).values(),
  );

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-soft p-4">
        <div className="text-[10px] uppercase tracking-wider text-faint">Query</div>
        <p className="mt-1 text-sm text-strong">{trace.query}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-muted-fg">
          <span className="rounded bg-surface-2 px-1.5 py-0.5 font-mono uppercase tracking-wider">
            {trace.mode}
          </span>
          {trace.role ? (
            <span className="rounded bg-violet-500/15 px-1.5 py-0.5 font-mono text-violet-700 dark:text-violet-200">
              {trace.role}
            </span>
          ) : null}
          <span className="font-mono">total {trace.total_elapsed_ms}ms</span>
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {trace.access_denied ? (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-100">
            <div className="text-[10px] uppercase tracking-wider opacity-70">access denied</div>
            <p className="mt-1">{trace.access_denied_message ?? "No accessible matches."}</p>
          </div>
        ) : null}

        <section>
          <div className="mb-2 flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-violet-500 dark:text-violet-300" />
            <span className="text-[10px] uppercase tracking-wider text-faint">
              {llm.used ? `Answer · ${llm.model}` : "Assembled prompt (no LLM)"}
            </span>
            {llm.used ? (
              <span className="ml-auto font-mono text-[10px] text-faint">{llm.elapsed_ms}ms</span>
            ) : null}
          </div>
          <div className="rounded-lg border border-base bg-surface-1 p-3 shadow-card">
            {llm.answer ? (
              llm.used ? (
                <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-2 prose-headings:text-strong prose-strong:text-strong prose-a:text-violet-500 dark:prose-a:text-violet-300">
                  <ReactMarkdown>{llm.answer}</ReactMarkdown>
                </div>
              ) : (
                <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-muted-fg">
                  {llm.answer}
                </pre>
              )
            ) : (
              <p className="text-sm text-faint">No answer produced.</p>
            )}
          </div>
        </section>

        {docs.length > 0 ? (
          <section>
            <div className="mb-2 flex items-center gap-2">
              <FileText className="h-3.5 w-3.5 text-faint" />
              <span className="text-[10px] uppercase tracking-wider text-faint">
                Documents referenced
              </span>
              <span className="ml-auto font-mono text-[10px] text-faint">{docs.length}</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {docs.map((d) => {
                const sec = SECURITY_COLORS[d.security_level] ?? SECURITY_COLORS[1];
                return (
                  <span
                    key={d.doc_slug}
                    className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[10px] ${sec.bg} ${sec.text} ${sec.border}`}
                  >
                    <span className="font-medium">{d.doc_name}</span>
                  </span>
                );
              })}
            </div>
          </section>
        ) : null}

        {top.length > 0 ? (
          <section>
            <div className="mb-2 flex items-center gap-2">
              <span className="text-[10px] uppercase tracking-wider text-faint">
                Cited chunks (top {top.length})
              </span>
            </div>
            <div className="space-y-2">
              {top.map((c, i) => (
                <CandidateRow key={`${c.chunk_id}-${i}`} cand={c} index={i} />
              ))}
            </div>
          </section>
        ) : null}

        <p className="pt-2 text-[10px] text-faint">
          Click any stage or chunk in the 3D scene to drill into per-stage details.
        </p>
      </div>
    </div>
  );
}
