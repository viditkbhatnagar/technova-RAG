"use client";

import { Cpu, Globe, Server, Timer, X } from "lucide-react";
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
      <div className="flex items-start justify-between gap-2 border-b border-white/10 p-4">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wider text-white/40">stage</div>
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
          className="rounded-md p-1 text-white/50 transition-colors hover:bg-white/10 hover:text-white"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        <p className="text-sm text-white/70">{stage.description}</p>
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
          <div className="rounded-lg border border-white/10 bg-white/5 p-3">
            <div className="text-[10px] uppercase tracking-wider text-white/40">
              {trace.stages.llm.used ? `Answer (${trace.stages.llm.model})` : "Assembled prompt (LLM not configured)"}
            </div>
            <p className="mt-2 max-h-64 overflow-y-auto whitespace-pre-wrap text-sm text-white/80">
              {trace.stages.llm.answer || "—"}
            </p>
          </div>
        ) : null}
        {candidates.length > 0 ? (
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-wider text-white/40">
                {stage.id === "final" ? "Top-K cited" : "Candidates"}
              </span>
              <span className="font-mono text-[10px] text-white/40">
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
          <p className="text-xs text-white/40">No per-stage candidates for this stage.</p>
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
      <div className="flex items-start justify-between gap-2 border-b border-white/10 p-4">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wider text-white/40">
            chunk · {stageId}
          </div>
          <div className="mt-0.5 truncate text-base font-semibold text-white">
            {cand.doc_name}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1 text-white/50 transition-colors hover:bg-white/10 hover:text-white"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge className={`${sec.bg} ${sec.text} ${sec.border} border text-[10px] font-semibold`}>
            {sec.label}
          </Badge>
          <Badge variant="outline" className="border-white/20 font-mono text-[10px] text-white/60">
            p.{cand.page_number}
          </Badge>
          <Badge variant="outline" className="border-white/20 font-mono text-[10px] text-white/60">
            score {cand.score.toFixed(3)}
          </Badge>
          {cand.retrieval_method ? (
            <Badge variant="outline" className="border-white/20 font-mono text-[10px] text-white/60">
              {cand.retrieval_method}
            </Badge>
          ) : null}
        </div>
        <Separator className="bg-white/10" />
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-white/80">
          {cand.text_preview}
        </p>
        <p className="font-mono text-[10px] text-white/30">{cand.chunk_id}</p>
      </div>
    </div>
  );
}

function CandidateRow({ cand, index }: { cand: PipelineCandidate; index: number }) {
  const sec = SECURITY_COLORS[cand.security_level] ?? SECURITY_COLORS[1];
  return (
    <div className="rounded-md border border-white/10 bg-white/5 p-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[10px] text-white/40">#{index + 1}</span>
            <span className="truncate text-xs font-medium text-white/90">{cand.doc_name}</span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-1">
            <Badge className={`${sec.bg} ${sec.text} ${sec.border} border text-[9px]`}>
              {sec.label}
            </Badge>
            <span className="font-mono text-[10px] text-white/40">p.{cand.page_number}</span>
          </div>
        </div>
        <span className="font-mono text-[11px] text-white/70">{cand.score.toFixed(3)}</span>
      </div>
      <p className="mt-1.5 line-clamp-2 text-[11px] text-white/55">{cand.text_preview}</p>
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
    <div className="rounded-md border border-white/10 bg-white/5 px-2.5 py-2">
      <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-white/40">
        {icon}
        {label}
      </div>
      <div className="mt-0.5 truncate font-mono text-xs text-white/85">{value}</div>
    </div>
  );
}

function Empty({ trace }: { trace: PipelineTrace | null }) {
  return (
    <div className="flex h-full flex-col items-start gap-3 p-5 text-sm text-white/60">
      <div className="text-[10px] uppercase tracking-wider text-white/40">Pipeline</div>
      <p>
        Click any stage in the 3D scene to see what runs there, the model used, and (in
        live mode) the candidates that flowed through.
      </p>
      {trace ? (
        <div className="w-full space-y-2">
          <div className="text-[10px] uppercase tracking-wider text-white/40">Last run</div>
          <div className="rounded-lg border border-white/10 bg-white/5 p-3">
            <p className="truncate text-xs text-white/80">{trace.query}</p>
            <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] text-white/60">
              <span>mode: {trace.mode}{trace.role ? ` · ${trace.role}` : ""}</span>
              <span>total: {trace.total_elapsed_ms}ms</span>
              <span>final: {trace.stages.final.count}</span>
              <span>llm: {trace.stages.llm.used ? "yes" : "no"}</span>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
