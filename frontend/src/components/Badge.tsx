import { HTMLAttributes } from "react";

// Arc status/state pill — restyled to the industrial look, same props API.
// Tones map to tricolore via the themed tokens: primary = arc (accent),
// secondary = resolve, warning = warn, neutral = ink/paper.
export type BadgeTone = "primary" | "secondary" | "warning" | "neutral";
export type BadgeEmphasis = "solid" | "subtle";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  emphasis?: BadgeEmphasis;
}

const STYLES: Record<BadgeTone, Record<BadgeEmphasis, string>> = {
  primary: {
    solid: "bg-accent text-background",
    subtle: "border border-accent bg-accentSubtle text-accent",
  },
  secondary: {
    solid: "bg-secondary text-background",
    subtle: "border border-secondary bg-secondary/15 text-secondary",
  },
  warning: {
    solid: "bg-warning text-background",
    subtle: "border border-warning bg-warning/15 text-warning",
  },
  neutral: {
    solid: "bg-text text-background",
    subtle: "border border-border bg-raised text-muted",
  },
};

export function Badge({ tone = "primary", emphasis = "solid", className, children, ...rest }: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center justify-center whitespace-nowrap rounded-full px-3 py-1",
        "font-mono text-label-sm font-medium uppercase tracking-[0.12em]",
        STYLES[tone][emphasis],
        className ?? "",
      ].join(" ")}
      {...rest}
    >
      {children}
    </span>
  );
}
