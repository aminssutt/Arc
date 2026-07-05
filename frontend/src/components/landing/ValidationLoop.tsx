"use client";

/**
 * The human-in-the-loop field-validation cycle, as a circular schematic.
 *
 *   Diagnose ▸ Push (to the technician's phone) ▸ Field test ▸ Verdict
 *   ▸ Pivot (on refusal, re-diagnose) — then round again.
 *
 * The active phase glows and auto-rotates while in view. A rotating dashed guide
 * ring keeps the whole thing alive without being busy. Theme-aware neutrals,
 * static tricolore accents, reduced-motion safe. `compact` shrinks it for the
 * §02 method column; the full size anchors §05.
 */
import { memo } from "react";
import { motion } from "framer-motion";
import { EASE_EXPO } from "@/motion/tokens";
import { ACCENT, NEUTRAL, ON_ACCENT, useAutoCycle, type AccentKey } from "./schematic-kit";

interface Phase {
  key: string;
  label: string;
  agent: string;
  accent: AccentKey;
}

const PHASES: Phase[] = [
  { key: "diagnose", label: "Diagnose", agent: "root-cause", accent: "arc" },
  { key: "push", label: "Push", agent: "→ phone", accent: "ember" },
  { key: "field", label: "Field test", agent: "technician", accent: "warn" },
  { key: "verdict", label: "Verdict", agent: "confirm / refuse", accent: "resolve" },
  { key: "pivot", label: "Pivot", agent: "re-diagnose", accent: "danger" },
];

export function ValidationLoop({ compact = false }: { compact?: boolean }) {
  const SIZE = 460;
  const C = SIZE / 2;
  const RC = compact ? 138 : 152;
  const NODE_R = compact ? 44 : 48;

  const { ref, active } = useAutoCycle(PHASES.length, 1500);

  // Round to a fixed precision so the server- and client-rendered SVG path
  // strings are byte-identical (framer re-serializes `d` on the client, and a
  // last-digit float drift would otherwise trip a hydration mismatch).
  const round = (n: number) => Math.round(n * 1000) / 1000;
  const polar = (r: number, angleDeg: number): [number, number] => {
    const a = (angleDeg * Math.PI) / 180;
    return [round(C + r * Math.cos(a)), round(C + r * Math.sin(a))];
  };
  const nodeAngle = (i: number) => -90 + i * (360 / PHASES.length);
  const offsetDeg = (((NODE_R + 8) / RC) * 180) / Math.PI;

  return (
    <div ref={ref} className={compact ? "w-full max-w-[380px] mx-auto" : "w-full max-w-[460px] mx-auto"}>
      <motion.svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="w-full"
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: "0px 0px -10% 0px" }}
        role="img"
        aria-label="The field-validation loop: diagnose, push to the technician's phone, field test on-site, verdict — confirm or refuse — and pivot to re-diagnose on refusal."
      >
        <defs>
          <marker id="vl-arrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="#8A897F" />
          </marker>
        </defs>

        {/* rotating dashed guide ring */}
        <motion.circle
          cx={C}
          cy={C}
          r={RC}
          fill="none"
          style={{ stroke: NEUTRAL.border }}
          strokeWidth={1}
          strokeDasharray="3 8"
          animate={{ rotate: 360 }}
          transition={{ duration: 34, repeat: Infinity, ease: "linear" }}
        />

        {/* connecting arcs */}
        {PHASES.map((_, i) => {
          const a1 = nodeAngle(i) + offsetDeg;
          const a2 = nodeAngle((i + 1) % PHASES.length) - offsetDeg;
          const [x1, y1] = polar(RC, a1);
          const [x2, y2] = polar(RC, a2);
          const on = i === active;
          const accent = ACCENT[PHASES[i].accent];
          return (
            <motion.path
              key={`arc-${i}`}
              d={`M ${x1},${y1} A ${RC},${RC} 0 0 1 ${x2},${y2}`}
              fill="none"
              stroke={on ? accent : undefined}
              style={on ? undefined : { stroke: NEUTRAL.borderStrong }}
              strokeWidth={on ? 2.5 : 1.4}
              markerEnd="url(#vl-arrow)"
              variants={{
                hidden: { pathLength: 0, opacity: 0 },
                show: { pathLength: 1, opacity: 1, transition: { duration: 0.6, ease: EASE_EXPO, delay: 0.2 + i * 0.09 } },
              }}
            />
          );
        })}

        {/* center label */}
        <text x={C} y={C - 6} textAnchor="middle" className="font-mono" fontSize={9} letterSpacing="2" style={{ fill: NEUTRAL.muted }}>
          HUMAN VETO
        </text>
        <text x={C} y={C + 13} textAnchor="middle" className="font-display" fontSize={16} fontWeight={600} style={{ fill: NEUTRAL.text }}>
          Field loop
        </text>

        {/* phase nodes */}
        {PHASES.map((phase, i) => {
          const [x, y] = polar(RC, nodeAngle(i));
          const on = i === active;
          const c = ACCENT[phase.accent];
          return (
            <motion.g
              key={phase.key}
              variants={{
                hidden: { opacity: 0, scale: 0.6 },
                show: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: EASE_EXPO, delay: 0.3 + i * 0.08 } },
              }}
              style={{ transformOrigin: `${x}px ${y}px` }}
            >
              {on && (
                <motion.circle
                  cx={x}
                  cy={y}
                  r={NODE_R}
                  fill="none"
                  stroke={c}
                  strokeWidth={2}
                  initial={{ scale: 1, opacity: 0.7 }}
                  animate={{ scale: 1.4, opacity: 0 }}
                  transition={{ duration: 1.3, repeat: Infinity, ease: "easeOut" }}
                  style={{ transformOrigin: `${x}px ${y}px` }}
                />
              )}
              <circle
                cx={x}
                cy={y}
                r={NODE_R}
                fill={on ? c : NEUTRAL.panel}
                style={{ stroke: on ? c : NEUTRAL.border, transition: "fill 0.35s ease" }}
                strokeWidth={on ? 2 : 1.4}
              />
              <text x={x} y={y - 4} textAnchor="middle" className="font-mono" fontSize={8} fill={on ? ON_ACCENT[phase.accent] : undefined} fillOpacity={on ? 0.75 : 1} style={on ? undefined : { fill: NEUTRAL.muted }}>
                {String(i + 1).padStart(2, "0")}
              </text>
              <text x={x} y={y + 9} textAnchor="middle" className="font-display" fontSize={12} fontWeight={600} fill={on ? ON_ACCENT[phase.accent] : undefined} style={on ? undefined : { fill: NEUTRAL.text }}>
                {phase.label}
              </text>
              <text x={x} y={y + 21} textAnchor="middle" className="font-mono" fontSize={7} fill={on ? ON_ACCENT[phase.accent] : undefined} fillOpacity={on ? 0.65 : 1} style={on ? undefined : { fill: NEUTRAL.muted }}>
                {phase.agent}
              </text>
            </motion.g>
          );
        })}
      </motion.svg>
    </div>
  );
}

export default memo(ValidationLoop);
