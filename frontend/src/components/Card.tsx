import { HTMLAttributes, ReactNode } from "react";

// Arc base card — Figma "Section Card", node 38:9 / component 11:77.
export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  eyebrow?: string;
  title: string;
  footnote?: string;
  children?: ReactNode;
}

export function Card({ eyebrow, title, footnote, children, className, ...rest }: CardProps) {
  return (
    <div
      className={[
        "flex flex-col items-start gap-3 rounded-lg border border-border bg-raised p-5",
        className ?? "",
      ].join(" ")}
      {...rest}
    >
      {eyebrow && (
        <p className="text-label-sm font-medium uppercase tracking-wide text-accent">{eyebrow}</p>
      )}
      <p className="text-h6 font-semibold text-text">{title}</p>
      {children && <div className="text-body-sm text-muted">{children}</div>}
      {footnote && <p className="text-caption text-muted">{footnote}</p>}
    </div>
  );
}
