export type Eligibility = "ELIGIBLE" | "INELIGIBLE" | "PENDING" | "ON_HOLD";
export type CaseStatus = "Open" | "Waiting for Learner" | "Waiting for Mentor" | "Ready for Review" | "Closed";
export type CheckResult = "PASS" | "FAIL" | "UNKNOWN";
export type ExtensionState = "not_requested" | "pending" | "approved" | "denied" | "late_request";

export const STATUSES: CaseStatus[] =
  ["Open", "Waiting for Learner", "Waiting for Mentor", "Ready for Review", "Closed"];

export interface CaseInput {
  learner_name: string;
  question: string;
  attendance_pct?: number | null;
  sessions?: number | null;
  capstone_score?: number | null;
  submission_safe?: boolean | null;
  extension_requested?: boolean | null;
  extension_approved?: boolean | null;
  makeup_approved?: boolean | null;
  missed_session_date?: string | null;
  note_offered?: boolean | null;
  note_verified?: boolean | null;
  case_date?: string;
}

export interface Check { rule: string; label: string; result: CheckResult; detail: string; source: string; }
export interface DeadlineInfo {
  standard_due: string; effective_due: string;
  extension_state: ExtensionState; can_still_request: boolean; is_past_due: boolean; note: string;
}
export interface RuleResult {
  eligibility: Eligibility; checks: Check[]; missing_facts: string[]; needs_approval: string[];
  hold: boolean; suggested_status: CaseStatus; next_action: string; next_actions: string[];
  warnings: string[]; deadline: DeadlineInfo; policy_ids: string[];
}
export interface SourceRef {
  id: string; version: string; effective: string; status: "CURRENT" | "SUPERSEDED";
  role: "evidence" | "superseded"; snippet: string; superseded_by: string | null;
}
export interface CaseOut {
  id: number; created_at: string;
  input: CaseInput;
  rule_result: RuleResult; sources: SourceRef[];
  llm_answer: string | null;
  llm_error: string | null;
  status: CaseStatus; case_note: string;
}
export interface CaseSummary {
  id: number; created_at: string; learner_name: string; eligibility: Eligibility; status: CaseStatus;
}
export interface FieldError { field: string; message: string; }
export interface Health { status: string; case_date: string; policies: string[]; llm_configured: boolean; }
