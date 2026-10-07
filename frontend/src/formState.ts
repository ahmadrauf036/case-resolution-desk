import type { CaseInput, FieldError } from "./types";

export type Tri = "none" | "approved" | "denied";

export interface FormState {
  learner_name: string;
  question: string;
  attendance_pct: string;
  sessions: string;
  capstone_score: string;
  submission: "unknown" | "safe" | "secret";
  extension: "none" | "requested";
  extension_decision: Tri;
  makeup: Tri;
  missed_session_date: string;
  note: "none" | "offered" | "verified";
  case_date: string;
}

export type FormErrors = Partial<Record<keyof FormState, string>>;

export const emptyForm = (caseDate = ""): FormState => ({
  learner_name: "", question: "",
  attendance_pct: "", sessions: "", capstone_score: "",
  submission: "unknown",
  extension: "none", extension_decision: "none",
  makeup: "none",
  missed_session_date: "",
  note: "none",
  case_date: caseDate,
});

const numOrNull = (s: string): number | null => (s.trim() === "" ? null : Number(s));
const triToBool = (t: Tri): boolean | null => (t === "approved" ? true : t === "denied" ? false : null);
const boolToTri = (b: boolean | null | undefined): Tri => (b === true ? "approved" : b === false ? "denied" : "none");

/** Form state -> API body. Empty/unknown is always null, never 0 or NaN. */
export function toPayload(f: FormState): CaseInput {
  const requested = f.extension === "requested";
  const payload: CaseInput = {
    learner_name: f.learner_name.trim(),
    question: f.question.trim(),
    attendance_pct: numOrNull(f.attendance_pct),
    sessions: numOrNull(f.sessions),
    capstone_score: numOrNull(f.capstone_score),
    submission_safe: f.submission === "safe" ? true : f.submission === "secret" ? false : null,
    extension_requested: requested ? true : null,
    extension_approved: requested ? triToBool(f.extension_decision) : null,
    makeup_approved: triToBool(f.makeup),
    missed_session_date: f.missed_session_date || null,
    note_offered: f.note === "none" ? null : true,
    note_verified: f.note === "verified" ? true : null,
  };
  if (f.case_date) payload.case_date = f.case_date;
  return payload;
}

/** API body -> form state (used by example buttons, and later by "Duplicate and edit"). */
export function fromInput(i: CaseInput, fallbackDate = ""): FormState {
  const n = (v: number | null | undefined) => (v === null || v === undefined ? "" : String(v));
  return {
    learner_name: i.learner_name,
    question: i.question,
    attendance_pct: n(i.attendance_pct),
    sessions: n(i.sessions),
    capstone_score: n(i.capstone_score),
    submission: i.submission_safe === true ? "safe" : i.submission_safe === false ? "secret" : "unknown",
    extension: i.extension_requested ? "requested" : "none",
    extension_decision: i.extension_requested ? boolToTri(i.extension_approved) : "none",
    makeup: boolToTri(i.makeup_approved),
    missed_session_date: i.missed_session_date ?? "",
    note: i.note_offered ? (i.note_verified ? "verified" : "offered") : "none",
    case_date: i.case_date ?? fallbackDate,
  };
}

function checkRange(value: string, min: number, max: number, integer: boolean, label: string): string | undefined {
  if (value.trim() === "") return undefined; // unknown is allowed
  const n = Number(value);
  if (Number.isNaN(n)) return `${label} must be a number.`;
  if (integer && !Number.isInteger(n)) return `${label} must be a whole number.`;
  if (n < min || n > max) return `${label} must be between ${min} and ${max}.`;
  return undefined;
}

/** Quick client-side feedback. The server's 422 messages are always shown too. */
export function validate(f: FormState): FormErrors {
  const e: FormErrors = {};
  const name = f.learner_name.trim();
  const q = f.question.trim();
  if (!name) e.learner_name = "Enter the learner's name.";
  else if (name.length > 100) e.learner_name = "Name must be 100 characters or fewer.";
  if (!q) e.question = "Enter the learner's question.";
  else if (q.length > 2000) e.question = "Question must be 2000 characters or fewer.";
  e.attendance_pct = checkRange(f.attendance_pct, 0, 100, false, "Attendance");
  e.sessions = checkRange(f.sessions, 0, 100, true, "Live sessions");
  e.capstone_score = checkRange(f.capstone_score, 0, 100, false, "Capstone score");
  (Object.keys(e) as (keyof FormState)[]).forEach((k) => e[k] === undefined && delete e[k]);
  return e;
}

/** Which form control a backend field name belongs to. */
const FIELD_TO_CONTROL: Record<string, keyof FormState> = {
  learner_name: "learner_name",
  question: "question",
  attendance_pct: "attendance_pct",
  sessions: "sessions",
  capstone_score: "capstone_score",
  submission_safe: "submission",
  extension_requested: "extension",
  extension_approved: "extension_decision",
  makeup_approved: "makeup",
  missed_session_date: "missed_session_date",
  note_offered: "note",
  note_verified: "note",
  case_date: "case_date",
};

/** Split server errors into per-control messages and a banner for anything unmatched. */
export function mapServerErrors(errors: FieldError[], detail: string): { fields: FormErrors; banner: string | null } {
  const fields: FormErrors = {};
  const unmatched: string[] = [];
  for (const err of errors) {
    const control = FIELD_TO_CONTROL[err.field];
    if (control) fields[control] = fields[control] ? `${fields[control]} ${err.message}` : err.message;
    else unmatched.push(err.message);
  }
  if (errors.length === 0) return { fields, banner: detail };
  return { fields, banner: unmatched.length ? unmatched.join(" ") : null };
}