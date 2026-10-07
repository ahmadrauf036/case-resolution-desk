import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { STATUSES, type CaseOut, type CaseStatus } from "../types";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { Select } from "./ui/Input";

interface Props {
  caseId: number;
  current: CaseStatus;
  onUpdated: (updated: CaseOut) => void;
}

export function StatusControl({ caseId, current, onUpdated }: Props) {
  const [selected, setSelected] = useState<CaseStatus>(current);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const inFlight = useRef(false);

  // Follow the saved status when another case is opened or the server returns a new value.
  useEffect(() => { setSelected(current); setError(null); setDone(null); }, [caseId, current]);

  const save = async () => {
    if (inFlight.current || selected === current) return;
    inFlight.current = true;
    setSaving(true);
    setError(null);
    setDone(null);
    try {
      const updated = await api.setStatus(caseId, selected);
      onUpdated(updated);
      setDone(`Status set to ${updated.status}.`);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.status === 404 ? "Case not found." : e.fields[0]?.message ?? e.message);
      } else {
        setError("Cannot reach the server.");
      }
    } finally {
      inFlight.current = false;
      setSaving(false);
    }
  };

  return (
    <Card>
      <h3 className="mb-3 text-base font-medium">Workflow status</h3>
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[12rem] flex-1">
          <label htmlFor="status-select" className="mb-1 block text-sm font-medium">Status</label>
          <Select
            id="status-select"
            value={selected}
            disabled={saving}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "status-err" : "status-hint"}
            onChange={(e) => { setSelected(e.target.value as CaseStatus); setError(null); setDone(null); }}
          >
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </Select>
        </div>
        <Button onClick={save} disabled={saving || selected === current}>
          {saving ? "Saving" : "Update status"}
        </Button>
      </div>
      <p id="status-hint" className="mt-2 text-sm text-muted">
        Changes only the workflow status. The rule result and case note stay as saved.
      </p>
      {error && <p id="status-err" role="alert" className="mt-2 text-sm text-red-300">{error}</p>}
      {done && <p role="status" className="mt-2 text-sm text-emerald-300">{done}</p>}
    </Card>
  );
}