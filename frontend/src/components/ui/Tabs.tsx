import { useRef, type KeyboardEvent, type ReactNode } from "react";

export interface TabDef {
  id: string;
  label: ReactNode;
  content: ReactNode;
}

interface Props {
  idPrefix: string;
  label: string;
  tabs: TabDef[];
  value: string;
  onChange: (id: string) => void;
}

/**
 * Accessible tabs: arrow keys, Home and End move between tabs.
 * Every panel stays mounted (just hidden), so form input is not lost when switching tabs.
 */
export function Tabs({ idPrefix, label, tabs, value, onChange }: Props) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  const move = (to: number) => {
    const next = tabs[(to + tabs.length) % tabs.length];
    onChange(next.id);
    refs.current[next.id]?.focus();
  };

  const onKeyDown = (e: KeyboardEvent, i: number) => {
    if (e.key === "ArrowRight") { e.preventDefault(); move(i + 1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); move(i - 1); }
    else if (e.key === "Home") { e.preventDefault(); move(0); }
    else if (e.key === "End") { e.preventDefault(); move(tabs.length - 1); }
  };

  return (
    <div>
      <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto border-b border-white/10">
        {tabs.map((t, i) => {
          const active = t.id === value;
          return (
            <button
              key={t.id}
              ref={(el) => { refs.current[t.id] = el; }}
              type="button"
              role="tab"
              id={`${idPrefix}-tab-${t.id}`}
              aria-selected={active}
              aria-controls={`${idPrefix}-panel-${t.id}`}
              tabIndex={active ? 0 : -1}
              onClick={() => onChange(t.id)}
              onKeyDown={(e) => onKeyDown(e, i)}
              className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${
                active ? "border-white text-white" : "border-transparent text-muted hover:text-white"
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>
      {tabs.map((t) => (
        <div
          key={t.id}
          role="tabpanel"
          id={`${idPrefix}-panel-${t.id}`}
          aria-labelledby={`${idPrefix}-tab-${t.id}`}
          hidden={t.id !== value}
          className="pt-4"
        >
          {t.content}
        </div>
      ))}
    </div>
  );
}