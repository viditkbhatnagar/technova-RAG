"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";
import { SECURITY_COLORS } from "@/lib/types";
import { useTheme } from "@/lib/theme";
import type {
  PipelineArchitecture,
  PipelineCandidate,
  PipelineStage,
  PipelineTrace,
} from "@/lib/api";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), { ssr: false });

interface PipelineViewerProps {
  architecture: PipelineArchitecture | null;
  trace: PipelineTrace | null;
  loading: boolean;
  onSelectStage: (stage: PipelineStage) => void;
  onSelectCandidate: (cand: PipelineCandidate, stageId: string) => void;
}

const STAGE_POSITIONS: Record<string, { x: number; y: number; z: number }> = {
  query:    { x: -360, y:    0, z:    0 },
  embed:    { x: -180, y:   60, z:    0 },
  security: { x: -180, y:  -60, z:  120 },
  dense:    { x:    0, y:  100, z:    0 },
  bm25:     { x:    0, y: -100, z:    0 },
  rrf:      { x:  180, y:    0, z:    0 },
  rerank:   { x:  340, y:    0, z:    0 },
  final:    { x:  500, y:    0, z:    0 },
  llm:      { x:  680, y:    0, z:    0 },
};

const SATELLITE_STAGES = ["dense", "bm25", "rrf", "rerank", "final"] as const;
type SatelliteStage = (typeof SATELLITE_STAGES)[number];

interface ViewNode {
  id: string;
  label: string;
  kind: "stage" | "candidate";
  stageId: string;
  color: string;
  size: number;
  fx?: number;
  fy?: number;
  fz?: number;
  x?: number;
  y?: number;
  z?: number;
  raw?: PipelineStage | PipelineCandidate;
}

interface ViewLink {
  source: string;
  target: string;
  kind: "stage" | "satellite";
  color: string;
  width: number;
  particles: number;
}

function candidatesForStage(trace: PipelineTrace | null, stageId: SatelliteStage): PipelineCandidate[] {
  if (!trace) return [];
  if (stageId === "final") return trace.stages.final.top_k ?? [];
  const s = trace.stages[stageId];
  return (s as { candidates?: PipelineCandidate[] })?.candidates ?? [];
}

function buildGraphData(
  arch: PipelineArchitecture,
  trace: PipelineTrace | null,
  palette: { stageEdge: string; dimEdge: string },
): { nodes: ViewNode[]; links: ViewLink[] } {
  const secureActive = trace?.mode === "secure" && trace?.stages.security?.active === true;
  const accessDenied = trace?.access_denied === true;

  const nodes: ViewNode[] = arch.stages.map((s) => {
    const pos = STAGE_POSITIONS[s.id] ?? { x: 0, y: 0, z: 0 };
    let color = s.color;
    let size = 22;
    if (s.id === "security") {
      color = secureActive ? (accessDenied ? "#ef4444" : s.color) : "rgba(244,63,94,0.25)";
      size = secureActive ? 26 : 16;
    }
    if (s.id === "llm" && trace && !trace.stages.llm.used) {
      color = "rgba(139,92,246,0.35)";
    }
    return {
      id: s.id,
      label: s.label,
      kind: "stage",
      stageId: s.id,
      color,
      size,
      fx: pos.x,
      fy: pos.y,
      fz: pos.z,
      raw: s,
    };
  });

  const links: ViewLink[] = arch.edges.map((e) => {
    const isSecurityEdge =
      e.source === "security" || e.target === "security";
    let color = palette.stageEdge;
    let width = 1.6;
    if (isSecurityEdge) {
      color = secureActive
        ? accessDenied
          ? "rgba(239,68,68,0.55)"
          : "rgba(244,63,94,0.55)"
        : "rgba(244,63,94,0.12)";
      width = secureActive ? 1.8 : 0.6;
    }
    if ((e.source === "query" || e.source === "embed") && (e.target === "dense" || e.target === "bm25")) {
      // direct query→bm25 / embed→dense edges dim when security is active to
      // emphasise the gated path
      if (secureActive) {
        color = palette.dimEdge;
        width = 0.8;
      }
    }
    return {
      source: e.source,
      target: e.target,
      kind: "stage",
      color,
      width,
      particles: 0,
    };
  });

  if (trace) {
    // chunk satellites + flow particles for each retrieval-bearing stage
    for (const stageId of SATELLITE_STAGES) {
      const cands = candidatesForStage(trace, stageId).slice(0, 10);
      if (cands.length === 0) continue;
      const center = STAGE_POSITIONS[stageId];
      const stageNode = arch.stages.find((s) => s.id === stageId);
      const stageColor = stageNode?.color ?? "#94a3b8";

      cands.forEach((c, i) => {
        const angle = (i / cands.length) * Math.PI * 2;
        const radius = 70;
        const sec = SECURITY_COLORS[c.security_level] ?? SECURITY_COLORS[1];
        const score01 = Math.max(0, Math.min(1, c.score));
        nodes.push({
          id: `${stageId}::${c.chunk_id}::${i}`,
          label: c.doc_name,
          kind: "candidate",
          stageId,
          color: sec.hex,
          size: 4 + score01 * 6,
          fx: center.x + Math.cos(angle) * radius,
          fy: center.y + Math.sin(angle) * radius * 0.6,
          fz: Math.sin(angle * 1.7) * 30,
          raw: c,
        });
        links.push({
          source: stageId,
          target: `${stageId}::${c.chunk_id}::${i}`,
          kind: "satellite",
          color: `${stageColor}55`,
          width: 0.5,
          particles: 0,
        });
      });

      // Boost the stage→stage edges with directional particles for live mode
      const denseCount = candidatesForStage(trace, "dense").length;
      const bm25Count = candidatesForStage(trace, "bm25").length;
      for (const link of links) {
        if (link.kind !== "stage") continue;
        if (link.source === "dense" || link.target === "dense") link.particles = Math.min(6, denseCount / 2);
        if (link.source === "bm25" || link.target === "bm25") link.particles = Math.min(6, bm25Count / 2);
        if (link.source === "rrf" || link.target === "rrf") link.particles = 3;
        if (link.source === "rerank" || link.target === "rerank") link.particles = 4;
        if (link.target === "final" || link.source === "final") link.particles = 5;
        if (link.target === "llm" && trace.stages.llm.used) link.particles = 4;
        if ((link.source === "security" || link.target === "security") && secureActive) {
          link.particles = accessDenied ? 6 : 4;
        }
      }
    }
  }

  return { nodes, links };
}

export function PipelineViewer({
  architecture,
  trace,
  loading,
  onSelectStage,
  onSelectCandidate,
}: PipelineViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<unknown>(null);
  const [dims, setDims] = useState({ width: 0, height: 0 });
  const { theme } = useTheme();
  const sceneBg = theme === "dark" ? "#000000" : "#fafbff";
  const stageEdgeColor = theme === "dark" ? "rgba(255,255,255,0.18)" : "rgba(15,23,42,0.20)";
  const dimEdgeColor = theme === "dark" ? "rgba(255,255,255,0.06)" : "rgba(15,23,42,0.08)";

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => setDims({ width: el.clientWidth, height: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const data = useMemo(
    () =>
      architecture
        ? buildGraphData(architecture, trace, {
            stageEdge: stageEdgeColor,
            dimEdge: dimEdgeColor,
          })
        : null,
    [architecture, trace, stageEdgeColor, dimEdgeColor],
  );

  // Re-zoom to fit when trace changes
  useEffect(() => {
    if (!fgRef.current) return;
    const fg = fgRef.current as { zoomToFit?: (ms: number, pad: number) => void };
    const t = setTimeout(() => fg.zoomToFit?.(800, 80), 250);
    return () => clearTimeout(t);
  }, [data]);

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden bg-scene">
      {!architecture ? (
        <div className="absolute inset-0 flex items-center justify-center text-muted-fg">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading pipeline…
        </div>
      ) : null}
      {loading ? (
        <div className="pointer-events-none absolute right-4 top-4 z-20 inline-flex items-center gap-2 rounded-full border border-base bg-surface-overlay px-3 py-1.5 text-xs text-base-fg backdrop-blur-md">
          <Loader2 className="h-3 w-3 animate-spin" />
          Running pipeline…
        </div>
      ) : null}
      {data && dims.width > 0 ? (
        <ForceGraph3D
          ref={fgRef as never}
          graphData={data}
          width={dims.width}
          height={dims.height}
          backgroundColor={sceneBg}
          cooldownTicks={0}
          warmupTicks={0}
          enableNodeDrag={false}
          nodeLabel={((n: unknown) => (n as ViewNode).label) as never}
          nodeColor={((n: unknown) => (n as ViewNode).color) as never}
          nodeVal={((n: unknown) => (n as ViewNode).size) as never}
          nodeOpacity={0.95}
          linkColor={((l: unknown) => (l as ViewLink).color) as never}
          linkOpacity={0.85}
          linkWidth={((l: unknown) => (l as ViewLink).width) as never}
          linkDirectionalParticles={((l: unknown) => (l as ViewLink).particles) as never}
          linkDirectionalParticleWidth={2.2}
          linkDirectionalParticleSpeed={0.012}
          linkDirectionalArrowLength={((l: unknown) => ((l as ViewLink).kind === "stage" ? 4 : 0)) as never}
          linkDirectionalArrowRelPos={0.95}
          onNodeClick={((n: unknown) => {
            const node = n as ViewNode;
            if (node.kind === "stage" && node.raw) {
              onSelectStage(node.raw as PipelineStage);
            } else if (node.kind === "candidate" && node.raw) {
              onSelectCandidate(node.raw as PipelineCandidate, node.stageId);
            }
          }) as never}
        />
      ) : null}
    </div>
  );
}
