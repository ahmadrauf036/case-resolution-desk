import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError } from "./api";
import type { Health } from "./types";

type HealthState =
  | { phase: "loading" }
  | { phase: "ok"; health: Health }
  | { phase: "error"; message: string };

const Ctx = createContext<{ state: HealthState; retry: () => void }>({ state: { phase: "loading" }, retry: () => {} });

export function HealthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<HealthState>({ phase: "loading" });

  const load = useCallback(() => {
    setState({ phase: "loading" });
    api.health().then(
      (health) => setState({ phase: "ok", health }),
      (e: unknown) => setState({ phase: "error", message: e instanceof ApiError ? e.message : "Cannot reach the server." }),
    );
  }, []);

  useEffect(load, [load]);

  return <Ctx.Provider value={{ state, retry: load }}>{children}</Ctx.Provider>;
}

export const useHealth = () => useContext(Ctx);
