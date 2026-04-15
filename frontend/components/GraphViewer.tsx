"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { X, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { fetchGraph, type GraphData, type GraphEdge, type GraphNode } from "@/lib/api";
import { ENTITY_COLORS, SECURITY_COLORS } from "@/lib/types";
import { useTheme } from "@/lib/theme";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), { ssr: false });

interface ForceNode extends GraphNode {
  val?: number;
  color?: string;
}

interface ForceLink extends GraphEdge {
  color?: string;
}

function nodeColor(node: GraphNode): string {
  if (node.type === "document") {
    const lvl = typeof node.security_level === "number" ? node.security_level : 1;
    return SECURITY_COLORS[lvl]?.hex ?? "#3b82f6";
  }
  if (node.type === "chunk") return "#94a3b8";
  if (node.type === "entity") {
    const et = (node.entity_type || "DEFAULT").toUpperCase();
    return ENTITY_COLORS[et] ?? ENTITY_COLORS.DEFAULT;
  }
  return "#94a3b8";
}

function nodeSize(node: GraphNode): number {
  if (node.type === "document") return 15;
  if (node.type === "entity") return 8;
  return 5;
}

function edgeColor(type: string): string {
  if (type === "contains") return "rgba(255,255,255,0.08)";
  if (type === "mentions") return "rgba(148,163,184,0.25)";
  return "rgba(167,139,250,0.45)";
}

interface SelectedEdge {
  source: GraphNode;
  target: GraphNode;
  type: string;
  label: string;
  weight?: number;
}

export function GraphViewer() {
  const [data, setData] = useState<GraphData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<SelectedEdge | null>(null);
  const [dims, setDims] = useState({ width: 0, height: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();
  const sceneBg = theme === "dark" ? "#000000" : "#fafbff";

  useEffect(() => {
    let cancelled = false;
    fetchGraph()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load graph");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => setDims({ width: el.clientWidth, height: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const graphData = useMemo(() => {
    if (!data) return { nodes: [] as ForceNode[], links: [] as ForceLink[] };
    const nodes: ForceNode[] = data.nodes.map((n) => ({
      ...n,
      val: nodeSize(n),
      color: nodeColor(n),
    }));
    const links: ForceLink[] = data.edges.map((e) => ({
      ...e,
      color: edgeColor(e.type),
    }));
    return { nodes, links };
  }, [data]);

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden bg-scene">
      {!data && !error ? (
        <div className="absolute inset-0 flex items-center justify-center text-muted-fg">
          <div className="flex items-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Loading knowledge graph…</span>
          </div>
        </div>
      ) : null}
      {error ? (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="max-w-md rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-700 dark:text-red-200">
            {error}
          </div>
        </div>
      ) : null}
      {data && dims.width > 0 ? (
        <ForceGraph3D
          graphData={graphData}
          width={dims.width}
          height={dims.height}
          backgroundColor={sceneBg}
          nodeLabel={((n: unknown) => {
            const node = n as ForceNode;
            return `${node.label} (${node.type})`;
          }) as never}
          nodeColor={((n: unknown) => (n as ForceNode).color || "#94a3b8") as never}
          nodeVal={((n: unknown) => (n as ForceNode).val || 5) as never}
          nodeOpacity={0.95}
          linkColor={((l: unknown) => (l as ForceLink).color || "rgba(255,255,255,0.1)") as never}
          linkOpacity={0.6}
          linkWidth={((l: unknown) => ((l as ForceLink).type === "relationship" ? 1.2 : 0.4)) as never}
          linkDirectionalParticles={((l: unknown) => {
            const type = (l as ForceLink).type;
            return type === "contains" || type === "mentions" ? 0 : 2;
          }) as never}
          linkDirectionalParticleWidth={1.5}
          linkDirectionalArrowLength={((l: unknown) => {
            const type = (l as ForceLink).type;
            return type === "contains" || type === "mentions" ? 0 : 3;
          }) as never}
          linkDirectionalArrowRelPos={0.9}
          linkLabel={((l: unknown) => {
            const e = l as ForceLink & { source: unknown; target: unknown };
            const s = typeof e.source === "object" && e.source ? (e.source as GraphNode).label : String(e.source);
            const t = typeof e.target === "object" && e.target ? (e.target as GraphNode).label : String(e.target);
            const w = (e as { weight?: number }).weight;
            return `${s} → ${e.label}${w ? ` (×${w})` : ""} → ${t}`;
          }) as never}
          enableNodeDrag={false}
          onNodeClick={((n: unknown) => {
            setSelected(n as ForceNode);
            setSelectedEdge(null);
          }) as never}
          onLinkClick={((l: unknown) => {
            const e = l as ForceLink & { source: unknown; target: unknown; weight?: number };
            const source = typeof e.source === "object" ? (e.source as GraphNode) : undefined;
            const target = typeof e.target === "object" ? (e.target as GraphNode) : undefined;
            if (!source || !target) return;
            setSelectedEdge({
              source,
              target,
              type: e.type,
              label: e.label,
              weight: e.weight,
            });
            setSelected(null);
          }) as never}
          onBackgroundClick={(() => {
            setSelected(null);
            setSelectedEdge(null);
          }) as never}
        />
      ) : null}
      {selected ? <InfoPanel node={selected} onClose={() => setSelected(null)} /> : null}
      {selectedEdge ? (
        <EdgePanel edge={selectedEdge} onClose={() => setSelectedEdge(null)} />
      ) : null}
      {data ? <StatsBar data={data} /> : null}
      {data ? <Legend /> : null}
    </div>
  );
}

function InfoPanel({ node, onClose }: { node: GraphNode; onClose: () => void }) {
  const sec =
    typeof node.security_level === "number" ? SECURITY_COLORS[node.security_level] : null;
  return (
    <div className="absolute right-4 top-4 w-80 overflow-hidden rounded-xl border border-base bg-surface-overlay text-base-fg shadow-card backdrop-blur-md">
      <div className="flex items-start justify-between gap-2 border-b border-soft p-4">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wider text-faint">{node.type}</div>
          <div className="mt-0.5 truncate text-base font-semibold text-strong">{node.label}</div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1 text-faint transition-colors hover:bg-surface-2 hover:text-strong"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="space-y-3 p-4 text-sm">
        {sec ? (
          <Row label="Security">
            <Badge className={`${sec.bg} ${sec.text} ${sec.border} border text-[10px] font-semibold`}>
              {sec.label}
            </Badge>
          </Row>
        ) : null}
        {node.domain ? <Row label="Domain">{String(node.domain)}</Row> : null}
        {node.entity_type ? <Row label="Entity Type">{String(node.entity_type)}</Row> : null}
        {typeof node.mentions === "number" ? (
          <Row label="Mentions">{node.mentions}</Row>
        ) : null}
        {typeof node.page_number === "number" ? (
          <Row label="Page">{node.page_number}</Row>
        ) : null}
        {node.parent_doc ? (
          <Row label="Parent Doc">
            <span className="truncate text-muted-fg">{String(node.parent_doc)}</span>
          </Row>
        ) : null}
        {node.text_preview ? (
          <>
            <Separator className="bg-base" />
            <div className="text-xs text-muted-fg">Preview</div>
            <p className="text-xs leading-relaxed text-base-fg">{String(node.text_preview)}</p>
          </>
        ) : null}
        {node.metadata && typeof node.metadata === "object" ? (
          <>
            <Separator className="bg-base" />
            <div className="space-y-1 text-xs text-muted-fg">
              {Object.entries(node.metadata as Record<string, unknown>).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-2">
                  <span className="text-faint">{k}</span>
                  <span className="truncate">{String(v)}</span>
                </div>
              ))}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

function EdgePanel({ edge, onClose }: { edge: SelectedEdge; onClose: () => void }) {
  const prettyType = edge.type.replace(/_/g, " ");
  return (
    <div className="absolute right-4 top-4 w-80 overflow-hidden rounded-xl border border-base bg-surface-overlay text-base-fg shadow-card backdrop-blur-md">
      <div className="flex items-start justify-between gap-2 border-b border-soft p-4">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wider text-faint">Relationship</div>
          <div className="mt-0.5 truncate text-base font-semibold text-strong">{prettyType}</div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1 text-faint transition-colors hover:bg-surface-2 hover:text-strong"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="space-y-3 p-4 text-sm">
        <Row label="Source">
          <EndpointChip node={edge.source} />
        </Row>
        <Row label="Predicate">
          <span className="font-mono text-xs text-violet-500 dark:text-violet-300">{edge.label}</span>
        </Row>
        <Row label="Target">
          <EndpointChip node={edge.target} />
        </Row>
        {typeof edge.weight === "number" ? (
          <Row label="Weight">
            <span className="font-mono text-xs text-muted-fg">×{edge.weight}</span>
          </Row>
        ) : null}
        <Separator className="bg-base" />
        <p className="text-xs leading-relaxed text-muted-fg">
          {edge.type === "contains"
            ? "Document node contains this chunk."
            : edge.type === "mentions"
            ? "This chunk mentions the entity."
            : edge.type === "co_occurs_with"
            ? `Both entities appear in the same chunk${
                edge.weight ? ` across ${edge.weight} chunk(s)` : ""
              }.`
            : "Entity-to-entity relationship extracted from the corpus."}
        </p>
      </div>
    </div>
  );
}

function EndpointChip({ node }: { node: GraphNode }) {
  const color =
    node.type === "document"
      ? SECURITY_COLORS[
          typeof node.security_level === "number" ? node.security_level : 1
        ]?.hex
      : node.type === "chunk"
      ? "#94a3b8"
      : ENTITY_COLORS[(node.entity_type || "DEFAULT").toUpperCase()] ?? ENTITY_COLORS.DEFAULT;
  return (
    <span className="inline-flex max-w-[12rem] items-center gap-1.5">
      <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: color }} />
      <span className="truncate text-xs text-base-fg">{node.label}</span>
    </span>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-xs uppercase tracking-wider text-faint">{label}</span>
      <span className="text-sm">{children}</span>
    </div>
  );
}

function StatsBar({ data }: { data: GraphData }) {
  const s = data.stats;
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center p-4">
      <div className="pointer-events-auto flex gap-6 rounded-full border border-base bg-surface-overlay px-6 py-2 text-xs text-muted-fg shadow-card backdrop-blur-md">
        <Stat label="Documents" value={s.total_documents} />
        <Stat label="Chunks" value={s.total_chunks} />
        <Stat label="Entities" value={s.total_entities} />
        <Stat label="Relationships" value={s.total_relationships} />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="uppercase tracking-wider text-faint">{label}</span>
      <span className="font-mono font-semibold text-strong">{value}</span>
    </div>
  );
}

function Legend() {
  return (
    <div className="absolute left-4 top-4 space-y-2 rounded-xl border border-base bg-surface-overlay p-3 text-xs text-muted-fg shadow-card backdrop-blur-md">
      <div className="font-semibold uppercase tracking-wider text-faint">Nodes</div>
      <div className="space-y-1">
        {[0, 1, 2, 3].map((lvl) => {
          const s = SECURITY_COLORS[lvl];
          return (
            <div key={lvl} className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: s.hex }}
              />
              <span>Doc · {s.label}</span>
            </div>
          );
        })}
        <div className="flex items-center gap-2">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-slate-400" />
          <span>Chunk</span>
        </div>
        {[
          ["PERSON", ENTITY_COLORS.PERSON],
          ["POLICY", ENTITY_COLORS.POLICY],
          ["AMOUNT", ENTITY_COLORS.AMOUNT],
          ["DATE", ENTITY_COLORS.DATE],
          ["ORG", ENTITY_COLORS.ORG],
        ].map(([label, hex]) => (
          <div key={label} className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: hex }} />
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
