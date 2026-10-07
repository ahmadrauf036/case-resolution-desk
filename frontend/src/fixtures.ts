import type { CaseOut, SourceRef } from "./types";

/** MOCK DATA for the /preview page only. Shaped like the handoff's CaseOut; not real backend output. */
const KB01: SourceRef = { id: "KB-01", version: "v2", effective: "2026-09-01", status: "CURRENT", role: "evidence", superseded_by: null,
  snippet: "Certificate eligibility requires attendance of at least 80%, participation in at least 3 live sessions, and a passing capstone." };
const KB02: SourceRef = { id: "KB-02", version: "v3", effective: "2026-10-01", status: "CURRENT", role: "evidence", superseded_by: null,
  snippet: "The capstone is due Friday, 9 Oct 2026 at 17:00 PKT. A score of at least 70/100 is required to pass." };
const KB03: SourceRef = { id: "KB-03", version: "v2", effective: "2026-09-01", status: "CURRENT", role: "evidence", superseded_by: null,
  snippet: "API keys and other secrets must never be committed or included in the ZIP. If a secret is present, place the submission on hold." };
const KB05: SourceRef = { id: "KB-05", version: "v1", effective: "2026-05-01", status: "SUPERSEDED", role: "superseded", superseded_by: "KB-02 v3",
  snippet: "The capstone pass score was 60/100 and submissions were due at 18:00 PKT." };

const DUE = "2026-10-09T17:00:00+05:00";
const base = { id: 0, created_at: "2026-10-07T06:00:00Z", llm_error: null as string | null };

export const FIXTURES: Record<string, CaseOut> = {
  "A · Nadia": {
    ...base, id: 1, status: "Waiting for Mentor",
    input: { learner_name: "Nadia", question: "Can I still receive a certificate?", attendance_pct: 76, sessions: 2, extension_requested: true, note_offered: true },
    rule_result: {
      eligibility: "INELIGIBLE", hold: false, suggested_status: "Waiting for Mentor",
      checks: [
        { rule: "attendance", label: "Attendance at least 80%", result: "FAIL", detail: "76% recorded", source: "KB-01" },
        { rule: "sessions", label: "At least 3 live sessions", result: "FAIL", detail: "2 recorded", source: "KB-01" },
        { rule: "capstone", label: "Capstone score at least 70", result: "UNKNOWN", detail: "No score recorded", source: "KB-02" },
      ],
      missing_facts: ["Capstone score", "Verification of the medical note"],
      needs_approval: ["Mentor approval of the extension request", "Mentor approval of a makeup session"],
      next_action: "Ask the mentor to decide on the extension request and a makeup session.",
      next_actions: ["Ask the mentor to decide on the extension request and a makeup session.", "Verify the medical note.", "Record the capstone score once submitted."],
      warnings: [],
      deadline: { standard_due: DUE, effective_due: DUE, extension_state: "pending", can_still_request: true, is_past_due: false,
        note: "An extension request is not approval. The standard due date stays in force until a mentor approves." },
      policy_ids: ["KB-01", "KB-02"],
    },
    sources: [KB01, KB02],
    llm_answer: "Nadia does not meet the **attendance** or **live session** requirements on the current record (KB-01 v2). A medical note does not waive them.\nThe extension is requested, not approved, so the 9 Oct 17:00 PKT deadline still applies (KB-02 v3).",
    case_note: "Case #1 Nadia\nFacts: attendance 76%, sessions 2, extension requested.\nPolicies: KB-01 v2, KB-02 v3\nUnresolved: mentor decisions, note verification\nNext: ask mentor to decide.",
  },
  "B · Hamza": {
    ...base, id: 2, status: "Waiting for Learner",
    input: { learner_name: "Hamza", question: "Am I certified?", attendance_pct: 82, sessions: 3, capstone_score: 78, submission_safe: false },
    rule_result: {
      eligibility: "ON_HOLD", hold: true, suggested_status: "Waiting for Learner",
      checks: [
        { rule: "attendance", label: "Attendance at least 80%", result: "PASS", detail: "82% recorded", source: "KB-01" },
        { rule: "sessions", label: "At least 3 live sessions", result: "PASS", detail: "3 recorded", source: "KB-01" },
        { rule: "capstone", label: "Capstone score at least 70", result: "PASS", detail: "78 recorded", source: "KB-02" },
        { rule: "submission", label: "Submission is safe to review", result: "FAIL", detail: "A secret was found in the ZIP", source: "KB-03" },
      ],
      missing_facts: [], needs_approval: [],
      next_action: "Ask the learner to remove the secret, rotate the key, and send a clean replacement ZIP.",
      next_actions: ["Ask the learner to remove the secret, rotate the key, and send a clean replacement ZIP."],
      warnings: ["Numbers meet the thresholds, but no pass decision can be issued until the submission is safe."],
      deadline: { standard_due: DUE, effective_due: DUE, extension_state: "not_requested", can_still_request: true, is_past_due: false, note: "" },
      policy_ids: ["KB-03", "KB-01", "KB-02"],
    },
    sources: [KB03, KB01],
    llm_answer: "The submission is **on hold** because a key was found in the ZIP (KB-03 v2). No pass decision can be issued yet.",
    case_note: "Case #2 Hamza\nFacts: attendance 82%, sessions 3, score 78, secret found.\nPolicies: KB-03 v2, KB-01 v2\nUnresolved: clean replacement\nNext: remove secret, rotate key.",
  },
  "C · Sara": {
    ...base, id: 3, status: "Ready for Review",
    input: { learner_name: "Sara", question: "A colleague said the passing score is 60. Do I pass?", attendance_pct: 85, sessions: 3, capstone_score: 65, submission_safe: true },
    rule_result: {
      eligibility: "INELIGIBLE", hold: false, suggested_status: "Ready for Review",
      checks: [
        { rule: "attendance", label: "Attendance at least 80%", result: "PASS", detail: "85% recorded", source: "KB-01" },
        { rule: "sessions", label: "At least 3 live sessions", result: "PASS", detail: "3 recorded", source: "KB-01" },
        { rule: "capstone", label: "Capstone score at least 70", result: "FAIL", detail: "65 is below the current threshold of 70", source: "KB-02" },
      ],
      missing_facts: [], needs_approval: [],
      next_action: "Tell the learner the current pass score is 70, so 65 does not pass.",
      next_actions: ["Tell the learner the current pass score is 70, so 65 does not pass."],
      warnings: ["The 60-point rule (KB-05) is superseded and was not used."],
      deadline: { standard_due: DUE, effective_due: DUE, extension_state: "not_requested", can_still_request: true, is_past_due: false, note: "" },
      policy_ids: ["KB-02", "KB-01"],
    },
    sources: [KB02, KB01, KB05],
    llm_answer: "The current pass score is **70** (KB-02 v3). The 60-point rule in KB-05 is superseded, so a score of 65 does not pass.",
    case_note: "Case #3 Sara\nFacts: attendance 85%, sessions 3, score 65.\nPolicies: KB-02 v3, KB-01 v2\nUnresolved: none\nNext: explain the 70 threshold.",
  },
  "D · Missing data": {
    ...base, id: 4, status: "Waiting for Learner",
    input: { learner_name: "Case D", question: "Am I eligible?" },
    rule_result: {
      eligibility: "PENDING", hold: false, suggested_status: "Waiting for Learner",
      checks: [
        { rule: "attendance", label: "Attendance at least 80%", result: "UNKNOWN", detail: "Not recorded", source: "KB-01" },
        { rule: "sessions", label: "At least 3 live sessions", result: "UNKNOWN", detail: "Not recorded", source: "KB-01" },
        { rule: "capstone", label: "Capstone score at least 70", result: "UNKNOWN", detail: "Not recorded", source: "KB-02" },
      ],
      missing_facts: ["Attendance percentage", "Number of live sessions", "Capstone score", "Submission safety check"],
      needs_approval: [],
      next_action: "Collect attendance, live sessions, capstone score and the submission check.",
      next_actions: ["Collect attendance, live sessions, capstone score and the submission check."],
      warnings: [],
      deadline: { standard_due: DUE, effective_due: DUE, extension_state: "not_requested", can_still_request: true, is_past_due: false, note: "" },
      policy_ids: ["KB-01", "KB-02"],
    },
    sources: [KB01, KB02],
    llm_answer: "Eligibility cannot be decided yet. Four facts are missing.",
    case_note: "Case #4 Case D\nFacts: none recorded.\nPolicies: KB-01 v2, KB-02 v3\nUnresolved: four missing facts\nNext: collect them.",
  },
  "A · AI failed": {
    ...base, id: 5, status: "Waiting for Mentor",
    input: { learner_name: "Nadia", question: "Can I still receive a certificate?", attendance_pct: 76, sessions: 2, extension_requested: true, note_offered: true },
    llm_error: "The AI provider is rate limited (429). Try again shortly.",
    rule_result: {
      eligibility: "INELIGIBLE", hold: false, suggested_status: "Waiting for Mentor",
      checks: [{ rule: "attendance", label: "Attendance at least 80%", result: "FAIL", detail: "76% recorded", source: "KB-01" }],
      missing_facts: [], needs_approval: ["Mentor approval of the extension request"],
      next_action: "Ask the mentor to decide on the extension request.", next_actions: [],
      warnings: [],
      deadline: { standard_due: DUE, effective_due: DUE, extension_state: "pending", can_still_request: true, is_past_due: false, note: "" },
      policy_ids: ["KB-01", "KB-02"],
    },
    sources: [KB01, KB02],
    llm_answer: "Rule-based summary: attendance is 76%, below the 80% requirement (KB-01 v2). The extension is requested, not approved.",
    case_note: "Case #5 Nadia (AI unavailable)",
  },
};