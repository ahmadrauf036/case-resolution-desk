import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError } from "../api";
import { EXAMPLES } from "../examples";
import { fromInput, emptyForm, mapServerErrors, toPayload, validate, type FormErrors, type FormState, type Tri } from "../formState";
import type { CaseInput, CaseOut } from "../types";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { Input, Select, Textarea } from "./ui/Input";
import { Spinner } from "./ui/Spinner";
import { Field, fieldAria } from "./Field";
const focusFirstInvalid = () =>
  requestAnimationFrame(() => document.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus());
interface Props {
  defaultDate: string;
  /** Set to fill the form from a saved case ("Duplicate and edit"). A new nonce re-applies the same input. */
  prefill?: { input: CaseInput; nonce: number } | null;
  onCreated: (c: CaseOut) => void;
    onUncertain?: () => void;
}

const triOptions = (none: string) => (
  <>
    <option value="none">{none}</option>
    <option value="approved">Approved</option>
    <option value="denied">Denied</option>
  </>
);

export function CaseForm({ defaultDate, prefill, onCreated, onUncertain }: Props) {
  const [form, setForm] = useState<FormState>(() => emptyForm(defaultDate));
  const [errors, setErrors] = useState<FormErrors>({});
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const inFlight = useRef(false); // guards against double submits: every POST creates a new case

  // /health may answer after first render; fill the date only if the user hasn't set one.
  useEffect(() => {
    if (defaultDate) setForm((f) => (f.case_date ? f : { ...f, case_date: defaultDate }));
  }, [defaultDate]);
  useEffect(() => {
    if (!prefill) return;
    setForm(fromInput(prefill.input, defaultDate));
    setErrors({});
    setBanner(null);
    document.getElementById("learner_name")?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefill]);
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((e) => (e[key] ? { ...e, [key]: undefined } : e));
  };

  const loadExample = (name: string) => {
    setForm(fromInput(EXAMPLES[name], defaultDate));
    setErrors({});
    setBanner(null);
  };

  const onSubmit = async (ev: FormEvent) => {
    ev.preventDefault();
    if (inFlight.current) return;

    const clientErrors = validate(form);
    setErrors(clientErrors);
    setBanner(null);
        if (Object.keys(clientErrors).length > 0) { focusFirstInvalid(); return; }

    const payload = toPayload(form);
    inFlight.current = true;
    setSubmitting(true);
    try {
      const created = await api.createCase(payload);
      onCreated(created);
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        const mapped = mapServerErrors(e.fields, e.message);
        setErrors(mapped.fields);
                setBanner(mapped.banner);
        focusFirstInvalid();
      } else {
        const noResponse = e instanceof ApiError && e.status === 0;
        const message = e instanceof ApiError ? e.message : "Cannot reach the server.";
        setBanner(noResponse ? `${message} The case may have been saved: check History before analyzing again.` : message);
        if (noResponse) onUncertain?.(); // refresh history so a saved case shows up before any resubmit
      }
    } finally {
      inFlight.current = false;
      setSubmitting(false);
    }
  };

  const requested = form.extension === "requested";

  return (
    <Card>
      <h2 className="mb-3 text-lg font-medium">New case</h2>

      <div className="mb-4">
        <p className="mb-2 text-sm text-muted">Load an example</p>
        <div className="flex flex-wrap gap-2">
          {Object.keys(EXAMPLES).map((name) => (
            <Button key={name} variant="secondary" className="px-3 py-1.5 text-sm" disabled={submitting} onClick={() => loadExample(name)}>
              {name}
            </Button>
          ))}
        </div>
      </div>

      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {banner && (
          <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {banner}
          </div>
        )}

        <Field id="learner_name" label="Learner name" error={errors.learner_name}>
          <Input {...fieldAria("learner_name", errors.learner_name)} maxLength={200} value={form.learner_name}
            onChange={(e) => set("learner_name", e.target.value)} />
        </Field>

        <Field id="question" label="Question" error={errors.question}>
          <Textarea {...fieldAria("question", errors.question)} rows={3} value={form.question}
            onChange={(e) => set("question", e.target.value)} />
        </Field>

        <div className="grid gap-4 sm:grid-cols-3">
          <Field id="attendance_pct" label="Attendance %" error={errors.attendance_pct} hint="0 to 100. Leave empty if unknown.">
            <Input {...fieldAria("attendance_pct", errors.attendance_pct, "h")} type="number" inputMode="decimal" step={0.1}
              value={form.attendance_pct} onChange={(e) => set("attendance_pct", e.target.value)} />
          </Field>
          <Field id="sessions" label="Live sessions" error={errors.sessions} hint="Whole number. Leave empty if unknown.">
            <Input {...fieldAria("sessions", errors.sessions, "h")} type="number" inputMode="numeric" step={1}
              value={form.sessions} onChange={(e) => set("sessions", e.target.value)} />
          </Field>
          <Field id="capstone_score" label="Capstone score" error={errors.capstone_score} hint="0 to 100. Leave empty if unknown.">
            <Input {...fieldAria("capstone_score", errors.capstone_score, "h")} type="number" inputMode="decimal" step={0.1}
              value={form.capstone_score} onChange={(e) => set("capstone_score", e.target.value)} />
          </Field>
        </div>

        <Field id="submission" label="Submission" error={errors.submission}>
          <Select {...fieldAria("submission", errors.submission)} value={form.submission}
            onChange={(e) => set("submission", e.target.value as FormState["submission"])}>
            <option value="unknown">Not checked</option>
            <option value="safe">Safe</option>
            <option value="secret">Secret found</option>
          </Select>
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="extension" label="Extension request" error={errors.extension}>
            <Select {...fieldAria("extension", errors.extension)} value={form.extension}
              onChange={(e) => {
                const v = e.target.value as FormState["extension"];
                set("extension", v);
                if (v === "none") set("extension_decision", "none");
              }}>
              <option value="none">Not requested</option>
              <option value="requested">Requested</option>
            </Select>
          </Field>
          <Field id="extension_decision" label="Mentor decision on extension" error={errors.extension_decision}
            hint={requested ? undefined : "Available once an extension is requested."}>
            <Select {...fieldAria("extension_decision", errors.extension_decision, requested ? undefined : "h")}
              disabled={!requested} value={form.extension_decision}
              onChange={(e) => set("extension_decision", e.target.value as Tri)}>
              {triOptions("No decision")}
            </Select>
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="makeup" label="Makeup session, mentor decision" error={errors.makeup}>
            <Select {...fieldAria("makeup", errors.makeup)} value={form.makeup}
              onChange={(e) => set("makeup", e.target.value as Tri)}>
              {triOptions("No decision")}
            </Select>
          </Field>
          <Field id="missed_session_date" label="Missed session date" error={errors.missed_session_date} hint="Optional.">
            <Input {...fieldAria("missed_session_date", errors.missed_session_date, "h")} type="date"
              value={form.missed_session_date} onChange={(e) => set("missed_session_date", e.target.value)} />
          </Field>
        </div>

        <Field id="note" label="Medical note" error={errors.note}>
          <Select {...fieldAria("note", errors.note)} value={form.note}
            onChange={(e) => set("note", e.target.value as FormState["note"])}>
            <option value="none">Not offered</option>
            <option value="offered">Offered, not verified</option>
            <option value="verified">Offered and verified</option>
          </Select>
        </Field>

        <Field id="case_date" label="Case date" error={errors.case_date} hint="Defaults to the assessment date from the backend.">
          <Input {...fieldAria("case_date", errors.case_date, "h")} type="date" value={form.case_date}
            onChange={(e) => set("case_date", e.target.value)} />
        </Field>

        <div className="flex items-center gap-3 pt-1">
          <Button type="submit" disabled={submitting}>{submitting ? "Analyzing" : "Analyze case"}</Button>
          {submitting && <Spinner label="Analyzing, this can take up to 20 seconds" />}
        </div>
      </form>
    </Card>
  );
}