import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api, ApiError } from "./api";
import type { CaseSummary } from "./types";

type CasesState =
  | { phase: "loading" }
  | { phase: "ok"; cases: CaseSummary[] }
  | { phase: "error"; message: string };

const Ctx = createContext<{ state: CasesState; refresh: () => void }>({ state: { phase: "loading" }, refresh: () => {} });

export function CasesProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<CasesState>({ phase: "loading" });
  const latestRequest = useRef(0);

  const refresh = useCallback(() => {
    const id = ++latestRequest.current;
    api.listCases().then(
      (cases) => { if (id === latestRequest.current) setState({ phase: "ok", cases }); },
      (e: unknown) => {
        if (id !== latestRequest.current) return;
        const message = e instanceof ApiError ? e.message : "Cannot reach the server.";
        // Keep showing the last good list if a refetch fails; only show the error on first load.
        setState((prev) => (prev.phase === "ok" ? prev : { phase: "error", message }));
      },
    );
  }, []);

  useEffect(refresh, [refresh]);

  const retry = useCallback(() => { setState({ phase: "loading" }); refresh(); }, [refresh]);

  return <Ctx.Provider value={{ state, refresh: state.phase === "error" ? retry : refresh }}>{children}</Ctx.Provider>;
}

export const useCases = () => useContext(Ctx);