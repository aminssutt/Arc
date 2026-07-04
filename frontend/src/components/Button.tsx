import { ButtonHTMLAttributes, ReactNode } from "react";

// Arc base button — Figma "Section Button", node 38:6 / component set 11:58.
// Variants: Style x Size. State (hover/disabled) is handled natively via
// Tailwind pseudo-classes and the `disabled` attribute instead of a prop.
export type ButtonVariant = "primary" | "secondary" | "ghost" | "warning" | "warningSubtle";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
}

const VARIANT_STYLES: Record<ButtonVariant, string> = {
  primary: "bg-accent text-background hover:bg-accent/90",
  secondary: "bg-secondary text-background hover:bg-secondary/90",
  ghost: "border border-accent bg-transparent text-accent hover:bg-accentSubtle",
  warning: "bg-warning text-background hover:bg-warning/90",
  warningSubtle: "border border-warning bg-warning/15 text-warning hover:bg-warning/25",
};

const SIZE_STYLES: Record<ButtonSize, string> = {
  sm: "h-8 gap-2 px-3 text-[14px] leading-[14px]",
  md: "h-[42px] gap-2 px-4 text-[16px] leading-[16px]",
  lg: "h-[52px] gap-2.5 px-6 text-[18px] leading-[18px]",
};

export function Button({
  variant = "primary",
  size = "sm",
  leadingIcon,
  trailingIcon,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      disabled={disabled}
      className={[
        "inline-flex items-center justify-center whitespace-nowrap rounded-md font-semibold transition-colors",
        "disabled:cursor-not-allowed disabled:border-border disabled:bg-raised disabled:text-muted disabled:opacity-60",
        VARIANT_STYLES[variant],
        SIZE_STYLES[size],
        className ?? "",
      ].join(" ")}
      {...rest}
    >
      {leadingIcon}
      {children}
      {trailingIcon}
    </button>
  );
}
