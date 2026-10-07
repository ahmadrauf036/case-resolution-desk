import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary";

const styles: Record<Variant, string> = {
  primary:
    "bg-[#2f7bff] text-white shadow-[0_0_20px_rgba(47,123,255,0.45)] hover:shadow-[0_0_28px_rgba(47,123,255,0.65)] disabled:opacity-50 disabled:shadow-none",
  secondary:
    "bg-transparent text-white border border-white/15 hover:bg-white/5 disabled:opacity-50",
};

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type={type}
      className={`rounded-lg px-5 py-2.5 font-medium transition-shadow disabled:cursor-not-allowed ${styles[variant]} ${className}`}
      {...props}
    />
  );
}
