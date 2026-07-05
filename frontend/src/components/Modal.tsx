"use client";

import { ReactNode, useEffect } from "react";

// Arc modal — panel surface, accent border, primary glow. Tone variants
// follow the badge/button semantic colors from the design system.
export type ModalTone = "primary" | "secondary" | "warning";

const TONES: Record<ModalTone, { border: string; iconWrap: string; glow: string }> = {
  primary: { border: "border-accent", iconWrap: "bg-accentSubtle text-accentBright", glow: "shadow-glow" },
  secondary: { border: "border-secondary", iconWrap: "bg-secondary/15 text-secondary", glow: "shadow-glow" },
  warning: { border: "border-warning", iconWrap: "bg-warningDeep text-warning", glow: "shadow-glowWarning" },
};

export function Modal({
  open,
  onClose,
  tone = "primary",
  icon,
  title,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  tone?: ModalTone;
  icon?: ReactNode;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-outer/80 p-6 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        className={`arc-fade-up w-full max-w-lg rounded-xl border bg-panel p-6 ${TONES[tone].border} ${TONES[tone].glow}`}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start gap-4">
          {icon && (
            <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-md ${TONES[tone].iconWrap}`}>
              {icon}
            </span>
          )}
          <div className="flex min-w-0 flex-1 flex-col gap-2">
            <h2 className="text-h5 font-semibold text-text">{title}</h2>
            <div className="text-body-sm text-textSecondary">{children}</div>
          </div>
        </div>
        {footer && <div className="mt-6 flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
}
