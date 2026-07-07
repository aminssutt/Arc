import Image from "next/image";
import Link from "next/link";
import { ReactNode } from "react";
import { AlertTriangleIcon } from "@/components/icons";
import { ProfileMenu } from "@/components/ProfileMenu";
import type { CaseStatus } from "@/lib/investigation";

// App top bar — Figma node 84:868, extended with the profile menu for the
// product shell. `crumb` names the current surface; `children` slots extra
// right-side content ahead of the profile chip.
export function AppTopBar({ crumb, children }: { crumb: string; children?: ReactNode }) {
  return (
    <header className="flex w-full shrink-0 items-center justify-between gap-2 border-b border-border bg-header px-4 py-3 sm:gap-4 sm:px-6 sm:py-4">
      <div className="flex min-w-0 items-center gap-2 p-1.5 sm:gap-4 sm:p-2.5">
        <Link href="/" className="shrink-0">
          <Image src="/assets/arc-logo.svg" alt="Arc" width={142} height={24} priority className="h-5 w-auto sm:h-6" />
        </Link>
        <div className="min-w-0 border-l border-borderStrong pl-3 sm:pl-4">
          <p className="max-w-[26vw] truncate text-body-sm text-textSecondary sm:max-w-none sm:text-body">{crumb}</p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2 sm:gap-4">
        {children}
        <ProfileMenu />
      </div>
    </header>
  );
}

// Telecom case statuses, tricolore: monitoring = arc, investigating = ember,
// awaiting field validation = warn (logistics), resolved = resolve.
const STATUS_CHIP: Record<CaseStatus, { label: string; className: string; dot: string; pulse: boolean }> = {
  monitoring: {
    label: "monitoring",
    className: "border-arc/60 bg-arc/[0.08] text-arc",
    dot: "bg-arc",
    pulse: false,
  },
  investigating: {
    label: "investigating",
    className: "border-ember/70 bg-ember/10 text-ember",
    dot: "bg-ember",
    pulse: true,
  },
  "awaiting-validation": {
    label: "awaiting field validation",
    className: "border-warn/70 bg-warn/10 text-warn",
    dot: "bg-warn",
    pulse: true,
  },
  resolved: {
    label: "resolved",
    className: "border-resolve/70 bg-resolve/10 text-resolve",
    dot: "bg-resolve",
    pulse: false,
  },
};

export function CaseStatusChip({ caseStatus }: { caseStatus: CaseStatus }) {
  const chip = STATUS_CHIP[caseStatus];
  return (
    <span
      className={`inline-flex h-8 items-center gap-1.5 rounded-md border px-2 font-mono text-[11px] font-semibold uppercase leading-none tracking-wide sm:gap-2 sm:px-3 sm:text-[13px] ${chip.className}`}
    >
      {chip.pulse ? (
        <span className={`h-2 w-2 rounded-full ${chip.dot} animate-signal-pulse`} />
      ) : (
        <AlertTriangleIcon className="h-4 w-4" />
      )}
      {chip.label}
    </span>
  );
}
