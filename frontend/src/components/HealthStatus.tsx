import { useHealth } from "../health";
import { Spinner } from "./ui/Spinner";
import { Button } from "./ui/Button";

export function HealthStatus() {
  const { state, retry } = useHealth();

  if (state.phase === "loading") return <Spinner label="Connecting to backend" />;

  if (state.phase === "error") {
    return (
      <div className="flex flex-wrap items-center gap-3 text-sm" role="alert">
        <span className="text-red-300">Backend offline. {state.message}</span>
        <Button variant="secondary" className="px-3 py-1 text-sm" onClick={retry}>Retry</Button>
      </div>
    );
  }

  const { health } = state;
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
      <span className="text-emerald-300">Backend connected</span>
      <span>Assessment date {health.case_date}</span>
      <span>{health.policies.join(", ")}</span>
      <span>{health.llm_configured ? "AI explanation on" : "AI not configured, rule-based summaries only"}</span>
    </div>
  );
}
