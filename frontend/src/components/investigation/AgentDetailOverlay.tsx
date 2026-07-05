"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect } from "react";
import { EASE_MECH } from "@/motion/tokens";
import {
  AGENTS,
  type ActivityEntry,
  type AgentId,
  type AgentStatus,
  type ChosenResponder,
  type MatchingSnapshot,
} from "@/lib/investigation";
import { AgentTerminal } from "./AgentTerminal";
import { MatchingReveal } from "./MatchingReveal";

// AgentDetailOverlay — the rich, non-blocking detail surface raised when a node
// in the orchestration graph is clicked. It centers a large dark panel over the
// live graph WITHOUT pausing the SSE stream: the graph keeps updating behind
// the backdrop and the panel re-renders from fresh props every tick, so closing
// (X / Esc / click-outside) returns to the already-advanced live view.
//   • matching node → MatchingReveal (the live employee-selection viz)
//   • every other node → AgentTerminal (the agent's live console)

const STATUS_LABEL: Record<AgentStatus, { label: string; cls: string }> = {
  monitoring: { label: "monitoring", cls: "text-[#6fb2ff]" },
  active: { label: "working", cls: "text-[#3ea9db]" },
  standby: { label: "standby", cls: "text-white/40" },
  done: { label: "done", cls: "text-[#4fdca0]" },
};

export function AgentDetailOverlay({
  agent,
  agents,
  activity,
  matching,
  responder,
  onClose,
}: {
  agent: AgentId | null;
  agents: Record<AgentId, AgentStatus>;
  activity: ActivityEntry[];
  matching: MatchingSnapshot | null;
  responder: ChosenResponder | null;
  onClose: () => void;
}) {
  const reduce = useReducedMotion();

  // Esc closes — bound only while open.
  useEffect(() => {
    if (!agent) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [agent, onClose]);

  const info = agent ? AGENTS[agent] : null;
  const status = agent ? agents[agent] : "standby";
  const isMatching = agent === "matching";

  return (
    <AnimatePresence>
      {agent && info && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-8"
          initial={reduce ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={reduce ? undefined : { opacity: 0 }}
          transition={{ duration: 0.25 }}
        >
          {/* backdrop — click-outside closes */}
          <button
            type="button"
            aria-label="Close detail"
            onClick={onClose}
            className="absolute inset-0 cursor-default bg-black/55 backdrop-blur-[3px]"
          />

          {/* panel */}
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={`${info.name} — live detail`}
            initial={reduce ? false : { opacity: 0, scale: 0.965, y: 14 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={reduce ? undefined : { opacity: 0, scale: 0.975, y: 10 }}
            transition={{ duration: 0.32, ease: EASE_MECH }}
            className="relative flex h-[80vh] max-h-[760px] w-full max-w-[860px] flex-col overflow-hidden rounded-2xl border border-surface-line bg-surface shadow-[0_40px_120px_-30px_rgba(0,0,0,0.9)]"
          >
            {/* header */}
            <header className="flex shrink-0 items-start justify-between gap-4 border-b border-surface-line bg-surface-raised px-5 py-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2.5">
                  <span
                    className={[
                      "h-2 w-2 rounded-full",
                      status === "active" ? "bg-[#3ea9db] animate-signal-pulse" : status === "done" ? "bg-[#4fdca0]" : status === "monitoring" ? "bg-[#6fb2ff]" : "bg-white/25",
                    ].join(" ")}
                  />
                  <h2 className="font-display text-h5 font-semibold text-white">{info.name}</h2>
                  <span className={`font-mono text-[11px] uppercase tracking-wide ${STATUS_LABEL[status].cls}`}>
                    ● {STATUS_LABEL[status].label}
                  </span>
                </div>
                <p className="mt-1 max-w-2xl text-body-sm leading-snug text-white/50">{info.role}</p>
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-surface-line bg-surface text-white/60 transition-colors hover:bg-white/10 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </header>

            {/* body */}
            <div className="min-h-0 flex-1 overflow-hidden p-5">
              {isMatching ? (
                <MatchingReveal matching={matching} responder={responder} />
              ) : (
                <AgentTerminal agent={agent} status={status} activity={activity} />
              )}
            </div>

            {/* footer hint */}
            <footer className="flex shrink-0 items-center justify-between border-t border-surface-line bg-surface-raised px-5 py-2.5">
              <span className="font-mono text-[10px] uppercase tracking-label text-white/35">
                live · graph keeps running behind
              </span>
              <span className="font-mono text-[10px] text-white/35">esc / click outside to close</span>
            </footer>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
