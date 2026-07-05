"use client";

/**
 * §07 — grounding & citations. Each claim the agent makes is tethered to a
 * specific page of the carrier's own docs. The diagram cycles through three
 * claims; the active one lights, and a sky-blue tether draws to the exact
 * source card + page it cites — the same clickable sources that ship in the
 * final action report.
 *
 * Theme-aware neutrals (CSS vars), static tricolore accents, reduced-motion safe.
 */
import { memo } from "react";
import { motion } from "framer-motion";
import { FileText } from "lucide-react";
import { ACCENT, useAutoCycle, type AccentKey } from "./schematic-kit";

interface Link {
  claim: string;
  source: string;
  page: string;
  accent: AccentKey;
}
const LINKS: Link[] = [
  { claim: "Rectifier module PN-RECT-48-2000 is the fault origin", source: "Rectifier Maintenance Manual", page: "p. 42", accent: "arc" },
  { claim: "Site draws from the −48 V DC power plant on feed B", source: "PAR-021-NORD site dossier", page: "p. 7", accent: "ember" },
  { claim: "Swap procedure requires an isolation step first", source: "Field Repair Procedure R-118", page: "§ 3.2", accent: "resolve" },
];

function GroundedCitationsImpl() {
  const { ref, active } = useAutoCycle(LINKS.length, 2200);

  return (
    <div ref={ref} className="grid gap-6 lg:grid-cols-[1fr_auto_1fr] items-center">
      {/* claims */}
      <div className="space-y-3">
        <p className="section-label mb-1">Agent claims</p>
        {LINKS.map((l, i) => {
          const on = i === active;
          const c = ACCENT[l.accent];
          return (
            <motion.div
              key={l.claim}
              className="rounded-card border p-3.5"
              animate={{
                borderColor: on ? c : "#E6E5DD",
                backgroundColor: on ? "#FFFFFF" : "#F3F2EC",
                opacity: on ? 1 : 0.6,
              }}
              transition={{ duration: 0.35 }}
            >
              <div className="flex items-start gap-2.5">
                <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: c }} />
                <p className="text-[13.5px] leading-snug text-ink">{l.claim}</p>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* tether — animated citation beam */}
      <div className="hidden lg:block">
        <svg viewBox="0 0 120 200" width="120" height="200" role="img" aria-label="Citation tether linking the active claim to its source document.">
          <defs>
            <marker id="cite-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill={ACCENT[LINKS[active].accent]} />
            </marker>
          </defs>
          <motion.path
            key={active}
            d="M 4,100 C 55,100 65,100 116,100"
            fill="none"
            stroke={ACCENT[LINKS[active].accent]}
            strokeWidth={2}
            markerEnd="url(#cite-arrow)"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          />
          <path
            d="M 4,100 C 55,100 65,100 116,100"
            fill="none"
            stroke={ACCENT[LINKS[active].accent]}
            strokeWidth={2}
            strokeLinecap="round"
            strokeDasharray="3 8"
            className="animate-dash-flow"
            opacity={0.7}
          />
        </svg>
      </div>

      {/* sources */}
      <div className="space-y-3">
        <p className="section-label mb-1">Carrier&apos;s own docs</p>
        {LINKS.map((l, i) => {
          const on = i === active;
          const c = ACCENT[l.accent];
          return (
            <motion.div
              key={l.source}
              className="rounded-card border p-3.5"
              animate={{
                borderColor: on ? c : "#E6E5DD",
                backgroundColor: on ? "#FFFFFF" : "#F3F2EC",
                opacity: on ? 1 : 0.6,
              }}
              transition={{ duration: 0.35 }}
            >
              <div className="flex items-center gap-2.5">
                <FileText className="h-4 w-4 shrink-0" style={{ color: c }} />
                <div className="min-w-0">
                  <p className="truncate text-[13.5px] font-medium text-ink">{l.source}</p>
                  <p className="font-mono text-[11px]" style={{ color: c }}>
                    cited · {l.page}
                  </p>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

export const GroundedCitations = memo(GroundedCitationsImpl);
export default GroundedCitations;
