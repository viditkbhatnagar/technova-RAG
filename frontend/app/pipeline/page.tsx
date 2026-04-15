"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Loader2, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PipelineViewer } from "@/components/PipelineViewer";
import { StagePanel } from "@/components/StagePanel";
import { fetchPipelineArchitecture, tracePipeline } from "@/lib/api";
import type {
  PipelineArchitecture,
  PipelineCandidate,
  PipelineStage,
  PipelineTrace,
} from "@/lib/api";

export default function PipelinePage() {
  const [arch, setArch] = useState<PipelineArchitecture | null>(null);
  const [trace, setTrace] = useState<PipelineTrace | null>(null);
  const [query, setQuery] = useState("What is the leave policy?");
  const [running, setRunning] = useState(false);
  const [runLLM, setRunLLM] = useState(true);
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
      const t = await tracePipeline({ query: q, mode: "open", run_llm: runLLM });
      setTrace(t);
      setSelectedCand(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Trace failed");
    } finally {
      setRunning(false);
    }
  }, [query, runLLM]);

  const onClear = useCallback(() => {
    setTrace(null);
    setSelectedCand(null);
    setSelectedStage(null);
  }, []);

  return (
    <main className="relative flex h-screen flex-col bg-[#050507] text-white">
      <header className="flex shrink-0 flex-wrap items-center gap-3 border-b border-white/10 bg-black/50 px-5 py-3 backdrop-blur-md">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-xs text-white/50 transition-colors hover:text-white/80"
        >
          <ArrowLeft className="h-3 w-3" /> Home
        </Link>
        <div className="ml-2 hidden h-4 w-px bg-white/15 sm:block" />
        <h1 className="text-sm font-semibold">Pipeline Visualizer</h1>
        <p className="hidden text-xs text-white/40 sm:block">
          {trace
            ? "Live trace · click any node for details"
            : "Static architecture · run a query to see live data flow"}
        </p>

        <div className="ml-auto flex flex-1 items-center gap-2 sm:flex-none">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question to trace…"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !running) onRun();
            }}
            className="w-full bg-white/5 sm:w-80"
          />
          <label className="hidden cursor-pointer items-center gap-1.5 text-[11px] text-white/60 sm:flex">
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
        </div>
      </header>

      {error ? (
        <div className="border-b border-red-500/30 bg-red-500/10 px-5 py-2 text-xs text-red-200">
          {error}
        </div>
      ) : null}

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[1fr_400px]">
        <div className="relative min-h-0 border-b border-white/10 lg:border-b-0 lg:border-r">
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
        <aside className="min-h-0 overflow-hidden bg-black/40">
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
  return (
    <div className="absolute bottom-3 left-1/2 z-10 flex max-w-[95%] -translate-x-1/2 flex-wrap items-center gap-2 rounded-full border border-white/10 bg-black/70 px-4 py-2 text-[11px] backdrop-blur-md">
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
    <span className={`inline-flex items-center gap-1 ${highlight ? "text-white" : "text-white/70"}`}>
      <span className="text-white/40">{label}</span>
      <span className={`font-mono ${highlight ? "text-white" : "text-white/85"}`}>{value}</span>
    </span>
  );
}
