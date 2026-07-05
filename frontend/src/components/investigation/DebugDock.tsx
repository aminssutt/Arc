"use client";

import { Bug, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/Button";
import type { DemoScenario, ValidationVerdict } from "@/lib/contracts";

// Minimized debug tooling: a single dock button that expands into a small
// panel. Production surfaces stay clean; the demo hooks stay reachable.
export function DebugDock({
  running,
  streaming,
  streamNote,
  canValidate,
  onRun,
  onReset,
  onToggleStream,
  onValidate,
}: {
  running: boolean;
  streaming: boolean;
  streamNote: string | null;
  /** True once an incident push payload has been captured from the stream. */
  canValidate: boolean;
  onRun: (scenario: DemoScenario) => void;
  onReset: () => void;
  onToggleStream: () => void;
  /** Demo-only: POST the field verdict from the web (same call as the iOS app). */
  onValidate: (verdict: ValidationVerdict) => void;
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

          {/* Demo field-validation — the verdict normally comes from the phone.
              These POST the same call the iOS app makes so the web demo can
              complete end-to-end. Not a replacement for the real iOS path. */}
          <div className="flex flex-col gap-2 border-t border-border pt-3">
            <p className="text-label-sm font-medium uppercase tracking-wide text-muted">
              Field validate (demo)
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                className="flex-1"
                disabled={!canValidate}
                onClick={() => onValidate("real")}
              >
                Confirm (real)
              </Button>
              <Button
                size="sm"
                variant="warningSubtle"
                className="flex-1"
                disabled={!canValidate}
                onClick={() => onValidate("false")}
              >
                Refuse (pivot)
              </Button>
            </div>
            {!canValidate && (
              <p className="text-caption text-muted">Waiting for a push_sent incident…</p>
            )}
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
