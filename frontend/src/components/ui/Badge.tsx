import type { Eligibility } from "../../types";

const styles: Record<Eligibility, string> = {
  ELIGIBLE: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  INELIGIBLE: "bg-red-500/10 text-red-300 border-red-500/30",
  PENDING: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  ON_HOLD: "bg-amber-500/10 text-amber-300 border-amber-500/30",
};

/** Short label for lists. The longer result-screen wording is added in Phase 2. */
export const ELIGIBILITY_LABEL: Record<Eligibility, string> = {
  ELIGIBLE: "Eligible",
  INELIGIBLE: "Ineligible",
  PENDING: "Pending",
  ON_HOLD: "On hold",
};

export function Badge({ value }: { value: Eligibility }) {
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-sm font-medium ${styles[value]}`}>
      {ELIGIBILITY_LABEL[value]}
    </span>
  );
}

export function NeutralBadge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block rounded-full border border-white/15 px-2.5 py-0.5 text-sm text-white/80">
      {children}
    </span>
  );
}
