import { useEffect, useState } from "react";
import { useNavigate, useOutletContext, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { ResultView } from "../components/ResultView";
import { StatusControl } from "../components/StatusControl";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
import { Spinner } from "../components/ui/Spinner";
import { useCases } from "../cases";
import type { ShellContext } from "../shellContext";
import type { CaseOut } from "../types";

type State =
  | { phase: "loading" }
  | { phase: "ok"; data: CaseOut }
  | { phase: "error"; message: string };

/** /cases/:id, shown as a modal over the form and history. Closing returns to "/". */
export default function CaseDetail() {
  const { id: idParam } = useParams();
  const navigate = useNavigate();
  const { duplicate } = useOutletContext<ShellContext>();
  const { refresh } = useCases();
  const id = Number(idParam);
  const [state, setState] = useState<State>({ phase: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!Number.isInteger(id) || id < 1) {
      setState({ phase: "error", message: "Case not found." });
      return;
    }
    let cancelled = false; // ignore a slow response if the case changed meanwhile
    setState({ phase: "loading" });
    api.getCase(id).then(
      (data) => { if (!cancelled) setState({ phase: "ok", data }); },
      (e: unknown) => {
        if (cancelled) return;
        const message = e instanceof ApiError ? (e.status === 404 ? "Case not found." : e.message) : "Cannot reach the server.";
        setState({ phase: "error", message });
      },
    );
    return () => { cancelled = true; };
  }, [id, attempt]);

  const close = () => navigate("/");

  const handleUpdated = (updated: CaseOut) => {
    setState({ phase: "ok", data: updated }); // the modal follows the server's response
    refresh(); // history shows the new status
  };

  const title = state.phase === "ok" ? `Case #${state.data.id}` : Number.isInteger(id) ? `Case #${id}` : "Case";

  return (
    <Modal title={title} onClose={close}>
      {state.phase === "loading" && <Spinner label="Loading case" />}

      {state.phase === "error" && (
        <div>
          <p role="alert" className="text-red-300">{state.message}</p>
          {state.message !== "Case not found." && (
            <Button variant="secondary" className="mt-3 px-3 py-1 text-sm" onClick={() => setAttempt((n) => n + 1)}>Retry</Button>
          )}
        </div>
      )}

      {state.phase === "ok" && (
        <ResultView data={state.data}>
          <StatusControl caseId={state.data.id} current={state.data.status} onUpdated={handleUpdated} />
          <div>
            <Button
              variant="secondary"
              onClick={() => { duplicate(state.data.input); close(); }}
            >
              Duplicate and edit
            </Button>
            <p className="mt-1 text-sm text-muted">Fills the form with these facts. Analyzing again creates a new case.</p>
          </div>
        </ResultView>
      )}
    </Modal>
  );
}