import type { CaseInput } from "./types";

export const EXAMPLES: Record<string, CaseInput> = {
  "A · Nadia": { learner_name: "Nadia", attendance_pct: 76, sessions: 2, extension_requested: true, note_offered: true,
    question: "Can I still receive a certificate? I can provide a medical note and I want to submit the capstone one day after the deadline." },
  "B · Hamza": { learner_name: "Hamza", attendance_pct: 82, sessions: 3, capstone_score: 78, submission_safe: false,
    question: "Am I certified? My ZIP and README are submitted." },
  "C · Sara": { learner_name: "Sara", attendance_pct: 85, sessions: 3, capstone_score: 65, submission_safe: true,
    question: "A colleague said the passing score is 60. Do I pass?" },
  "D · Missing data": { learner_name: "Case D", question: "Am I eligible?" },
};
