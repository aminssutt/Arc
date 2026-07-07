"use client";

import { motion, useReducedMotion } from "framer-motion";
import { GitBranch, Play, RotateCcw } from "lucide-react";
import type { DemoScenario, ValidationVerdict } from "@/lib/contracts";
import type { CaseStatus } from "@/lib/investigation";

// Situation launcher — the primary, unmissable control to test a situation.
// Previously the run controls hid inside the gear DebugDock; this surfaces them
// as a labelled bar at the top of the monitor. Idle → a hero invitation to
// launch; active → a slim status strip that keeps Reset within reach. Wired to
// the page's existing runScenario / reset (logic unchanged). Sky-blue brand
// chrome; the live-stream state reads as a tricolore pill.
export function SituationLauncher({
  caseStatus,
  running,
  canValidate,
  streamNote,
  onRun,
  onReset,
  onValidate,
}: {
  caseStatus: CaseStatus;
  running: boolean;
  canValidate: boolean;
  streamNote: string | null;
  onRun: (scenario: DemoScenario) => void;
  onReset: () => void;
  onValidate: (verdict: ValidationVerdict) => void;
}) {
  const reduce = useReducedMotion();
  const awaitingValidation = caseStatus === "awaiting-validation";
  return (
    <motion.div layout={!reduce} className="flex shrink-0 flex-wrap items-center justify-end gap-2">
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={running || (awaitingValidation && !canValidate)}
          onClick={() => awaitingValidation ? onValidate("real") : onRun("confirm")}
          className="inline-flex h-11 items-center gap-2 rounded-md bg-[#0078AE] px-3 lg:h-9 text-[13px] font-semibold text-white transition-all duration-300 ease-mech hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Play className="h-4 w-4" fill="currentColor" />
          {running ? "Starting…" : awaitingValidation ? "Confirm verdict" : "Run incident"}
        </button>
        <button
          type="button"
          disabled={running || (awaitingValidation && !canValidate)}
          onClick={() => awaitingValidation ? onValidate("false") : onRun("pivot")}
          className="inline-flex h-11 items-center gap-2 rounded-md border border-[#0078AE]/50 px-3 lg:h-9 text-[13px] font-semibold text-[#0078AE] transition-colors hover:bg-[#0078AE]/[0.06] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <GitBranch className="h-4 w-4" />
          {awaitingValidation ? "Pivot diagnosis" : "Run pivot path"}
        </button>
        <button
          type="button"
          onClick={onReset}
          className="inline-flex h-11 items-center gap-2 rounded-md border border-border bg-transparent px-3 lg:h-9 text-[13px] font-semibold text-textSecondary transition-colors hover:border-borderStrong hover:text-text"
        >
          <RotateCcw className="h-4 w-4" />
          Reset
        </button>
      </div>

      {streamNote && <p className="w-full text-right font-mono text-[10px] text-warn">{streamNote}</p>}
    </motion.div>
  );
}
