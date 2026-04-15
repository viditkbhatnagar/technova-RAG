"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Hash, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { SECURITY_COLORS } from "@/lib/types";
import type { ChunkRecord } from "@/lib/api";

const PREVIEW_CHARS = 280;

interface ChunkViewerProps {
  chunk: ChunkRecord;
}

export function ChunkViewer({ chunk }: ChunkViewerProps) {
  const [expanded, setExpanded] = useState(false);
  const sec = SECURITY_COLORS[chunk.security_level] ?? SECURITY_COLORS[1];
  const truncated =
    chunk.text.length > PREVIEW_CHARS
      ? chunk.text.slice(0, PREVIEW_CHARS) + "…"
      : chunk.text;

  return (
    <div className="rounded-lg border border-base bg-surface-1 p-4 shadow-card transition-colors hover:border-strong">
      <div className="flex flex-wrap items-center gap-1.5">
        <Badge
          variant="secondary"
          className="bg-surface-2 font-mono text-[10px] text-muted-fg"
        >
          #{chunk.chunk_index}
        </Badge>
        <Badge
          variant="outline"
          className="border-base font-mono text-[10px] text-muted-fg"
        >
          <FileText className="mr-1 h-3 w-3" />
          p.{chunk.page_number}
        </Badge>
        <Badge
          variant="outline"
          className="border-base font-mono text-[10px] text-muted-fg"
        >
          <Hash className="mr-1 h-3 w-3" />
          {chunk.char_count} chars
        </Badge>
        <Badge
          className={`${sec.bg} ${sec.text} ${sec.border} border text-[10px] font-semibold`}
        >
          {sec.label}
        </Badge>
        <span className="ml-auto truncate font-mono text-[10px] text-ghost">
          {chunk.chunk_id}
        </span>
      </div>
      <Separator className="my-3 bg-base" />
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-base-fg">
        {expanded ? chunk.text : truncated}
      </p>
      {chunk.text.length > PREVIEW_CHARS ? (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-3 inline-flex items-center gap-1 text-xs text-faint transition-colors hover:text-strong"
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
      <p className="mt-3 truncate font-mono text-[10px] text-ghost">
        sha256: {chunk.content_hash}
      </p>
    </div>
  );
}
