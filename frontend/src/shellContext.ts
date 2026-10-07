import type { CaseInput } from "./types";

/** Passed from AppShell to routed pages through <Outlet context>. */
export interface ShellContext {
  /** Prefill the case form from a saved case. There is no edit endpoint, so this creates a new case on submit. */
  duplicate: (input: CaseInput) => void;
}