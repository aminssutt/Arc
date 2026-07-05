import { HTMLAttributes, ReactNode } from "react";

// Arc base card — restyled to the industrial look, same props API.
// Themed tokens (bg-raised / border / text) keep it light/dark aware; the
// eyebrow becomes a mono spec-label in ember (detection accent).
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
        "flex flex-col items-start gap-3 rounded-card border border-border bg-raised p-5",
        "transition-[transform,box-shadow,border-color] duration-300 ease-mech",
        className ?? "",
      ].join(" ")}
      {...rest}
    >
      {eyebrow && (
        <p className="font-mono text-[11px] uppercase tracking-label text-ember">{eyebrow}</p>
      )}
      <p className="font-display text-h6 font-semibold tracking-tight text-text">{title}</p>
      {children && <div className="text-body-sm text-muted">{children}</div>}
      {footnote && <p className="font-mono text-caption text-muted">{footnote}</p>}
    </div>
  );
}
