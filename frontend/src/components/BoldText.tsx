import { Fragment } from "react";

/**
 * Renders model text safely: plain text, whitespace preserved, and **bold** turned into <strong>.
 * Everything else, including any HTML, is shown as literal text. No dangerouslySetInnerHTML.
 */
export function BoldText({ text }: { text: string }) {
  const parts = text.split(/\*\*(.+?)\*\*/g); // odd indexes are the bold segments
  return (
    <p className="whitespace-pre-wrap break-words leading-relaxed">
      {parts.map((part, i) => (i % 2 === 1 ? <strong key={i}>{part}</strong> : <Fragment key={i}>{part}</Fragment>))}
    </p>
  );
}