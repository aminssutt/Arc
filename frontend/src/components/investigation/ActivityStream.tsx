"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { EASE_MECH } from "@/motion/tokens";
import type { ActivityEntry, FlowTone } from "@/lib/investigation";

// Live reasoning stream — a compact, animated log of what each agent is doing,
// driven by the real SSE events already in state (agent_started/completed,
// retrieval_performed, diagnostic_ready, push_sent, awaiting_field_validation,
// validation_result, remediation_ready, action_report_ready, incident_resolved).
// Newest first, capped so the rail never overflows. AnimatePresence streams new
// lines in from the top; reduced-motion collapses the animation.

const TONE_DOT: Record<FlowTone, string> = {
  primary: "bg-[#0078AE]",
  warning: "bg-warn",
  neutral: "bg-arc",
  secondary: "bg-resolve",
};

const TONE_TEXT: Record<FlowTone, string> = {
  primary: "text-[#0078AE]",
  warning: "text-warn",
  neutral: "text-arc",
  secondary: "text-resolve",
};

export function ActivityStream({ activity }: { activity: ActivityEntry[] }) {
  const reduce = useReducedMotion();
  // Newest first, capped — the stream is a live tail, not an archive.
  const rows = [...activity].reverse().slice(0, 9);
  const live = activity.length > 0;

  return (
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border border-borderSubtle bg-panelMuted">
      <header className="flex shrink-0 items-center justify-between border-b border-borderSubtle px-3 py-2.5">
        <span className="font-mono text-[11px] font-semibold uppercase tracking-label text-textSecondary">
          Reasoning stream
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            className={[
              "h-1.5 w-1.5 rounded-full",
              live ? "bg-[#0078AE]" : "bg-muted",
              live && !reduce ? "animate-signal-pulse" : "",
            ].join(" ")}
          />
          <span className="font-mono text-[10px] uppercase tracking-wide text-muted">
            {live ? "live" : "idle"}
          </span>
        </span>
      </header>

      <div className="scroll-slim min-h-0 flex-1 overflow-y-auto px-3 py-2">
        {rows.length === 0 ? (
          <p className="py-6 text-center text-body-sm text-muted">
            Agent activity will stream here as the Orchestrator drives the run.
          </p>
        ) : (
          <ul className="flex flex-col gap-2.5">
            <AnimatePresence initial={false}>
              {rows.map((entry) => (
                <motion.li
                  key={entry.id}
                  layout={!reduce}
                  initial={reduce ? false : { opacity: 0, y: -8, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: "auto" }}
                  exit={reduce ? undefined : { opacity: 0 }}
                  transition={{ duration: 0.32, ease: EASE_MECH }}
                  className="flex gap-2.5"
                >
                  <span className="relative mt-1 flex shrink-0 flex-col items-center">
                    <span className={`h-2 w-2 rounded-full ${TONE_DOT[entry.tone]}`} />
                    <span className="mt-0.5 w-px flex-1 bg-borderSubtle" />
                  </span>
                  <span className="flex min-w-0 flex-col gap-0.5 pb-1">
                    <span className="flex items-baseline gap-2">
                      <span className={`text-body-sm font-semibold ${TONE_TEXT[entry.tone]}`}>
                        {entry.label}
                      </span>
                      <span className="ml-auto shrink-0 font-mono text-[10px] text-muted">
                        {entry.timestamp}
                      </span>
                    </span>
                    <span className="text-caption leading-snug text-textSecondary">{entry.detail}</span>
                  </span>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </div>
    </section>
  );
}
