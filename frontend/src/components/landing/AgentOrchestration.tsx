"use client";

/**
 * §02 — the orchestration schematic, faithful to `backend/app/orchestrator.py`.
 *
 * The Watchdog is the DETECTOR: it watches every live feed and, on a
 * `fault_detected`, hands the incident to the Orchestrator — it is NOT a peer
 * specialist. The Orchestrator (Arc's own custom orchestrator, on Vultr) is the hub; it routes typed
 * state to the six specialist agents that form the vertical SIDE RAIL, in the
 * real pipeline order: Correlation ▸ Root-Cause ▸ Responder-Matching ▸
 * Validation ▸ Remediation ▸ Cost/Inventory/Dispatch (ONE agent). A dispatch
 * beam cycles hub → specialist, lighting one rail row at a time.
 *
 * Self-contained + theme-aware: neutrals resolve via CSS vars, accents are the
 * static sky-blue family, auto-cycles only while in view, respects reduced motion.
 */
import { memo } from "react";
import { motion } from "framer-motion";
import { EASE_EXPO } from "@/motion/tokens";
import { ACCENT, NEUTRAL, ON_ACCENT, useAutoCycle, type AccentKey } from "./schematic-kit";

const W = 720;
const H = 452;

// watchdog (detector) — feeds the hub
const WD = { x: 20, y: 36, w: 182, h: 60 };

// hub geometry (left)
const HUB = { x: 20, y: 178, w: 182, h: 108 };
const HUB_OUT: [number, number] = [HUB.x + HUB.w, HUB.y + HUB.h / 2];
const HUB_CX = HUB.x + HUB.w / 2;

// rail geometry (right)
const RAIL_X = 430;
const RAIL_W = 272;
const ROW_H = 60;
const ROW_GAP = 9;
const RAIL_TOP = 14;

const rowY = (i: number) => RAIL_TOP + i * (ROW_H + ROW_GAP);
const rowIn = (i: number): [number, number] => [RAIL_X, rowY(i) + ROW_H / 2];

function beamPath(i: number): string {
  const [x1, y1] = HUB_OUT;
  const [x2, y2] = rowIn(i);
  const mx = (x1 + x2) / 2;
  return `M ${x1},${y1} C ${mx},${y1} ${mx},${y2} ${x2},${y2}`;
}

interface Spec {
  name: string;
  role: string;
  accent: AccentKey;
  blurb: string;
}

// The REAL specialist roster, in the REAL routed order (orchestrator.py).
const SPECIALISTS: Spec[] = [
  { name: "Correlation", role: "topology + alarms", accent: "arc", blurb: "fuses the alarm storm with the network topology to isolate the one site that matters — and its equipment class." },
  { name: "Root-Cause", role: "grounded diagnosis", accent: "arc", blurb: "confidence-gated retrieval over the carrier's own technical docs and history — every ranked cause is cited." },
  { name: "Responder-Matching", role: "picks ONE tech", accent: "ember", blurb: "scores field technicians on competence × difficulty-fit × zone and notifies the single best responder — not a broadcast." },
  { name: "Validation", role: "human field loop", accent: "warn", blurb: "reads the technician's on-site verdict: confirm advances the pipeline; refuse pivots it back to re-diagnose." },
  { name: "Remediation", role: "cited fix procedure", accent: "resolve", blurb: "assembles the exact repair procedure — steps and safety — from the confirmed root cause, each step cited." },
  { name: "Cost / Inventory / Dispatch", role: "cost · part · crew", accent: "warn", blurb: "one agent: prices the fix, matches the part against live inventory, and books the crew." },
];

function AgentOrchestrationImpl() {
  const { ref, active } = useAutoCycle(SPECIALISTS.length, 1650);
  const activeSpec = SPECIALISTS[active];

  return (
    <div ref={ref} className="w-full">
      <div className="overflow-x-auto scroll-slim">
        <motion.svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full min-w-[620px]"
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "0px 0px -12% 0px" }}
          role="img"
          aria-label="The Watchdog detects a site fault and hands it to the Orchestrator, which routes typed state to six specialist agents in order: Correlation, Root-Cause, Responder-Matching, Validation, Remediation, and a single Cost/Inventory/Dispatch agent."
        >
          <defs>
            <radialGradient id="arc-route-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor={ACCENT.arc} stopOpacity="0.22" />
              <stop offset="100%" stopColor={ACCENT.arc} stopOpacity="0" />
            </radialGradient>
            <marker id="ao-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill={ACCENT.ember} />
            </marker>
          </defs>

          {/* beams hub → rows */}
          {SPECIALISTS.map((s, i) => {
            const on = i === active;
            const c = ACCENT[s.accent];
            return (
              <g key={`beam-${s.name}`}>
                <motion.path
                  d={beamPath(i)}
                  fill="none"
                  style={{ stroke: on ? c : NEUTRAL.border }}
                  strokeWidth={on ? 2 : 1.25}
                  variants={{
                    hidden: { pathLength: 0, opacity: 0 },
                    show: {
                      pathLength: 1,
                      opacity: 1,
                      transition: { duration: 0.8, ease: EASE_EXPO, delay: 0.2 + i * 0.06 },
                    },
                  }}
                />
                {on && (
                  <path
                    d={beamPath(i)}
                    fill="none"
                    stroke={c}
                    strokeWidth={2.5}
                    strokeLinecap="round"
                    strokeDasharray="5 10"
                    className="animate-dash-flow"
                    opacity={0.9}
                  />
                )}
              </g>
            );
          })}

          {/* watchdog (detector) → hub */}
          <motion.g
            variants={{
              hidden: { opacity: 0, y: -10 },
              show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE_EXPO } },
            }}
          >
            <rect x={WD.x} y={WD.y} width={WD.w} height={WD.h} rx={13} fill={NEUTRAL.panel} stroke={ACCENT.ember} strokeWidth={1.5} />
            <circle cx={WD.x + 20} cy={WD.y + WD.h / 2} r={4} fill={ACCENT.ember} className="animate-signal-pulse" />
            <text x={WD.x + 36} y={WD.y + 26} className="font-display" fontSize={15} fontWeight={600} style={{ fill: NEUTRAL.text }}>
              Watchdog
            </text>
            <text x={WD.x + 36} y={WD.y + 44} className="font-mono" fontSize={9.5} style={{ fill: NEUTRAL.muted }}>
              detects site faults
            </text>
          </motion.g>
          <motion.path
            d={`M ${HUB_CX},${WD.y + WD.h} L ${HUB_CX},${HUB.y}`}
            fill="none"
            stroke={ACCENT.ember}
            strokeWidth={1.6}
            markerEnd="url(#ao-arrow)"
            variants={{
              hidden: { pathLength: 0, opacity: 0 },
              show: { pathLength: 1, opacity: 1, transition: { duration: 0.5, ease: EASE_EXPO, delay: 0.15 } },
            }}
          />
          <path
            d={`M ${HUB_CX},${WD.y + WD.h} L ${HUB_CX},${HUB.y}`}
            fill="none"
            stroke={ACCENT.ember}
            strokeWidth={2}
            strokeLinecap="round"
            strokeDasharray="4 8"
            className="animate-dash-flow"
            opacity={0.7}
          />
          <text x={HUB_CX + 8} y={(WD.y + WD.h + HUB.y) / 2 + 3} className="font-mono" fontSize={8.5} letterSpacing="0.5" fill={ACCENT.ember}>
            fault_detected
          </text>

          {/* hub glow + node */}
          <circle cx={HUB_OUT[0] - 30} cy={HUB_OUT[1]} r={130} fill="url(#arc-route-glow)" />
          <motion.g
            variants={{
              hidden: { opacity: 0, scale: 0.85 },
              show: { opacity: 1, scale: 1, transition: { duration: 0.6, ease: EASE_EXPO } },
            }}
            style={{ transformOrigin: `${HUB.x + HUB.w / 2}px ${HUB.y + HUB.h / 2}px` }}
          >
            <rect x={HUB.x} y={HUB.y} width={HUB.w} height={HUB.h} rx={16} fill="#0b1220" stroke={ACCENT.arc} strokeWidth={1.5} />
            <circle cx={HUB.x + 20} cy={HUB.y + 24} r={4} fill={ACCENT.arc} className="animate-signal-pulse" />
            <text x={HUB.x + 34} y={HUB.y + 28} className="font-mono" fontSize={8.5} letterSpacing="0.5" fill={ACCENT.arc}>
              ARC ORCHESTRATOR · VULTR
            </text>
            <text x={HUB.x + 20} y={HUB.y + 60} className="font-display" fontSize={20} fontWeight={600} fill="#FAFAF7">
              Orchestrator
            </text>
            <text x={HUB.x + 20} y={HUB.y + 84} className="font-mono" fontSize={10} fill="#9FB6C9">
              routes typed state
            </text>
          </motion.g>

          {/* rail rows */}
          {SPECIALISTS.map((s, i) => {
            const on = i === active;
            const c = ACCENT[s.accent];
            const y = rowY(i);
            return (
              <motion.g
                key={s.name}
                variants={{
                  hidden: { opacity: 0, x: 14 },
                  show: {
                    opacity: 1,
                    x: 0,
                    transition: { duration: 0.5, ease: EASE_EXPO, delay: 0.3 + i * 0.06 },
                  },
                }}
              >
                <rect
                  x={RAIL_X}
                  y={y}
                  width={RAIL_W}
                  height={ROW_H}
                  rx={12}
                  fill={on ? c : NEUTRAL.panel}
                  style={{ stroke: on ? c : NEUTRAL.border, transition: "fill 0.4s ease" }}
                  strokeWidth={on ? 1.75 : 1.25}
                />
                <circle
                  cx={RAIL_X + 20}
                  cy={y + ROW_H / 2}
                  r={4.5}
                  fill={on ? ON_ACCENT[s.accent] : c}
                  style={{ transition: "fill 0.4s ease" }}
                />
                <text
                  x={RAIL_X + 38}
                  y={y + 26}
                  className="font-display"
                  fontSize={14.5}
                  fontWeight={600}
                  fill={on ? ON_ACCENT[s.accent] : undefined}
                  style={on ? undefined : { fill: NEUTRAL.text }}
                >
                  {s.name}
                </text>
                <text
                  x={RAIL_X + 38}
                  y={y + 44}
                  className="font-mono"
                  fontSize={9.5}
                  fill={on ? ON_ACCENT[s.accent] : undefined}
                  fillOpacity={on ? 0.75 : 1}
                  style={on ? undefined : { fill: NEUTRAL.muted }}
                >
                  {s.role}
                </text>
              </motion.g>
            );
          })}
        </motion.svg>
      </div>

      {/* live caption — the routed specialist's job, in plain language */}
      <div className="mt-5 flex items-start gap-3 min-h-[2.75rem]">
        <span
          className="mt-1 h-2 w-2 shrink-0 rounded-full"
          style={{ background: ACCENT[activeSpec.accent] }}
        />
        <p className="text-[14px] text-ink-soft leading-relaxed">
          <span className="font-mono text-[12px] text-ink mr-1.5">{activeSpec.name}</span>
          {activeSpec.blurb}
        </p>
      </div>
    </div>
  );
}

export const AgentOrchestration = memo(AgentOrchestrationImpl);
export default AgentOrchestration;
