"use client";

import { Bug, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/Button";
import type { DemoScenario } from "@/lib/contracts";

// Minimized debug tooling: a single dock button that expands into a small
// panel. Production surfaces stay clean; the demo hooks stay reachable.
export function DebugDock({
  running,
  streaming,
  streamNote,
  onRun,
  onReset,
  onToggleStream,
}: {
  running: boolean;
  streaming: boolean;
  streamNote: string | null;
  onRun: (scenario: DemoScenario) => void;
  onReset: () => void;
  onToggleStream: () => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end gap-2">
      {open && (
        <div className="arc-fade-up flex w-64 flex-col gap-3 rounded-lg border border-border bg-header/95 p-4 shadow-glow backdrop-blur">
          <div className="flex items-center justify-between">
            <p className="text-label-sm font-medium uppercase tracking-wide text-muted">Debug</p>
            <Link href="/console" className="text-caption text-muted hover:text-textSecondary">
              raw console
            </Link>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" className="flex-1" disabled={running} onClick={() => onRun("confirm")}>
              Confirm
            </Button>
            <Button size="sm" variant="ghost" className="flex-1" disabled={running} onClick={() => onRun("pivot")}>
              Pivot
            </Button>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" className="flex-1" onClick={onReset}>
              Reset
            </Button>
            <Button
              size="sm"
              variant={streaming ? "secondary" : "ghost"}
              className="flex-1"
              onClick={onToggleStream}
            >
              {streaming ? "Stream on" : "Stream"}
            </Button>
          </div>
          {streamNote && <p className="text-caption text-warning">{streamNote}</p>}
        </div>
      )}
      <button
        onClick={() => setOpen((value) => !value)}
        aria-label="Toggle debug tools"
        className={[
          "flex h-10 w-10 items-center justify-center rounded-full border transition-colors",
          open
            ? "border-accent bg-accentSubtle text-accentBright"
            : "border-border bg-header/90 text-muted hover:border-borderStrong hover:text-textSecondary",
        ].join(" ")}
      >
        {open ? <X className="h-4 w-4" /> : <Bug className="h-4 w-4" />}
      </button>
    </div>
  );
}
