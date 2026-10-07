import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useCases } from "../cases";
import { useHealth } from "../health";
import type { ShellContext } from "../shellContext";
import type { CaseInput, CaseOut } from "../types";
import { CaseForm } from "./CaseForm";
import { HealthStatus } from "./HealthStatus";
import { HistoryList } from "./HistoryList";
import { Tabs } from "./ui/Tabs";

export function AppShell() {
  const navigate = useNavigate();
  const { state } = useHealth();
  const { state: cases, refresh } = useCases();
  const [prefill, setPrefill] = useState<{ input: CaseInput; nonce: number } | null>(null);
  const [leftTab, setLeftTab] = useState("form");
  const defaultDate = state.phase === "ok" ? state.health.case_date : "";

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 rounded-lg text-sm font-medium ${isActive ? "text-[#2f7bff]" : "text-muted hover:text-white"}`;

  const onCreated = (c: CaseOut) => {
    refresh(); // history refetch; the new case is opened through its own route
    navigate(`/cases/${c.id}`);
  };

  const context: ShellContext = {
    duplicate: (input) => {
      setLeftTab("form"); // make sure the form is visible before it is filled
      setPrefill({ input, nonce: Date.now() });
    },
  };

  const historyLabel = cases.phase === "ok" ? `History (${cases.cases.length})` : "History";

  return (
       <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
      <header className="mb-6 border-b border-white/10 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-semibold">SkillBridge Case Resolution Desk</h1>
          <nav aria-label="Main" className="flex gap-1">
            <NavLink to="/" end className={navClass}>New case</NavLink>
          </nav>
        </div>
        <div className="mt-3"><HealthStatus /></div>
      </header>

      {/* Desktop: tabs (new case, history) on the left, result on the right. Mobile: one column. */}
            {/* One column: tabs for new case and history. A case opens as a modal through the /cases/:id route. */}
      <main>
        <div>
          <Tabs
            idPrefix="left"
            label="Case entry and history"
            value={leftTab}
            onChange={setLeftTab}
            tabs={[
              {
                id: "form",
                label: "New case",
                content: <CaseForm defaultDate={defaultDate} prefill={prefill} onCreated={onCreated} onUncertain={refresh} />,
              },
              { id: "history", label: historyLabel, content: <HistoryList /> },
            ]}
          />
        </div>
      
                  <Outlet context={context} />
      </main>
    </div>
  );
}