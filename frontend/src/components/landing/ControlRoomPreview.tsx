"use client";

/**
 * §05 — a compact, bespoke preview of the live control room, for the always-dark
 * live "screen" section. LEFT: a miniature network map with the faulted site
 * (PAR-021-NORD) lit in sky blue and a slow radar sweep. RIGHT: a live event
 * stream whose newest row pulses as the "cursor" walks the incident timeline.
 *
 * This is a purpose-built marketing preview — it does NOT import the real
 * investigation components. Fixed dark palette (the section is always dark),
 * reduced-motion safe via useAutoCycle.
 */
import { memo } from "react";
import { motion } from "framer-motion";
import { ACCENT, DARK, useAutoCycle, type AccentKey } from "./schematic-kit";

interface Site {
  id: string;
  x: number;
  y: number;
  fault?: boolean;
}
const SITES: Site[] = [
  { id: "PAR-018", x: 40, y: 48 },
  { id: "PAR-021-NORD", x: 150, y: 110, fault: true },
  { id: "PAR-024", x: 250, y: 60 },
  { id: "PAR-030", x: 88, y: 176 },
  { id: "PAR-033", x: 262, y: 168 },
];
const EDGES: Array<[number, number]> = [
  [0, 1],
  [1, 2],
  [1, 3],
  [1, 4],
  [2, 4],
];

interface Ev {
  t: string;
  agent: string;
  msg: string;
  accent: AccentKey;
}
const EVENTS: Ev[] = [
  { t: "00:00", agent: "Watchdog", msg: "anomaly · PAR-021-NORD", accent: "arc" },
  { t: "00:14", agent: "Correlation", msg: "42 alarms → 1 site", accent: "arc" },
  { t: "00:47", agent: "Root-Cause", msg: "rectifier module · cited", accent: "arc" },
  { t: "01:05", agent: "Responder-Matching", msg: "1 tech · senior · in-zone", accent: "warn" },
  { t: "01:10", agent: "Validation", msg: "push sent → technician", accent: "warn" },
  { t: "02:38", agent: "Field", msg: "CONFIRMED on-site", accent: "resolve" },
  { t: "02:55", agent: "Dispatch", msg: "crew + PN-RECT-48-2000", accent: "resolve" },
];

function ControlRoomPreviewImpl() {
  const { ref, active } = useAutoCycle(EVENTS.length, 1400);

  return (
    <div
      ref={ref}
      className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr] rounded-card border p-4 sm:p-5"
      style={{ background: DARK.panel, borderColor: DARK.border }}
    >
      {/* ── mini network map ─────────────────────────────────────────────── */}
      <div className="relative rounded-[10px] overflow-hidden" style={{ background: DARK.panelMuted }}>
        <div className="absolute left-3 top-3 z-10 font-mono text-[10px] uppercase tracking-label" style={{ color: DARK.muted }}>
          network map
        </div>
        <svg viewBox="0 0 300 224" className="w-full" role="img" aria-label="Miniature network map with the faulted site PAR-021-NORD lit in the centre.">
          {/* radar sweep */}
          <motion.line
            x1={150}
            y1={110}
            x2={150}
            y2={0}
            stroke={ACCENT.arc}
            strokeWidth={1.25}
            opacity={0.28}
            style={{ transformOrigin: "150px 110px" }}
            animate={{ rotate: 360 }}
            transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
          />
          {EDGES.map(([a, b], i) => (
            <line key={i} x1={SITES[a].x} y1={SITES[a].y} x2={SITES[b].x} y2={SITES[b].y} stroke={DARK.border} strokeWidth={1} />
          ))}
          {SITES.map((s) => (
            <g key={s.id}>
              {s.fault && (
                <motion.circle
                  cx={s.x}
                  cy={s.y}
                  r={9}
                  fill="none"
                  stroke={ACCENT.arc}
                  strokeWidth={1.5}
                  initial={{ scale: 1, opacity: 0.7 }}
                  animate={{ scale: 2.6, opacity: 0 }}
                  transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
                  style={{ transformOrigin: `${s.x}px ${s.y}px` }}
                />
              )}
              <circle cx={s.x} cy={s.y} r={s.fault ? 6 : 3.5} fill={s.fault ? ACCENT.arc : DARK.muted} />
              <text x={s.x + (s.fault ? 11 : 8)} y={s.y + 3} className="font-mono" fontSize={7.5} fill={s.fault ? ACCENT.arc : DARK.muted}>
                {s.id}
              </text>
            </g>
          ))}
        </svg>
      </div>

      {/* ── live event stream ────────────────────────────────────────────── */}
      <div className="min-w-0">
        <div className="mb-3 flex items-center justify-between">
          <span className="font-mono text-[10px] uppercase tracking-label" style={{ color: DARK.muted }}>
            live event stream
          </span>
          <span className="inline-flex items-center gap-1.5 font-mono text-[10px]" style={{ color: ACCENT.resolve }}>
            <span className="h-1.5 w-1.5 rounded-full animate-signal-pulse" style={{ background: ACCENT.resolve }} />
            streaming
          </span>
        </div>
        <div className="space-y-1.5">
          {EVENTS.map((e, i) => {
            const on = i === active;
            const c = ACCENT[e.accent];
            return (
              <motion.div
                key={e.t}
                className="flex items-center gap-3 rounded-md px-2.5 py-2"
                animate={{
                  backgroundColor: on ? "rgba(255,255,255,0.05)" : "rgba(255,255,255,0)",
                  opacity: i <= active ? 1 : 0.4,
                }}
                transition={{ duration: 0.3 }}
              >
                <span className="font-mono text-[10px] tabular-nums shrink-0" style={{ color: DARK.muted }}>
                  {e.t}
                </span>
                <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: c, boxShadow: on ? `0 0 8px ${c}` : "none" }} />
                <span className="font-mono text-[11px] shrink-0" style={{ color: c }}>
                  {e.agent}
                </span>
                <span className="truncate text-[12px]" style={{ color: DARK.text }}>
                  {e.msg}
                </span>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export const ControlRoomPreview = memo(ControlRoomPreviewImpl);
export default ControlRoomPreview;
