import { ShieldAlert } from "lucide-react";

interface AccessDeniedProps {
  message?: string | null;
  restrictedDocCount?: number;
}

export function AccessDenied({ message, restrictedDocCount }: AccessDeniedProps) {
  const count = restrictedDocCount ?? 0;
  return (
    <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-amber-800 dark:text-amber-100">
      <div className="flex items-start gap-3">
        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-300" />
        <div className="space-y-2 text-sm leading-relaxed">
          <div className="font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-200">
            Access Restricted
          </div>
          {message ? <p>{message}</p> : null}
          {count > 0 ? (
            <p className="opacity-80">
              ⚠️ Relevant information exists in {count} restricted document
              {count === 1 ? "" : "s"}. Contact your department head for elevated access.
            </p>
          ) : (
            <p className="opacity-80">
              Contact your department head for elevated access.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
