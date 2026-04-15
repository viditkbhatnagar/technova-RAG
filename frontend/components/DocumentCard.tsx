import Link from "next/link";
import { ArrowRight, FileText, Layers, Hash } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { SECURITY_COLORS } from "@/lib/types";
import type { DocumentSummary } from "@/lib/api";

interface DocumentCardProps {
  doc: DocumentSummary;
}

export function DocumentCard({ doc }: DocumentCardProps) {
  const sec = SECURITY_COLORS[doc.security_level] ?? SECURITY_COLORS[1];
  return (
    <Link
      href={`/documents/${doc.doc_slug}`}
      className="group relative flex flex-col rounded-2xl border border-white/10 bg-white/5 p-5 transition-all hover:-translate-y-0.5 hover:border-white/25 hover:bg-white/[0.07]"
    >
      <div
        className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: `radial-gradient(600px circle at 50% 0%, ${sec.hex}22, transparent 60%)`,
        }}
      />
      <div className="relative flex flex-1 flex-col">
        <div className="mb-3 flex flex-wrap items-center gap-1.5">
          <Badge
            className={`${sec.bg} ${sec.text} ${sec.border} border text-[10px] font-semibold`}
          >
            {sec.label}
          </Badge>
          <Badge
            variant="outline"
            className="border-white/20 text-[10px] text-white/60"
          >
            {doc.domain}
          </Badge>
        </div>
        <h3 className="text-balance text-lg font-semibold leading-tight text-white">
          {doc.doc_name}
        </h3>
        <p className="mt-1 truncate font-mono text-[11px] text-white/40">
          {doc.file_name}
        </p>
        <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
          <Stat icon={<FileText className="h-3 w-3" />} label="Pages" value={doc.page_count} />
          <Stat icon={<Layers className="h-3 w-3" />} label="Chunks" value={doc.chunk_count} />
          <Stat icon={<Hash className="h-3 w-3" />} label="Chars" value={doc.char_count.toLocaleString()} />
        </div>
        <div className="mt-5 flex items-center justify-between text-xs text-white/50">
          <span className="font-mono text-[10px] text-white/30">{doc.doc_slug}</span>
          <span className="inline-flex items-center gap-1 text-white/60 transition-colors group-hover:text-white">
            Open
            <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
          </span>
        </div>
      </div>
    </Link>
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
    <div className="rounded-md border border-white/10 bg-white/5 px-2 py-1.5">
      <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-white/40">
        {icon}
        {label}
      </div>
      <div className="mt-0.5 font-mono text-sm text-white/90">{value}</div>
    </div>
  );
}
