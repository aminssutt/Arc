"use client";

import { ButtonHTMLAttributes } from "react";
import { ArrowRightIcon } from "@/components/icons";

// Small ghost pill used in panel headers ("live building feed" etc.) —
// the Ghost/Small button instance from the Figma concept frame.
export function PanelButton({
  children,
  className,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={[
        "inline-flex h-8 items-center gap-2 rounded-md border border-accent bg-accentSubtle px-3",
        "text-[14px] font-semibold leading-[14px] text-accentBright transition-colors hover:bg-accentSubtle/70",
        className ?? "",
      ].join(" ")}
      {...rest}
    >
      {children}
      <ArrowRightIcon className="h-4 w-4" />
    </button>
  );
}
