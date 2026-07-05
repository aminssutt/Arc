"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { MapPin, ShieldCheck, UserCheck } from "lucide-react";
import { revealScale } from "@/motion/tokens";
import type { ChosenResponder } from "@/lib/investigation";

// The matching beat — the "routed to ONE technician, not broadcast" moment.
// Surfaces the ResponderMatchingAgent pick (name, tier, zone, why) as a
// distinct card that animates in when the responder is chosen. Sky-blue chrome
// (brand), tricolore for the zone-fit status (in-zone = resolve, hors-zone =
// warn). Renders nothing until a responder lands.
export function MatchingBeat({ responder }: { responder: ChosenResponder | null }) {
  const reduce = useReducedMotion();

  return (
    <AnimatePresence>
      {responder && (
        <motion.section
          key={responder.employeeId}
          variants={revealScale}
          initial={reduce ? "show" : "hidden"}
          animate="show"
          exit={reduce ? undefined : { opacity: 0, y: -6 }}
          className="relative shrink-0 overflow-hidden rounded-md border border-[#0078AE]/60 bg-[#0078AE]/[0.07] p-3.5"
        >
          <span className="absolute inset-x-0 top-0 h-[2px] bg-[#0078AE]" />

          <div className="flex items-center gap-2">
            <UserCheck className="h-4 w-4 text-[#0078AE]" />
            <p className="font-mono text-[10px] font-semibold uppercase tracking-label text-[#0078AE]">
              Routed to ONE technician
            </p>
          </div>

          <div className="mt-2.5 flex items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-[#0078AE] font-mono text-body-sm font-bold text-white">
              {responder.name
                .split(/\s+/)
                .map((part) => part[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()}
            </span>
            <div className="min-w-0">
              <p className="truncate text-body-sm font-semibold text-text">{responder.name}</p>
              <p className="truncate font-mono text-caption text-muted">
                {responder.employeeId}
                {responder.role ? ` · ${responder.role}` : ""}
              </p>
            </div>
          </div>

          <div className="mt-2.5 flex flex-wrap gap-1.5">
            <span className="inline-flex items-center gap-1 rounded border border-[#0078AE]/40 bg-[#0078AE]/10 px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wide text-[#0078AE]">
              <ShieldCheck className="h-3 w-3" />
              {responder.tier}
            </span>
            <span
              className={[
                "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wide",
                responder.outOfZone
                  ? "border-warn/50 bg-warn/10 text-warn"
                  : "border-resolve/50 bg-resolve/10 text-resolve",
              ].join(" ")}
            >
              <MapPin className="h-3 w-3" />
              {responder.outOfZone ? "hors-zone" : "in-zone"}
              {responder.region ? ` · ${responder.region}` : ""}
            </span>
            {responder.difficulty && (
              <span className="inline-flex items-center rounded border border-borderSubtle bg-panel px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wide text-textSecondary">
                {responder.difficulty}
              </span>
            )}
          </div>

          {responder.reason && (
            <p className="mt-2 text-caption leading-snug text-textSecondary">
              <span className="text-muted">why: </span>
              {responder.reason}
            </p>
          )}

          <p className="mt-1.5 text-caption leading-snug text-muted">
            Notified alone — no broadcast to the rest of the crew.
          </p>
        </motion.section>
      )}
    </AnimatePresence>
  );
}
