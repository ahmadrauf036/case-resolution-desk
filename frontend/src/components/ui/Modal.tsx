import { useEffect, useRef, type ReactNode } from "react";
import { Button } from "./Button";

interface Props {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

/**
 * Modal built on the native <dialog>: the browser traps focus, makes the page behind inert,
 * and closes on Esc. Clicking the dimmed backdrop or the Close button also closes it.
 */
export function Modal({ title, onClose, children }: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (!d.open) {
      if (typeof d.showModal === "function") d.showModal();
      else d.setAttribute("open", ""); // very old browsers, and test environments without <dialog> support
    }
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden"; // keep the page behind from scrolling
    return () => { document.body.style.overflow = previous; };
  }, []);

  return (
    <dialog
      ref={ref}
      aria-labelledby="modal-title"
      onClose={onClose} // fires on Esc
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }} // click on the backdrop
      className="m-auto max-h-[90vh] w-[calc(100%-1.5rem)] max-w-4xl overflow-y-auto rounded-xl border border-white/10 bg-black p-0 text-white backdrop:bg-black/80"
    >
      <div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-white/10 bg-black px-5 py-3">
        <h2 id="modal-title" className="text-lg font-medium">{title}</h2>
        <Button variant="secondary" className="px-3 py-1 text-sm" onClick={onClose}>Close</Button>
      </div>
      <div className="p-5">{children}</div>
    </dialog>
  );
}