"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Loader2, Play, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PipelineViewer } from "@/components/PipelineViewer";
import { StagePanel } from "@/components/StagePanel";
import { ThemeToggle } from "@/components/ThemeToggle";
import { fetchPipelineArchitecture, tracePipeline } from "@/lib/api";
import type {
  Mode,
  PipelineArchitecture,
  PipelineCandidate,
  PipelineStage,
  PipelineTrace,
  Role,
} from "@/lib/api";
import { ROLE_META } from "@/lib/types";

const ROLES: Role[] = ["employee", "manager", "admin"];

export default function PipelinePage() {
  const [arch, setArch] = useState<PipelineArchitecture | null>(null);
  const [trace, setTrace] = useState<PipelineTrace | null>(null);
  const [query, setQuery] = useState("What is the leave policy?");
  const [running, setRunning] = useState(false);
  const [runLLM, setRunLLM] = useState(true);
  const [mode, setMode] = useState<Mode>("open");
  const [role, setRole] = useState<Role>("employee");
  const [error, setError] = useState<string | null>(null);
  const [selectedStage, setSelectedStage] = useState<PipelineStage | null>(null);
  const [selectedCand, setSelectedCand] = useState<{ cand: PipelineCandidate; stageId: string } | null>(null);

  useEffect(() => {
    let cancel = false;
    fetchPipelineArchitecture()
      .then((a) => {
        if (!cancel) setArch(a);
      })
      .catch((e) => {
        if (!cancel) setError(e instanceof Error ? e.message : "Failed to load architecture");
      });
    return () => {
      cancel = true;
    };
  }, []);

  const onRun = useCallback(async () => {
    const q = query.trim();
    if (!q) return;
    setRunning(true);
    setError(null);
    try {
      const t = await tracePipeline({
        query: q,
        mode,
        role: mode === "secure" ? role : undefined,
        run_llm: runLLM,
      });
      setTrace(t);
      setSelectedCand(null);
      if (t.access_denied) {
        const securityStage = arch?.stages.find((s) => s.id === "security") ?? null;
        setSelectedStage(securityStage);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Trace failed");
    } finally {
      setRunning(false);
    }
  }, [arch, query, mode, role, runLLM]);

  const onClear = useCallback(() => {
    setTrace(null);
    setSelectedCand(null);
    setSelectedStage(null);
  }, []);

  return (
    <main className="relative flex h-screen flex-col bg-app text-base-fg">
      <header className="flex shrink-0 flex-wrap items-center gap-3 border-b border-soft bg-surface-overlay px-5 py-3 backdrop-blur-md">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-xs text-faint transition-colors hover:text-strong"
        >
          <ArrowLeft className="h-3 w-3" /> Home
        </Link>
        <div className="ml-2 hidden h-4 w-px bg-base sm:block" />
        <h1 className="text-sm font-semibold text-strong">Pipeline Visualizer</h1>

        <div className="ml-2 inline-flex rounded-md border border-base bg-surface-1 p-0.5 text-[11px]">
          <button
            type="button"
            onClick={() => setMode("open")}
            className={`rounded px-2.5 py-1 transition-colors ${
              mode === "open" ? "bg-surface-2 text-strong" : "text-muted-fg hover:text-strong"
            }`}
          >
            Open
          </button>
          <button
            type="button"
            onClick={() => setMode("secure")}
            className={`rounded px-2.5 py-1 transition-colors ${
              mode === "secure" ? "bg-rose-500/20 text-rose-700 dark:text-rose-200" : "text-muted-fg hover:text-strong"
            }`}
          >
            Secure
          </button>
        </div>

        {mode === "secure" ? (
          <div className="inline-flex rounded-md border border-base bg-surface-1 p-0.5 text-[11px]">
            {ROLES.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRole(r)}
                title={ROLE_META[r].description}
                className={`rounded px-2.5 py-1 transition-colors ${
                  role === r ? "bg-violet-500/20 text-violet-700 dark:text-violet-200" : "text-muted-fg hover:text-strong"
                }`}
              >
                {ROLE_META[r].label}
                <span className="ml-1 text-[10px] text-faint">L{ROLE_META[r].clearance}</span>
              </button>
            ))}
          </div>
        ) : null}

        <div className="ml-auto flex flex-1 items-center gap-2 sm:flex-none">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question to trace…"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !running) onRun();
            }}
            className="w-full bg-surface-1 sm:w-72"
          />
          <label className="hidden cursor-pointer items-center gap-1.5 text-[11px] text-muted-fg sm:flex">
            <input
              type="checkbox"
              checked={runLLM}
              onChange={(e) => setRunLLM(e.target.checked)}
              className="h-3 w-3 accent-violet-500"
            />
            run LLM
          </label>
          <Button onClick={onRun} disabled={running || !query.trim()}>
            {running ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Running
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" /> Run
              </>
            )}
          </Button>
          {trace ? (
            <Button variant="outline" onClick={onClear}>
              Clear
            </Button>
          ) : null}
          <ThemeToggle />
        </div>
      </header>

      {error ? (
        <div className="border-b border-red-500/40 bg-red-500/10 px-5 py-2 text-xs text-red-700 dark:text-red-200">
          {error}
        </div>
      ) : null}
      {trace?.access_denied ? (
        <div className="flex items-start gap-2 border-b border-red-500/40 bg-red-500/10 px-5 py-3 text-xs text-red-700 dark:text-red-100">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <div className="font-semibold">
              Access denied for role <span className="font-mono">{trace.role}</span>
            </div>
            <div className="opacity-80">
              {trace.access_denied_message ??
                "The accessible corpus didn't yield a strong match, but restricted chunks did."}
            </div>
          </div>
        </div>
      ) : null}

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[1fr_400px]">
        <div className="relative min-h-0 border-b border-soft lg:border-b-0 lg:border-r">
          <PipelineViewer
            architecture={arch}
            trace={trace}
            loading={running}
            onSelectStage={(s) => {
              setSelectedStage(s);
              setSelectedCand(null);
            }}
            onSelectCandidate={(c, stageId) => {
              setSelectedCand({ cand: c, stageId });
              setSelectedStage(null);
            }}
          />
          {trace ? <StatsBar trace={trace} /> : null}
        </div>
        <aside className="min-h-0 overflow-hidden bg-surface-overlay">
          <StagePanel
            selectedStage={selectedStage}
            selectedCandidate={selectedCand}
            trace={trace}
            onClose={() => {
              setSelectedStage(null);
              setSelectedCand(null);
            }}
          />
        </aside>
      </div>
    </main>
  );
}

function StatsBar({ trace }: { trace: PipelineTrace }) {
  const s = trace.stages;
  const sec = s.security;
  return (
    <div className="absolute bottom-3 left-1/2 z-10 flex max-w-[95%] -translate-x-1/2 flex-wrap items-center gap-2 rounded-full border border-base bg-surface-overlay px-4 py-2 text-[11px] shadow-card backdrop-blur-md">
      <Pill label="mode" value={trace.mode} highlight={trace.mode === "secure"} />
      {sec?.active ? (
        <Pill label="role" value={`${sec.role} · L${sec.clearance}`} highlight />
      ) : null}
      <Pill label="embed" value={`${s.embed.elapsed_ms}ms`} />
      <Pill label="dense" value={`${s.dense.candidates.length}·${s.dense.elapsed_ms}ms`} />
      <Pill label="bm25" value={`${s.bm25.candidates.length}·${s.bm25.elapsed_ms}ms`} />
      <Pill label="rrf" value={`${s.rrf.candidates.length}·${s.rrf.elapsed_ms}ms`} />
      <Pill label="rerank" value={`${s.rerank.candidates.length}·${s.rerank.elapsed_ms}ms`} />
      <Pill label="final" value={`${s.final.count}`} />
      <Pill label="llm" value={s.llm.used ? `${s.llm.elapsed_ms}ms` : "off"} />
      <Pill label="total" value={`${trace.total_elapsed_ms}ms`} highlight />
    </div>
  );
}

function Pill({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1 ${highlight ? "text-strong" : "text-muted-fg"}`}>
      <span className="text-faint">{label}</span>
      <span className={`font-mono ${highlight ? "text-strong" : "text-base-fg"}`}>{value}</span>
    </span>
  );
}
