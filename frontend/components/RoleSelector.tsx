"use client";

import { ShieldCheck } from "lucide-react";
import type { Role } from "@/lib/api";
import { ROLE_META } from "@/lib/types";

interface RoleSelectorProps {
  role: Role | null;
  onChange: (role: Role) => void;
}

const ORDER: Role[] = ["employee", "manager", "admin"];

export function RoleSelector({ role, onChange }: RoleSelectorProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-2 text-sm text-muted-fg">
        <ShieldCheck className="h-4 w-4 text-violet-500 dark:text-violet-400" />
        <span>Select a role to begin. Changing role clears the conversation.</span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {ORDER.map((r) => {
          const meta = ROLE_META[r];
          const active = role === r;
          return (
            <button
              key={r}
              type="button"
              onClick={() => onChange(r)}
              className={`rounded-lg border px-3 py-2 text-left transition-all ${
                active
                  ? "border-violet-400/60 bg-violet-500/15 shadow-[0_0_0_1px_rgba(167,139,250,0.3)]"
                  : "border-base bg-surface-1 hover:border-strong hover:bg-surface-2"
              }`}
            >
              <div className={`text-sm font-semibold ${active ? "text-strong" : "text-base-fg"}`}>
                {meta.label}
              </div>
              <div className="mt-0.5 font-mono text-[10px] text-faint">
                Clearance L{meta.clearance} · {meta.docCount} docs
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
