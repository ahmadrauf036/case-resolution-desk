import { useState } from "react";
import type { SourceRef } from "../types";

export function SourceChips({ sources }: { sources: SourceRef[] }) {
  const [open, setOpen] = useState<string | null>(null);
  if (sources.length === 0) return <p className="text-sm text-muted">No sources were used.</p>;

  return (
    <ul className="space-y-2">
      {sources.map((s) => {
        const key = `${s.id}-${s.version}`;
        const expanded = open === key;
        const superseded = s.role === "superseded";
        return (
          <li key={key}>
            <button
              type="button"
              aria-expanded={expanded}
              onClick={() => setOpen(expanded ? null : key)}
              className={`rounded-full border px-3 py-1 text-sm ${
                superseded
                  ? "border-white/10 text-white/50 line-through"
                  : "border-white/25 text-white hover:bg-white/5"
              }`}
            >
              {s.id} {s.version}
            </button>
            {superseded && (
              <span className="ml-2 text-sm text-amber-300">
                Superseded by {s.superseded_by ?? "a newer policy"}, not valid for this case
              </span>
            )}
            {expanded && (
              <div className={`mt-2 rounded-lg border border-white/10 p-3 text-sm ${superseded ? "text-white/55" : "text-white/80"}`}>
                <p className="mb-1 text-muted">
                  {s.status === "CURRENT" ? "Current" : "Superseded"}, effective {s.effective}
                </p>
                <p className="whitespace-pre-wrap wrap-break-word">{s.snippet}</p>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}