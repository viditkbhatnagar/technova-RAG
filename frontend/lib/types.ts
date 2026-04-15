import type { ChunkResult, Role } from "./api";

export type { ChunkResult, Role };

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChunkResult[];
  accessDenied?: boolean;
  accessDeniedMessage?: string | null;
  restrictedDocCount?: number;
  timestamp: Date;
}

export const SECURITY_COLORS: Record<number, { label: string; bg: string; text: string; border: string; hex: string }> = {
  0: { label: "PUBLIC", bg: "bg-emerald-500/15", text: "text-emerald-300", border: "border-emerald-500/40", hex: "#10b981" },
  1: { label: "INTERNAL", bg: "bg-blue-500/15", text: "text-blue-300", border: "border-blue-500/40", hex: "#3b82f6" },
  2: { label: "CONFIDENTIAL", bg: "bg-orange-500/15", text: "text-orange-300", border: "border-orange-500/40", hex: "#f97316" },
  3: { label: "RESTRICTED", bg: "bg-red-500/15", text: "text-red-300", border: "border-red-500/40", hex: "#ef4444" },
};

export const ENTITY_COLORS: Record<string, string> = {
  PERSON: "#a855f7",
  POLICY: "#14b8a6",
  AMOUNT: "#f59e0b",
  MONEY: "#f59e0b",
  DATE: "#06b6d4",
  DURATION: "#06b6d4",
  ORG: "#ec4899",
  DEPARTMENT: "#ec4899",
  ROLE: "#ffffff",
  ROLE_LEVEL: "#ffffff",
  DEFAULT: "#94a3b8",
};

export const ROLE_META: Record<Role, { label: string; clearance: number; docCount: number; description: string }> = {
  employee: {
    label: "Employee",
    clearance: 1,
    docCount: 5,
    description: "Sees PUBLIC + INTERNAL documents",
  },
  manager: {
    label: "Manager",
    clearance: 2,
    docCount: 8,
    description: "Sees PUBLIC + INTERNAL + CONFIDENTIAL documents",
  },
  admin: {
    label: "Admin",
    clearance: 3,
    docCount: 11,
    description: "Sees all documents including RESTRICTED",
  },
};
