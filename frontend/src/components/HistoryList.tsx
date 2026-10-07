import { NavLink } from "react-router-dom";
import { useCases } from "../cases";
import { formatPkt } from "../format";
import { Badge, NeutralBadge } from "./ui/Badge";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { Spinner } from "./ui/Spinner";

export function HistoryList() {
  const { state, refresh } = useCases();

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-lg font-medium">History</h2>
        {state.phase === "ok" && (
          <Button variant="secondary" className="px-3 py-1 text-sm" onClick={refresh}>Refresh</Button>
        )}
      </div>

      {state.phase === "loading" && <Spinner label="Loading cases" />}

      {state.phase === "error" && (
        <div role="alert" className="space-y-2 text-sm">
          <p className="text-red-300">Could not load history. {state.message}</p>
          <Button variant="secondary" className="px-3 py-1 text-sm" onClick={refresh}>Retry</Button>
        </div>
      )}

      {state.phase === "ok" && state.cases.length === 0 && (
        <p className="text-sm text-muted">No cases yet. Analyze a case and it will appear here.</p>
      )}

      {state.phase === "ok" && state.cases.length > 0 && (
        <ul className="-mx-2 divide-y divide-white/10">
          {state.cases.map((c) => (
            <li key={c.id}>
              <NavLink
                to={`/cases/${c.id}`}
                className={({ isActive }) =>
                  `block rounded-lg px-2 py-2.5 hover:bg-white/5 ${isActive ? "bg-white/10" : ""}`
                }
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-medium">{c.learner_name}</span>
                  <Badge value={c.eligibility} />
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
                  <NeutralBadge>{c.status}</NeutralBadge>
                  <span>#{c.id}</span>
                  <span>{formatPkt(c.created_at)}</span>
                </div>
              </NavLink>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}