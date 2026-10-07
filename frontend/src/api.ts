import type { CaseInput, CaseOut, CaseStatus, CaseSummary, FieldError, Health } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  fields: FieldError[];
  constructor(status: number, message: string, fields: FieldError[] = []) {
    super(message);
    this.status = status;
    this.fields = fields;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      ...init,
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(30_000),
    });
  } catch {
    throw new ApiError(0, "Cannot reach the server, or the request took too long. Check that the backend is running.");
  }
  if (!res.ok) {
    let body: { detail?: unknown; errors?: FieldError[] } | null = null;
    try { body = await res.json(); } catch { /* ignore */ }
    throw new ApiError(
      res.status,
      typeof body?.detail === "string" ? body.detail : "Unexpected error.",
      body?.errors ?? [],
    );
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/health"),
  createCase: (b: CaseInput) => request<CaseOut>("/api/cases", { method: "POST", body: JSON.stringify(b) }),
  listCases: () => request<CaseSummary[]>("/api/cases"),
  getCase: (id: number) => request<CaseOut>(`/api/cases/${id}`),
  setStatus: (id: number, status: CaseStatus) =>
    request<CaseOut>(`/api/cases/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
};
