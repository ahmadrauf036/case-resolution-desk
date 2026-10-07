import { useEffect, useState, type ReactNode } from "react";
import type { CaseOut } from "../types";
import { CHECK_DISPLAY, ELIGIBILITY_HEADLINE, EXTENSION_LABEL, formatPkt } from "../format";
import { Badge, NeutralBadge } from "./ui/Badge";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { Tabs } from "./ui/Tabs";
import { BoldText } from "./BoldText";
import { SourceChips } from "./SourceChips";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <h3 className="mb-3 text-base font-medium">{title}</h3>
      {children}
    </Card>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1 pl-5 text-sm">
      {items.map((t, i) => <li key={i}>{t}</li>)}
    </ul>
  );
}

function CopyButton({ text }: { text: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("failed");
    }
    setTimeout(() => setState("idle"), 2000);
  };
  return (
    <Button variant="secondary" className="px-3 py-1 text-sm" onClick={copy}>
      {state === "copied" ? "Copied" : state === "failed" ? "Copy failed" : "Copy note"}
    </Button>
  );
}

export function ResultView({ data, children }: { data: CaseOut; children?: ReactNode }) {
  const r = data.rule_result;
  const d = r.deadline;
  const [tab, setTab] = useState("overview");

  // A different case always opens on the Overview tab. A status change on the same case keeps the current tab.
  useEffect(() => { setTab("overview"); }, [data.id]);

  const overview = (
    <div className="space-y-4">
      <Card>
        <h3 className="mb-1 text-base font-medium">Next action</h3>
        <p className="text-base">{r.next_action}</p>
        {r.next_actions.length > 0 && (
          <details className="mt-3">
            <summary className="cursor-pointer text-sm text-muted">All next actions ({r.next_actions.length})</summary>
            <div className="mt-2"><BulletList items={r.next_actions} /></div>
          </details>
        )}
      </Card>

      {(r.needs_approval.length > 0 || r.missing_facts.length > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {r.needs_approval.length > 0 && (
            <Section title="Awaiting approval"><BulletList items={r.needs_approval} /></Section>
          )}
          {r.missing_facts.length > 0 && (
            <Section title="Still needed"><BulletList items={r.missing_facts} /></Section>
          )}
        </div>
      )}

      {r.warnings.length > 0 && (
        <div role="note" className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
          <h3 className="mb-2 text-base font-medium text-amber-300">Warnings</h3>
          <BulletList items={r.warnings} />
        </div>
      )}

      <Section title="Deadline">
        <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
          <div><dt className="text-muted">Standard due</dt><dd>{formatPkt(d.standard_due)}</dd></div>
          <div><dt className="text-muted">Effective due</dt><dd>{formatPkt(d.effective_due)}</dd></div>
          <div><dt className="text-muted">Extension</dt><dd>{EXTENSION_LABEL[d.extension_state]}</dd></div>
        </dl>
        {d.note && <p className="mt-3 whitespace-pre-wrap text-sm">{d.note}</p>}
      </Section>
    </div>
  );

  const checks = (
    <Section title="Checks">
      {r.checks.length === 0 ? (
        <p className="text-sm text-muted">No checks were run.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-136 text-left text-sm">
            <thead className="text-muted">
              <tr>
                <th className="pb-2 pr-3 font-medium">Check</th>
                <th className="pb-2 pr-3 font-medium">Result</th>
                <th className="pb-2 pr-3 font-medium">Detail</th>
                <th className="pb-2 font-medium">Source</th>
              </tr>
            </thead>
            <tbody>
              {r.checks.map((c) => {
                const disp = CHECK_DISPLAY[c.result];
                return (
                  <tr key={c.rule} className="border-t border-white/10 align-top">
                    <td className="py-2 pr-3">{c.label}</td>
                    <td className={`py-2 pr-3 whitespace-nowrap ${disp.cls}`}>
                      <span aria-hidden="true">{disp.icon} </span>{disp.text}
                    </td>
                    <td className="py-2 pr-3">{c.detail}</td>
                    <td className="py-2 whitespace-nowrap">{c.source}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );

  const explanation = (
    <Section title="Explanation">
      {data.llm_error && (
        <div role="alert" className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm">
          <p className="font-medium text-amber-300">AI explanation unavailable, showing rule-based summary</p>
          <p className="mt-1 whitespace-pre-wrap wrap-break-word text-white/80">{data.llm_error}</p>
        </div>
      )}
      {data.llm_answer ? <BoldText text={data.llm_answer} /> : <p className="text-sm text-muted">No explanation was returned.</p>}
    </Section>
  );

  const sources = <Section title="Sources"><SourceChips sources={data.sources} /></Section>;

  const caseFile = (
    <div className="space-y-4">
      <Section title="Case note">
        <pre className="overflow-x-auto whitespace-pre-wrap wrap-break-word rounded-lg border border-white/10 bg-black p-3 font-mono text-xs">
          {data.case_note}
        </pre>
        <div className="mt-2"><CopyButton text={data.case_note} /></div>
      </Section>
      {children}
    </div>
  );

  return (
    <div className="space-y-4">
      {/* Always visible above the tabs: the rule result is authoritative and comes before any AI text */}
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <Badge value={r.eligibility} />
          <NeutralBadge>{data.status}</NeutralBadge>
          <span className="text-sm text-muted">Case #{data.id} for {data.input.learner_name}</span>
        </div>
        <p className="mt-3 text-lg font-medium">{ELIGIBILITY_HEADLINE[r.eligibility]}</p>
        <p className="mt-1 text-sm text-muted">
          Decided by the rule engine. A recommendation only: nothing here is an approval.
        </p>
      </Card>

      <Tabs
        idPrefix="result"
        label="Case result sections"
        value={tab}
        onChange={setTab}
        tabs={[
          { id: "overview", label: "Overview", content: overview },
          { id: "checks", label: `Checks (${r.checks.length})`, content: checks },
          { id: "explanation", label: data.llm_error ? "Explanation (fallback)" : "Explanation", content: explanation },
          { id: "sources", label: `Sources (${data.sources.length})`, content: sources },
          { id: "case", label: "Case file", content: caseFile },
        ]}
      />
    </div>
  );
}