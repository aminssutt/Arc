"use client";

/**
 * §04 — THE signature diagram, faithful to `backend/app/orchestrator.py`.
 * A serpentine "detection → cited action" pipeline:
 *
 *   TOP  (Phase 1) :  Fault ▸ Correlate ▸ Root-Cause ▸ Match responder ▸
 *                     Push → Field validation (human)
 *   drop (CONFIRMED) ▸ into the bottom lane
 *   BOTTOM (Phase 2, R→L) :  Remediate ▸ Cost/Inventory/Dispatch ▸ Cited report
 *   loop (REFUSED)  :  Field validation ⟲ back to Root-Cause (pivot / re-diagnose)
 *
 * A single active-stage pointer walks the happy path, lighting each node and its
 * incoming beam with a sky-blue dash-flow. The CONFIRMED artery keeps a permanent
 * subtle flow; the REFUSED pivot is a neutral-slate exception path. Theme-aware
 * (neutrals via CSS vars, accents static sky-blue), reduced-motion safe.
 */
import { memo } from "react";
import { motion } from "framer-motion";
import { EASE_EXPO } from "@/motion/tokens";
import { ACCENT, NEUTRAL, ON_ACCENT, useAutoCycle, type AccentKey } from "./schematic-kit";

const W = 1180;
const H = 400;
const NW = 196;
const NH = 72;

const TOP_Y = 64;
const BOT_Y = 280;
const TOP_CY = TOP_Y + NH / 2; // 100
const BOT_CY = BOT_Y + NH / 2; // 316

interface Node {
  x: number;
  y: number;
  tag: string;
  title: string;
  sub: string;
  accent: AccentKey;
}

// index order == happy-path walk order
const NODES: Node[] = [
  { x: 20, y: TOP_Y, tag: "01 · DETECT", title: "Fault", sub: "PAR-021-NORD", accent: "ember" },
  { x: 256, y: TOP_Y, tag: "02", title: "Correlate", sub: "topology + alarms", accent: "arc" },
  { x: 492, y: TOP_Y, tag: "03", title: "Root-Cause", sub: "grounded · cited", accent: "arc" },
  { x: 728, y: TOP_Y, tag: "04", title: "Match responder", sub: "one tech · scored", accent: "ember" },
  { x: 964, y: TOP_Y, tag: "HUMAN", title: "Field validation", sub: "push → on-site verdict", accent: "warn" },
  { x: 964, y: BOT_Y, tag: "05", title: "Remediate", sub: "fix procedure · cited", accent: "resolve" },
  { x: 492, y: BOT_Y, tag: "06", title: "Cost / Inv / Dispatch", sub: "cost · part · crew", accent: "warn" },
  { x: 20, y: BOT_Y, tag: "REPORT", title: "Cited report", sub: "clickable sources", accent: "resolve" },
];

const cx = (n: Node) => n.x + NW / 2;

interface Conn {
  d: string;
  feeds: number;
  arrow: string;
}

const line = (x1: number, y1: number, x2: number, y2: number) => `M ${x1},${y1} L ${x2},${y2}`;

const CONNS: Conn[] = [
  // top row, L→R (Phase 1 → human)
  { d: line(216, TOP_CY, 256, TOP_CY), feeds: 1, arrow: "arc-arrow" },
  { d: line(452, TOP_CY, 492, TOP_CY), feeds: 2, arrow: "arc-arrow" },
  { d: line(688, TOP_CY, 728, TOP_CY), feeds: 3, arrow: "arc-arrow" },
  { d: line(924, TOP_CY, 964, TOP_CY), feeds: 4, arrow: "arc-arrow" },
  // bottom row, R→L (Phase 2)
  { d: line(964, BOT_CY, 688, BOT_CY), feeds: 6, arrow: "arc-arrow" },
  { d: line(492, BOT_CY, 216, BOT_CY), feeds: 7, arrow: "arc-arrow" },
];

// CONFIRMED artery — vertical drop from Field validation to Remediate
const CONFIRMED_D = line(cx(NODES[4]), TOP_Y + NH, cx(NODES[5]), BOT_Y);
// REFUSED pivot — arc from Field validation top back to Root-Cause top
const REFUSED_D = `M ${cx(NODES[4])},${TOP_Y} C ${cx(NODES[4]) - 40},${TOP_Y - 44} ${cx(NODES[2]) + 40},${TOP_Y - 44} ${cx(NODES[2])},${TOP_Y}`;

function FaultPipelineImpl() {
  const { ref, active } = useAutoCycle(NODES.length, 1500);

  return (
    <div ref={ref} className="w-full">
      <div className="overflow-x-auto scroll-slim">
        <motion.svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full min-w-[980px]"
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "0px 0px -12% 0px" }}
          role="img"
          aria-label="The Arc pipeline: a fault at PAR-021-NORD is correlated and root-caused with cited grounding, then Responder-Matching picks and pushes to a single field technician for on-site validation. On confirmation it flows to remediation, a single cost/inventory/dispatch agent, and a cited action report. On refusal it pivots back to re-diagnose."
        >
          <defs>
            <marker id="arc-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill="#8A897F" />
            </marker>
            <marker id="arc-arrow-resolve" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7.5" markerHeight="7.5" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill={ACCENT.resolve} />
            </marker>
            <marker id="arc-arrow-danger" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7.5" markerHeight="7.5" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill={ACCENT.danger} />
            </marker>
          </defs>

          {/* ── straight connectors ─────────────────────────────────────── */}
          {CONNS.map((c, i) => {
            const on = c.feeds === active;
            const accent = ACCENT[NODES[c.feeds].accent];
            return (
              <g key={`c-${i}`}>
                <motion.path
                  d={c.d}
                  fill="none"
                  style={{ stroke: NEUTRAL.borderStrong }}
                  strokeWidth={1.4}
                  markerEnd={`url(#${c.arrow})`}
                  variants={{
                    hidden: { pathLength: 0, opacity: 0 },
                    show: { pathLength: 1, opacity: 1, transition: { duration: 0.5, ease: EASE_EXPO, delay: 0.3 + i * 0.05 } },
                  }}
                />
                {on && (
                  <path d={c.d} fill="none" stroke={accent} strokeWidth={2.5} strokeLinecap="round" strokeDasharray="5 9" className="animate-dash-flow" opacity={0.95} />
                )}
              </g>
            );
          })}

          {/* ── CONFIRMED artery (permanent subtle resolve flow) ────────── */}
          <motion.path
            d={CONFIRMED_D}
            fill="none"
            stroke={ACCENT.resolve}
            strokeWidth={active === 5 ? 2.5 : 1.75}
            markerEnd="url(#arc-arrow-resolve)"
            variants={{
              hidden: { pathLength: 0, opacity: 0 },
              show: { pathLength: 1, opacity: 1, transition: { duration: 0.6, ease: EASE_EXPO, delay: 0.6 } },
            }}
          />
          <path d={CONFIRMED_D} fill="none" stroke={ACCENT.resolve} strokeWidth={2.5} strokeLinecap="round" strokeDasharray="4 10" className="animate-dash-flow" opacity={active === 5 ? 0.95 : 0.45} />
          <text x={cx(NODES[4]) + 10} y={TOP_Y + NH + 44} className="font-mono" fontSize={9} letterSpacing="1" fill={ACCENT.resolve}>
            CONFIRMED
          </text>

          {/* ── REFUSED pivot loop (permanent subtle slate exception flow) ─ */}
          <motion.path
            d={REFUSED_D}
            fill="none"
            stroke={ACCENT.danger}
            strokeWidth={1.6}
            strokeDasharray="5 5"
            markerEnd="url(#arc-arrow-danger)"
            variants={{
              hidden: { pathLength: 0, opacity: 0 },
              show: { pathLength: 1, opacity: 1, transition: { duration: 0.7, ease: EASE_EXPO, delay: 0.75 } },
            }}
          />
          <path d={REFUSED_D} fill="none" stroke={ACCENT.danger} strokeWidth={2} strokeLinecap="round" strokeDasharray="3 9" className="animate-dash-flow" opacity={0.6} />
          <text x={(cx(NODES[2]) + cx(NODES[4])) / 2} y={TOP_Y - 32} textAnchor="middle" className="font-mono" fontSize={9} letterSpacing="1" fill={ACCENT.danger}>
            REFUSED · re-diagnose
          </text>

          {/* ── nodes ───────────────────────────────────────────────────── */}
          {NODES.map((n, i) => {
            const on = i === active;
            const c = ACCENT[n.accent];
            return (
              <motion.g
                key={n.title}
                variants={{
                  hidden: { opacity: 0, y: 10, scale: 0.96 },
                  show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.5, ease: EASE_EXPO, delay: 0.15 + i * 0.07 } },
                }}
                style={{ transformOrigin: `${cx(n)}px ${n.y + NH / 2}px` }}
              >
                {on && (
                  <rect x={n.x - 4} y={n.y - 4} width={NW + 8} height={NH + 8} rx={16} fill="none" stroke={c} strokeWidth={1} opacity={0.35} />
                )}
                <rect
                  x={n.x}
                  y={n.y}
                  width={NW}
                  height={NH}
                  rx={13}
                  fill={on ? c : NEUTRAL.panel}
                  style={{ stroke: on ? c : NEUTRAL.border, transition: "fill 0.35s ease" }}
                  strokeWidth={on ? 2 : 1.25}
                />
                <circle cx={n.x + 18} cy={n.y + 20} r={4} fill={on ? ON_ACCENT[n.accent] : c} className={on ? "animate-signal-pulse" : ""} />
                <text x={n.x + 30} y={n.y + 23} className="font-mono" fontSize={8.5} letterSpacing="1.2" fill={on ? ON_ACCENT[n.accent] : c} fillOpacity={on ? 0.85 : 1}>
                  {n.tag}
                </text>
                <text
                  x={n.x + 18}
                  y={n.y + 46}
                  className="font-display"
                  fontSize={16}
                  fontWeight={600}
                  fill={on ? ON_ACCENT[n.accent] : undefined}
                  style={on ? undefined : { fill: NEUTRAL.text }}
                >
                  {n.title}
                </text>
                <text
                  x={n.x + 18}
                  y={n.y + 62}
                  className="font-mono"
                  fontSize={9.5}
                  fill={on ? ON_ACCENT[n.accent] : undefined}
                  fillOpacity={on ? 0.7 : 1}
                  style={on ? undefined : { fill: NEUTRAL.muted }}
                >
                  {n.sub}
                </text>
              </motion.g>
            );
          })}
        </motion.svg>
      </div>

      {/* legend */}
      <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-[11px] text-ink-soft">
        <span className="inline-flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: ACCENT.resolve }} /> confirmed → remediate
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: ACCENT.danger }} /> refused → pivot &amp; re-diagnose
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: ACCENT.warn }} /> human field veto
        </span>
      </div>
    </div>
  );
}

export const FaultPipeline = memo(FaultPipelineImpl);
export default FaultPipeline;
