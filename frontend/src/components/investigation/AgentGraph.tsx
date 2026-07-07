"use client";

import { motion, useReducedMotion } from "framer-motion";
import { MapPin, ShieldCheck, Smartphone, UserCheck } from "lucide-react";
import { Fragment, useEffect, useRef, useState } from "react";
import { RobotIcon } from "@/components/icons";
import { EASE_MECH } from "@/motion/tokens";
import {
  AGENTS,
  AGENT_PIPELINE,
  type ActivityEntry,
  type AgentId,
  type AgentStatus,
  type ChosenResponder,
} from "@/lib/investigation";

// Agent Orchestration viewport — the live agentic flow, rebuilt as a pipeline
// you can watch work in real time. Two bands map 1:1 onto the real backend
// (backend/app/orchestrator.py):
//   • COMMAND — the Watchdog opens the incident, the Arc Orchestrator
//     routes the typed state and feeds the specialist rail;
//   • PIPELINE — Correlation → Root-Cause → Matching → Validation →
//     Remediation → Cost/Dispatch, the exact order the Orchestrator sequences.
// The ACTIVE agent gets a strong "working" treatment (sky-blue pulsing ring,
// shimmer, thinking dots, glow) and its INCOMING beam streams a dash-flow token
// — so the handoff from a finishing agent to the next is legible. The right
// rail carries the live decision, the matching beat, and the reasoning stream.
const CANVAS = { width: 1200, height: 600 };
const SKY = "#0078AE";

type Rect = { x: number; y: number; w: number; h: number };

const RAIL_Y = 322;
const RAIL_W = 150;
const RAIL_H = 210;
const RAIL_X = [40, 234, 428, 622, 816, 1010];

const RECT: Record<AgentId, Rect> = {
  main: { x: 150, y: 26, w: 220, h: 118 },
  orchestrator: { x: 490, y: 26, w: 280, h: 118 },
  correlation: { x: RAIL_X[0], y: RAIL_Y, w: RAIL_W, h: RAIL_H },
  rootCause: { x: RAIL_X[1], y: RAIL_Y, w: RAIL_W, h: RAIL_H },
  matching: { x: RAIL_X[2], y: RAIL_Y, w: RAIL_W, h: RAIL_H },
  validation: { x: RAIL_X[3], y: RAIL_Y, w: RAIL_W, h: RAIL_H },
  remediation: { x: RAIL_X[4], y: RAIL_Y, w: RAIL_W, h: RAIL_H },
  dispatch: { x: RAIL_X[5], y: RAIL_Y, w: RAIL_W, h: RAIL_H },
};

// Node draw order — command band first, then the pipeline left→right.
const NODE_ORDER: AgentId[] = ["main", "orchestrator", ...AGENT_PIPELINE];

// Sky-blue = the brand working color; tricolore carries the STATUS semantics:
// monitoring = arc (dormant Watchdog), active = sky-blue (working), done =
// resolve (validated), standby = ghost. Card surfaces stay theme-aware.
const STATUS_STYLE: Record<
  AgentStatus,
  { card: string; badge: string; label: string; text: string; ring: string; glow: string }
> = {
  monitoring: {
    card: "border-arc/70 bg-panel",
    badge: "bg-arc text-surface",
    label: "monitoring",
    text: "text-arc",
    ring: "rgb(77 157 255)",
    glow: "0 0 24px -6px rgba(77,157,255,0.5)",
  },
  active: {
    card: "border-[#0078AE] bg-panel",
    badge: "bg-[#0078AE] text-white",
    label: "working",
    text: "text-[#0078AE]",
    ring: SKY,
    glow: "0 0 34px -4px rgba(0,120,174,0.65)",
  },
  standby: {
    card: "border-border bg-panelMuted",
    badge: "bg-muted/40 text-background",
    label: "standby",
    text: "text-muted",
    ring: "rgb(148 163 184)",
    glow: "none",
  },
  done: {
    card: "border-resolve bg-resolve/10",
    badge: "bg-resolve text-surface",
    label: "done",
    text: "text-resolve",
    ring: "rgb(62 207 142)",
    glow: "0 0 20px -6px rgba(62,207,142,0.5)",
  },
};

type Point = { x: number; y: number };

function roundedOrthogonalPath(points: Point[], radius = 12): string {
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length - 1; i++) {
    const prev = points[i - 1];
    const corner = points[i];
    const next = points[i + 1];
    const inDir = { x: Math.sign(corner.x - prev.x), y: Math.sign(corner.y - prev.y) };
    const outDir = { x: Math.sign(next.x - corner.x), y: Math.sign(next.y - corner.y) };
    const inLen = Math.abs(corner.x - prev.x) + Math.abs(corner.y - prev.y);
    const outLen = Math.abs(next.x - corner.x) + Math.abs(next.y - corner.y);
    const r = Math.min(radius, inLen / 2, outLen / 2);
    d += ` L ${corner.x - inDir.x * r} ${corner.y - inDir.y * r}`;
    d += ` Q ${corner.x} ${corner.y} ${corner.x + outDir.x * r} ${corner.y + outDir.y * r}`;
  }
  const last = points[points.length - 1];
  d += ` L ${last.x} ${last.y}`;
  return d;
}

function railMid(id: AgentId): number {
  return RECT[id].y + RECT[id].h / 2;
}

// Connectors follow the real routing: Watchdog → Orchestrator, Orchestrator
// feeds the pipeline head, then each specialist hands off to the next.
type Link = { from: AgentId; to: AgentId; points: Point[] };

const LINKS: Link[] = [
  {
    from: "main",
    to: "orchestrator",
    points: [
      { x: RECT.main.x + RECT.main.w, y: railMid("main") },
      { x: RECT.orchestrator.x, y: railMid("orchestrator") },
    ],
  },
  {
    from: "orchestrator",
    to: "correlation",
    points: [
      { x: RECT.orchestrator.x + RECT.orchestrator.w / 2, y: RECT.orchestrator.y + RECT.orchestrator.h },
      { x: RECT.orchestrator.x + RECT.orchestrator.w / 2, y: 236 },
      { x: RECT.correlation.x + RAIL_W / 2, y: 236 },
      { x: RECT.correlation.x + RAIL_W / 2, y: RAIL_Y },
    ],
  },
  ...AGENT_PIPELINE.slice(0, -1).map((from, i): Link => {
    const to = AGENT_PIPELINE[i + 1];
    return {
      from,
      to,
      points: [
        { x: RECT[from].x + RAIL_W, y: RAIL_Y + RAIL_H / 2 },
        { x: RECT[to].x, y: RAIL_Y + RAIL_H / 2 },
      ],
    };
  }),
];

const IDLE_LINK = "rgb(var(--color-border-strong))";

function linkColor(status: AgentStatus): string {
  if (status === "active") return SKY;
  if (status === "done") return "rgb(62 207 142)";
  return IDLE_LINK;
}

function WorkingDots() {
  const reduce = useReducedMotion();
  return (
    <span className="inline-flex items-center gap-[3px]" aria-hidden>
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-1 w-1 rounded-full bg-current"
          animate={reduce ? undefined : { opacity: [0.25, 1, 0.25] }}
          transition={{ duration: 1.1, ease: "easeInOut", repeat: Infinity, delay: i * 0.18 }}
        />
      ))}
    </span>
  );
}

export function AgentGraph({
  agents,
  decisionLabel,
  decisionCopy,
  responder,
  activity,
  selectedAgent,
  onSelectAgent,
}: {
  agents: Record<AgentId, AgentStatus>;
  decisionLabel: string;
  decisionCopy: string;
  responder: ChosenResponder | null;
  activity: ActivityEntry[];
  selectedAgent: AgentId | null;
  onSelectAgent: (id: AgentId | null) => void;
}) {
  const reduce = useReducedMotion();
  const awaitingMobile = agents.validation === "active";

  const fitRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const el = fitRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setScale(Math.min(1, width / CANVAS.width, height / CANVAS.height));
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <>
    {/* ── DESKTOP (≥lg): the fit-to-width canvas — unchanged ───────────────── */}
    <div className="hidden h-full min-h-0 w-full bg-background lg:flex">
      <div ref={fitRef} className="flex min-h-0 min-w-0 flex-1 items-center justify-center">
        <div
          className="relative shrink-0"
          style={{
            width: CANVAS.width,
            height: CANVAS.height,
            transform: `scale(${scale})`,
            transformOrigin: "center",
          }}
        >
          {/* band captions */}
          <span
            className="pointer-events-none absolute font-mono text-[12px] uppercase tracking-label text-muted"
            style={{ left: RECT.main.x, top: 2 }}
          >
            Command
          </span>
          <span
            className="pointer-events-none absolute font-mono text-[12px] uppercase tracking-label text-muted"
            style={{ left: RAIL_X[0], top: 292 }}
          >
            Specialist pipeline · sequenced by the Orchestrator
          </span>

          <svg
            className="pointer-events-none absolute inset-0"
            viewBox={`0 0 ${CANVAS.width} ${CANVAS.height}`}
            width={CANVAS.width}
            height={CANVAS.height}
          >
            {LINKS.map((link, index) => {
              const targetStatus = agents[link.to];
              const color = linkColor(targetStatus);
              const d = roundedOrthogonalPath(link.points);
              const start = link.points[0];
              const end = link.points[link.points.length - 1];
              const flowing = targetStatus === "active";
              return (
                <g key={`${link.from}-${link.to}`}>
                  <motion.path
                    d={d}
                    fill="none"
                    stroke={color}
                    strokeWidth={2.5}
                    initial={reduce ? false : { pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 1 }}
                    transition={{ duration: 0.6, ease: EASE_MECH, delay: 0.1 + index * 0.05 }}
                    style={{ transition: "stroke 0.4s ease" }}
                  />
                  {/* live handoff beam — streams a dash-flow into the working agent */}
                  {flowing && (
                    <path
                      d={d}
                      fill="none"
                      stroke={SKY}
                      strokeWidth={3}
                      strokeLinecap="round"
                      strokeDasharray="5 11"
                      className={reduce ? "" : "animate-dash-flow"}
                      opacity={0.95}
                    />
                  )}
                  {/* travelling token — the state moving between agents */}
                  {flowing && !reduce && (
                    <circle r={5} fill={SKY}>
                      <animateMotion dur="1.15s" repeatCount="indefinite" path={d} />
                    </circle>
                  )}
                  {[start, end].map((dot, dotIndex) => (
                    <circle
                      key={dotIndex}
                      cx={dot.x}
                      cy={dot.y}
                      r={6}
                      fill="rgb(var(--color-background))"
                      stroke={color}
                      strokeWidth={2.5}
                      style={{ transition: "stroke 0.4s ease" }}
                    />
                  ))}
                </g>
              );
            })}
          </svg>

          {NODE_ORDER.map((id) => {
            const status = agents[id];
            const style = STATUS_STYLE[status];
            const rect = RECT[id];
            const selected = id === selectedAgent;
            const working = status === "active";
            const pipelineIndex = AGENT_PIPELINE.indexOf(id);
            return (
              <motion.button
                key={id}
                onClick={() => onSelectAgent(selected ? null : id)}
                className={[
                  "absolute flex flex-col items-center justify-center gap-2 overflow-hidden rounded-md border-2 p-3 text-center",
                  style.card,
                  selected ? "ring-2 ring-text" : "",
                ].join(" ")}
                style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}
                animate={{
                  boxShadow: style.glow,
                  opacity: status === "standby" ? 0.6 : 1,
                  scale: working ? 1.03 : 1,
                }}
                transition={{ duration: 0.4, ease: EASE_MECH }}
              >
                {/* pipeline stage number */}
                {pipelineIndex >= 0 && (
                  <span
                    className={`absolute left-2 top-2 font-mono text-[11px] font-semibold ${style.text}`}
                  >
                    {String(pipelineIndex + 1).padStart(2, "0")}
                  </span>
                )}

                {/* working overlays — pulsing ring + shimmer sweep */}
                {working && !reduce && (
                  <>
                    <motion.span
                      aria-hidden
                      className="pointer-events-none absolute inset-0 rounded-md border-2"
                      style={{ borderColor: style.ring }}
                      initial={{ opacity: 0.6, scale: 1 }}
                      animate={{ opacity: [0.6, 0, 0.6], scale: [1, 1.06, 1] }}
                      transition={{ duration: 1.9, ease: "easeInOut", repeat: Infinity }}
                    />
                    <motion.span
                      aria-hidden
                      className="pointer-events-none absolute inset-y-0 w-1/2"
                      style={{
                        background:
                          "linear-gradient(100deg, transparent, rgba(0,120,174,0.16), transparent)",
                      }}
                      initial={{ x: "-140%" }}
                      animate={{ x: "260%" }}
                      transition={{ duration: 1.8, ease: "easeInOut", repeat: Infinity }}
                    />
                  </>
                )}

                {id === "matching" && responder ? (
                  <span className="flex w-full flex-col items-center gap-2">
                    <span className="flex h-9 w-9 items-center justify-center rounded bg-[#0078AE] text-white">
                      <UserCheck className="h-5 w-5" />
                    </span>
                    <span className="text-body-sm font-semibold leading-tight text-text">{responder.name}</span>
                    <span className="font-mono text-[9px] uppercase tracking-wide text-[#0078AE]">
                      one technician selected
                    </span>
                    <span className="flex w-full flex-col gap-1 text-left font-mono text-[9px] leading-tight">
                      <span className="inline-flex items-center gap-1 text-textSecondary">
                        <ShieldCheck className="h-3 w-3 text-[#0078AE]" />
                        competence {responder.matchedSkills?.length ? "1.00" : "matched"}
                      </span>
                      <span className="inline-flex items-center gap-1 text-textSecondary">
                        <ShieldCheck className="h-3 w-3 text-[#0078AE]" />
                        seniority {responder.tier.toLowerCase()} · fit
                      </span>
                      <span className={responder.outOfZone ? "inline-flex items-center gap-1 text-warn" : "inline-flex items-center gap-1 text-resolve"}>
                        <MapPin className="h-3 w-3" />
                        {responder.outOfZone ? "out of zone" : `in zone${responder.region ? ` · ${responder.region}` : ""}`}
                      </span>
                    </span>
                  </span>
                ) : id === "validation" && awaitingMobile ? (
                  <span className="flex w-full flex-col items-center gap-2">
                    <span className="relative flex h-10 w-10 items-center justify-center rounded-full bg-ember/12 text-ember">
                      {!reduce && <span className="absolute inset-0 animate-ping rounded-full border border-ember/50" />}
                      <Smartphone className="relative h-5 w-5" />
                    </span>
                    <span className="text-body-sm font-semibold leading-tight text-text">Field validation</span>
                    <span className="inline-flex items-center gap-1 font-mono text-[10px] font-semibold uppercase tracking-wide text-ember">
                      awaiting mobile <WorkingDots />
                    </span>
                    <span className="text-[10px] leading-snug text-textSecondary">
                      {responder ? `${responder.name} must send the on-site verdict.` : "Waiting for the technician's on-site verdict."}
                    </span>
                  </span>
                ) : (
                  <>
                    <span className={`flex h-11 w-11 items-center justify-center rounded ${style.badge}`}>
                      <RobotIcon className="h-6 w-6" />
                    </span>
                    <span className="flex flex-col items-center gap-0.5">
                      <span className="text-body-sm font-medium leading-tight text-text">{AGENTS[id].name}</span>
                      {working ? (
                        <span className={`inline-flex items-center gap-1.5 font-mono text-[12px] ${style.text}`}>
                          working
                          <WorkingDots />
                        </span>
                      ) : (
                        <span className={`font-mono text-[12px] ${style.text}`}>{style.label}</span>
                      )}
                    </span>
                  </>
                )}
              </motion.button>
            );
          })}
        </div>
      </div>
    </div>

    {/* ── MOBILE (<lg): a vertical stacked pipeline — no horizontal scroll ──── */}
    <div className="flex w-full flex-col bg-background p-4 lg:hidden">
      {NODE_ORDER.map((id, index) => (
        <Fragment key={id}>
          {index > 0 && <MobileConnector status={agents[id]} reduce={reduce} />}
          <MobileAgentCard
            id={id}
            status={agents[id]}
            selected={id === selectedAgent}
            responder={responder}
            awaitingMobile={awaitingMobile}
            reduce={reduce}
            onClick={() => onSelectAgent(id === selectedAgent ? null : id)}
          />
        </Fragment>
      ))}
    </div>

    <span className="sr-only" aria-live="polite">
      {decisionLabel}. {decisionCopy}. {activity.at(-1)?.detail ?? ""}
    </span>
    </>
  );
}

// ── Mobile vertical pipeline ─────────────────────────────────────────────────
// A DOM-only stacked variant of the graph for <lg, so the whole pipeline reads
// top-to-bottom inside 390px with zero horizontal scroll. Same status semantics
// and the same rich matching / awaiting-validation content as the canvas nodes;
// each card is tappable and opens the same detail overlay.
function MobileConnector({ status, reduce }: { status: AgentStatus; reduce: boolean | null }) {
  const color = status === "active" ? SKY : status === "done" ? "rgb(62 207 142)" : IDLE_LINK;
  return (
    <div className="flex h-4 items-stretch justify-center" aria-hidden>
      <span
        className={`w-[2.5px] rounded-full ${status === "active" && !reduce ? "animate-signal-pulse" : ""}`}
        style={{ background: color }}
      />
    </div>
  );
}

function MobileAgentCard({
  id,
  status,
  selected,
  responder,
  awaitingMobile,
  reduce,
  onClick,
}: {
  id: AgentId;
  status: AgentStatus;
  selected: boolean;
  responder: ChosenResponder | null;
  awaitingMobile: boolean;
  reduce: boolean | null;
  onClick: () => void;
}) {
  const style = STATUS_STYLE[status];
  const working = status === "active";
  const pipelineIndex = AGENT_PIPELINE.indexOf(id);

  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "relative w-full overflow-hidden rounded-lg border-2 p-3 text-left transition-[border-color,background-color] duration-300",
        style.card,
        selected ? "ring-2 ring-text" : "",
      ].join(" ")}
      style={{ boxShadow: working ? style.glow : undefined, opacity: status === "standby" ? 0.65 : 1 }}
    >
      {pipelineIndex >= 0 && (
        <span className={`absolute right-3 top-3 font-mono text-[11px] font-semibold ${style.text}`}>
          {String(pipelineIndex + 1).padStart(2, "0")}
        </span>
      )}
      {working && !reduce && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-lg border-2 animate-signal-pulse"
          style={{ borderColor: style.ring }}
        />
      )}

      {id === "matching" && responder ? (
        <div className="flex flex-col gap-2.5">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-[#0078AE] text-white">
              <UserCheck className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <p className="text-body-sm font-semibold leading-tight text-text">{responder.name}</p>
              <p className="font-mono text-[9px] uppercase tracking-wide text-[#0078AE]">one technician selected</p>
            </div>
          </div>
          <div className="flex flex-col gap-1 font-mono text-[10px] leading-tight">
            <span className="inline-flex items-center gap-1 text-textSecondary">
              <ShieldCheck className="h-3 w-3 text-[#0078AE]" />
              competence {responder.matchedSkills?.length ? "1.00" : "matched"}
            </span>
            <span className="inline-flex items-center gap-1 text-textSecondary">
              <ShieldCheck className="h-3 w-3 text-[#0078AE]" />
              seniority {responder.tier.toLowerCase()} · fit
            </span>
            <span
              className={
                responder.outOfZone
                  ? "inline-flex items-center gap-1 text-warn"
                  : "inline-flex items-center gap-1 text-resolve"
              }
            >
              <MapPin className="h-3 w-3" />
              {responder.outOfZone ? "out of zone" : `in zone${responder.region ? ` · ${responder.region}` : ""}`}
            </span>
          </div>
        </div>
      ) : id === "validation" && awaitingMobile ? (
        <div className="flex items-center gap-3">
          <span className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ember/12 text-ember">
            {!reduce && <span className="absolute inset-0 animate-ping rounded-full border border-ember/50" />}
            <Smartphone className="relative h-5 w-5" />
          </span>
          <div className="min-w-0">
            <p className="text-body-sm font-semibold leading-tight text-text">Field validation</p>
            <p className="inline-flex items-center gap-1 font-mono text-[10px] font-semibold uppercase tracking-wide text-ember">
              awaiting mobile <WorkingDots />
            </p>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-3">
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded ${style.badge}`}>
            <RobotIcon className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
              <p className="text-body-sm font-medium leading-tight text-text">{AGENTS[id].name}</p>
              {id === "orchestrator" && (
                <span className="rounded bg-arc/10 px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-wide text-arc">
                  arc orchestrator · vultr
                </span>
              )}
            </div>
            {working ? (
              <span className={`inline-flex items-center gap-1.5 font-mono text-[11px] ${style.text}`}>
                working <WorkingDots />
              </span>
            ) : (
              <span className={`font-mono text-[11px] ${style.text}`}>{style.label}</span>
            )}
          </div>
        </div>
      )}
    </button>
  );
}
