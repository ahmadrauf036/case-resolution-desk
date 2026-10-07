import type { HTMLAttributes } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`bg-card border border-white/10 rounded-xl p-5 ${className}`} {...props} />;
}
