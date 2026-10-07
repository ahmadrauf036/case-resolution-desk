import type { CheckResult, Eligibility, ExtensionState } from "./types";

const fmt = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Karachi", dateStyle: "medium", timeStyle: "short" });

/** Format an ISO timestamp in Pakistan time, e.g. "9 Oct 2026, 17:00 PKT". */
export function formatPkt(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : `${fmt.format(d)} PKT`;
}

/** Result-screen wording. Never implies approval or a certificate. */
export const ELIGIBILITY_HEADLINE: Record<Eligibility, string> = {
  ELIGIBLE: "Meets requirements on record: human review required",
  INELIGIBLE: "Not eligible on current record",
  PENDING: "Pending: facts missing",
  ON_HOLD: "On hold: unsafe submission",
};

export const EXTENSION_LABEL: Record<ExtensionState, string> = {
  not_requested: "Not requested",
  pending: "Requested, not approved",
  approved: "Approved",
  denied: "Denied",
  late_request: "Requested too late",
};

export const CHECK_DISPLAY: Record<CheckResult, { icon: string; text: string; cls: string }> = {
  PASS: { icon: "✓", text: "Pass", cls: "text-emerald-300" },
  FAIL: { icon: "✕", text: "Fail", cls: "text-red-300" },
  UNKNOWN: { icon: "?", text: "Unknown", cls: "text-amber-300" },
};