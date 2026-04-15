"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { use } from "react";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Database,
  FileText,
  Hash,
  Layers,
  Loader2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChunkViewer } from "@/components/ChunkViewer";
import { ThemeToggle } from "@/components/ThemeToggle";
import { fetchDocument, fetchDocumentChunks } from "@/lib/api";
import type { ChunkRecord, DocumentDetail } from "@/lib/api";
import { SECURITY_COLORS } from "@/lib/types";

const PAGE_SIZE = 50;

export default function DocumentDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [chunks, setChunks] = useState<ChunkRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const sec = doc ? SECURITY_COLORS[doc.security_level] ?? SECURITY_COLORS[1] : null;

  useEffect(() => {
    let cancel = false;
    setError(null);
    fetchDocument(slug)
      .then((d) => {
        if (!cancel) setDoc(d);
      })
      .catch((e) => {
        if (!cancel) setError(e instanceof Error ? e.message : "Failed to load document");
      });
    return () => {
      cancel = true;
    };
  }, [slug]);

  const loadChunks = useCallback(async () => {
    setLoading(true);
    try {
      const page = await fetchDocumentChunks(slug, { limit: PAGE_SIZE, offset });
      setChunks(page.items);
      setTotal(page.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load chunks");
    } finally {
      setLoading(false);
    }
  }, [slug, offset]);

  useEffect(() => {
    void loadChunks();
  }, [loadChunks]);

  const sql = useMemo(
    () => `SELECT * FROM chunks WHERE doc_slug = '${slug}' ORDER BY chunk_index;`,
    [slug],
  );

  const pageEnd = Math.min(offset + PAGE_SIZE, total);
  const canPrev = offset > 0;
  const canNext = pageEnd < total;

  return (
    <main className="relative min-h-screen overflow-hidden bg-app text-base-fg">
      <div className="pointer-events-none absolute inset-0">
        {sec ? (
          <div
            className="absolute left-1/2 top-0 h-[500px] w-[500px] -translate-x-1/2 rounded-full blur-[120px]"
            style={{ background: `${sec.hex}1a` }}
          />
        ) : null}
      </div>

      <div className="absolute right-5 top-5 z-10">
        <ThemeToggle />
      </div>

      <div className="relative mx-auto max-w-4xl px-6 py-12">
        <Link
          href="/documents"
          className="mb-6 inline-flex items-center gap-1 text-xs text-faint transition-colors hover:text-strong"
        >
          <ArrowLeft className="h-3 w-3" />
          All documents
        </Link>

        {error ? (
          <div className="mb-6 rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-700 dark:text-red-200">
            {error}
          </div>
        ) : null}

        {doc ? (
          <>
            <div className="mb-8 rounded-2xl border border-base bg-surface-1 p-6 shadow-card">
              <div className="mb-3 flex flex-wrap items-center gap-1.5">
                {sec ? (
                  <Badge className={`${sec.bg} ${sec.text} ${sec.border} border text-[10px] font-semibold`}>
                    {sec.label}
                  </Badge>
                ) : null}
                <Badge variant="outline" className="border-base text-[10px] text-muted-fg">
                  {doc.domain}
                </Badge>
              </div>
              <h1 className="text-balance text-3xl font-semibold tracking-tight text-strong">
                {doc.doc_name}
              </h1>
              <p className="mt-1 font-mono text-xs text-faint">{doc.file_name}</p>
              <div className="mt-5 grid grid-cols-3 gap-3">
                <Stat icon={<FileText className="h-3 w-3" />} label="Pages" value={doc.page_count} />
                <Stat icon={<Layers className="h-3 w-3" />} label="Chunks" value={doc.chunk_count} />
                <Stat icon={<Hash className="h-3 w-3" />} label="Chars" value={doc.char_count.toLocaleString()} />
              </div>
              <div className="mt-5 rounded-lg border border-soft bg-surface-3 p-3">
                <div className="mb-1 flex items-center gap-1 text-[10px] uppercase tracking-wider text-faint">
                  <Database className="h-3 w-3" /> Open in Neon
                </div>
                <code className="block whitespace-pre-wrap font-mono text-[11px] text-muted-fg">
                  {sql}
                </code>
              </div>
            </div>

            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-fg">
                Chunks
              </h2>
              <span className="font-mono text-xs text-faint">
                {total === 0 ? "—" : `${offset + 1}–${pageEnd} of ${total}`}
              </span>
            </div>

            {loading ? (
              <div className="flex h-40 items-center justify-center text-sm text-faint">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading chunks…
              </div>
            ) : (
              <div className="space-y-3">
                {chunks.map((c) => (
                  <ChunkViewer key={c.chunk_id} chunk={c} />
                ))}
              </div>
            )}

            {total > PAGE_SIZE ? (
              <div className="mt-6 flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!canPrev}
                  onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                >
                  <ChevronLeft className="mr-1 h-3 w-3" /> Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!canNext}
                  onClick={() => setOffset((o) => o + PAGE_SIZE)}
                >
                  Next <ChevronRight className="ml-1 h-3 w-3" />
                </Button>
              </div>
            ) : null}
          </>
        ) : !error ? (
          <div className="flex h-64 items-center justify-center text-sm text-faint">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : null}
      </div>
    </main>
  );
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
}) {
  return (
    <div className="rounded-md border border-soft bg-surface-3 px-3 py-2">
      <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-faint">
        {icon}
        {label}
      </div>
      <div className="mt-1 font-mono text-lg text-strong">{value}</div>
    </div>
  );
}
