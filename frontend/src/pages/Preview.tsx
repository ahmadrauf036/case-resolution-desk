import { useState } from "react";
import { FIXTURES } from "../fixtures";
import { ResultView } from "../components/ResultView";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";

/** Dev-only: renders each mocked case so the result screen can be checked without the backend. */
export default function Preview() {
  const names = Object.keys(FIXTURES);
  const [name, setName] = useState(names[0]);
  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-1 text-lg font-medium">Result preview</h2>
        <p className="mb-3 text-sm text-muted">Mock data, not from the backend.</p>
        <div className="flex flex-wrap gap-2">
          {names.map((n) => (
            <Button key={n} variant="secondary" className={`px-3 py-1.5 text-sm ${n === name ? "bg-white/10" : ""}`} onClick={() => setName(n)}>
              {n}
            </Button>
          ))}
        </div>
      </Card>
      <ResultView data={FIXTURES[name]} />
    </div>
  );
}