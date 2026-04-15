"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Database, Loader2, RefreshCcw, Server } from "lucide-react";
import { DocumentCard } from "@/components/DocumentCard";
import { Button } from "@/components/ui/button";
import { fetchDocuments, fetchStatus, syncDocumentsToDb } from "@/lib/api";
import type { DocumentSummary } from "@/lib/api";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [qdrantPoints, setQdrantPoints] = useState<number | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [list, status] = await Promise.all([fetchDocuments(), fetchStatus()]);
      setDocs(list);
      const stats = (status as { collection_stats?: { points_count?: number } }).collection_stats;
      setQdrantPoints(stats?.points_count ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents");
      setDocs([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onSync = useCallback(async () => {
    setSyncing(true);
    setError(null);
    try {
      await syncDocumentsToDb();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }, [load]);

  const totalDocs = docs?.length ?? 0;
  const totalChunks = docs?.reduce((acc, d) => acc + d.chunk_count, 0) ?? 0;
  const totalChars = docs?.reduce((acc, d) => acc + d.char_count, 0) ?? 0;
  const needsSync =
    qdrantPoints !== null && totalChunks < qdrantPoints && totalDocs < 11;

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#0a0a0c]">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-0 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-emerald-600/10 blur-[120px]" />
      </div>

      <div className="relative mx-auto max-w-6xl px-6 py-12">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <Link
              href="/"
              className="mb-3 inline-flex items-center gap-1 text-xs text-white/50 transition-colors hover:text-white/80"
            >
              <ArrowLeft className="h-3 w-3" />
              Back to home
            </Link>
            <h1 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              Document Explorer
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-white/60">
              Every PDF in the corpus, broken down by chunks. Same data lives in Postgres
              (queryable in the Neon portal) and Qdrant (vectors).
            </p>
          </div>
          {needsSync ? (
            <Button onClick={onSync} disabled={syncing} variant="outline">
              {syncing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Syncing…
                </>
              ) : (
                <>
                  <RefreshCcw className="mr-2 h-4 w-4" /> Sync to Postgres
                </>
              )}
            </Button>
          ) : null}
        </div>

        <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <SummaryStat label="Documents" value={totalDocs} icon={<Database className="h-3 w-3" />} />
          <SummaryStat label="Chunks (Postgres)" value={totalChunks} icon={<Database className="h-3 w-3" />} />
          <SummaryStat
            label="Chunks (Qdrant)"
            value={qdrantPoints ?? "—"}
            icon={<Server className="h-3 w-3" />}
          />
          <SummaryStat label="Total chars" value={totalChars.toLocaleString()} />
        </div>

        {error ? (
          <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
            {error}
          </div>
        ) : null}

        {docs === null ? (
          <div className="flex h-64 items-center justify-center text-sm text-white/40">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Loading documents…
          </div>
        ) : docs.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-10 text-center text-sm text-white/60">
            <p className="mb-3">No documents in Postgres yet.</p>
            {qdrantPoints && qdrantPoints > 0 ? (
              <Button onClick={onSync} disabled={syncing}>
                {syncing ? "Syncing…" : `Backfill ${qdrantPoints} chunks from Qdrant`}
              </Button>
            ) : (
              <p className="text-white/40">Run /api/ingest first to load PDFs.</p>
            )}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {docs.map((doc) => (
              <DocumentCard key={doc.doc_slug} doc={doc} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function SummaryStat({
  label,
  value,
  icon,
}: {
  label: string;
  value: number | string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
      <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-white/40">
        {icon}
        {label}
      </div>
      <div className="mt-1 font-mono text-2xl font-semibold text-white">{value}</div>
    </div>
  );
}
