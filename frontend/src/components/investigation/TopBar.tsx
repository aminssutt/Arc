import Image from "next/image";
import Link from "next/link";
import { ReactNode } from "react";
import { AlertTriangleIcon } from "@/components/icons";
import { ProfileMenu } from "@/components/ProfileMenu";
import { ThemeToggle } from "@/components/ThemeToggle";
import type { CaseStatus } from "@/lib/investigation";

// App top bar — Figma node 84:868, extended with the profile menu for the
// product shell. `crumb` names the current surface; `children` slots extra
// right-side content ahead of the profile chip.
export function AppTopBar({ crumb, children }: { crumb: string; children?: ReactNode }) {
  return (
    <header className="flex w-full shrink-0 items-center justify-between border-b border-border bg-header px-6 py-4">
      <div className="flex items-center gap-4 p-2.5">
        <Link href="/">
          <Image src="/assets/arc-logo.svg" alt="Arc" width={142} height={24} priority />
        </Link>
        <div className="border-l border-borderStrong pl-4">
          <p className="text-body text-textSecondary">{crumb}</p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        {children}
        <ThemeToggle />
        <ProfileMenu />
      </div>
    </header>
  );
}

const STATUS_CHIP: Record<CaseStatus, { label: string; className: string; pulse: boolean }> = {
  monitoring: {
    label: "monitoring",
    className: "border-accent bg-accentSubtle text-accentBright",
    pulse: false,
  },
  investigating: {
    label: "investigating",
    className: "border-warning bg-warningDeep text-warning",
    pulse: true,
  },
  "awaiting-validation": {
    label: "awaiting validation",
    className: "border-warningBright bg-warningDeep text-warningBright",
    pulse: true,
  },
  resolved: {
    label: "resolved",
    className: "border-secondary bg-secondary/15 text-secondary",
    pulse: false,
  },
};

export function CaseStatusChip({ caseStatus }: { caseStatus: CaseStatus }) {
  const chip = STATUS_CHIP[caseStatus];
  return (
    <span
      className={`inline-flex h-8 items-center gap-2 rounded-md border px-3 text-[14px] font-semibold leading-[14px] ${chip.className}`}
    >
      <AlertTriangleIcon className={`h-4 w-4 ${chip.pulse ? "animate-pulse" : ""}`} />
      {chip.label}
    </span>
  );
}
