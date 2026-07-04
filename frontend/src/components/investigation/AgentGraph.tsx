"use client";

import { useEffect, useRef, useState } from "react";
import { RobotIcon } from "@/components/icons";
import { AGENTS, type AgentId, type AgentStatus } from "@/lib/investigation";

// Agent Orchestration viewport — Figma node 133:589 (graph canvas 133:797,
// decision column 133:901). Ten nodes at design coordinates (1216x655.56,
// node 167.1). Wiring follows the real orchestrator semantics rather than
// the mock: every sub-agent hangs off the Main Agent — phase-1 pair on the
// right, domain watchers below, and the human-loop / phase-2 trio down the
// left-hand pipeline lane.
const CANVAS = { width: 1216, height: 656 };
const NODE = 167;

const NODE_POS: Record<AgentId, { x: number; y: number }> = {
  main: { x: 751, y: 0 },
  security: { x: 681, y: 246 },
  fire: { x: 483, y: 246 },
  hvac: { x: 285, y: 246 },
  correlation: { x: 1049, y: 78 },
  rootCause: { x: 1049, y: 292 },
  validation: { x: 0, y: 488 },
  remediation: { x: 202, y: 488 },
  dispatch: { x: 404, y: 488 },
};

const STATUS_STYLE: Record<
  AgentStatus,
  { card: string; badge: string; label: string; text: string; glow: string }
> = {
  monitoring: {
    card: "border-accent bg-accentSubtle",
    badge: "bg-accent text-background",
    label: "monitoring",
    text: "text-accentBright",
    glow: "shadow-glow",
  },
  active: {
    card: "border-warning bg-warningDeep",
    badge: "bg-warning text-background",
    label: "active",
    text: "text-warningBright",
    glow: "shadow-glowWarning",
  },
  standby: {
    card: "border-border bg-panelMuted",
    badge: "bg-muted text-background",
    label: "standby",
    text: "text-muted",
    glow: "",
  },
  done: {
    card: "border-secondary bg-panelMuted",
    badge: "bg-secondary text-background",
    label: "done",
    text: "text-secondary",
    glow: "",
  },
};

type Point = { x: number; y: number };

function roundedOrthogonalPath(points: Point[], radius = 10): string {
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

function center(id: AgentId): Point {
  return { x: NODE_POS[id].x + NODE / 2, y: NODE_POS[id].y + NODE / 2 };
}

const MAIN_CX = center("main").x;
const MAIN_CY = center("main").y;
const MAIN_LEFT = NODE_POS.main.x;
const MAIN_RIGHT = NODE_POS.main.x + NODE;
const MAIN_BOTTOM = NODE_POS.main.y + NODE;

// All links originate at the Main Agent (the orchestrator sequences every
// sub-agent). Right edge → phase-1 pair; bottom ports → domain watchers;
// left edge → the human-loop / phase-2 trio, routed down the empty lane left
// of the watcher row so nothing crosses a node.
const LINK_WAYPOINTS: Record<Exclude<AgentId, "main">, Point[]> = {
  correlation: [
    { x: MAIN_RIGHT, y: MAIN_CY - 20 },
    { x: MAIN_RIGHT + 48, y: MAIN_CY - 20 },
    { x: MAIN_RIGHT + 48, y: center("correlation").y },
    { x: NODE_POS.correlation.x, y: center("correlation").y },
  ],
  rootCause: [
    { x: MAIN_RIGHT, y: MAIN_CY + 14 },
    { x: MAIN_RIGHT + 26, y: MAIN_CY + 14 },
    { x: MAIN_RIGHT + 26, y: center("rootCause").y },
    { x: NODE_POS.rootCause.x, y: center("rootCause").y },
  ],
  security: [
    { x: MAIN_CX + 26, y: MAIN_BOTTOM },
    { x: MAIN_CX + 26, y: MAIN_BOTTOM + 44 },
    { x: center("security").x, y: MAIN_BOTTOM + 44 },
    { x: center("security").x, y: NODE_POS.security.y },
  ],
  fire: [
    { x: MAIN_CX, y: MAIN_BOTTOM },
    { x: MAIN_CX, y: MAIN_BOTTOM + 33 },
    { x: center("fire").x, y: MAIN_BOTTOM + 33 },
    { x: center("fire").x, y: NODE_POS.fire.y },
  ],
  hvac: [
    { x: MAIN_CX - 26, y: MAIN_BOTTOM },
    { x: MAIN_CX - 26, y: MAIN_BOTTOM + 22 },
    { x: center("hvac").x, y: MAIN_BOTTOM + 22 },
    { x: center("hvac").x, y: NODE_POS.hvac.y },
  ],
  validation: [
    { x: MAIN_LEFT, y: MAIN_CY - 22 },
    { x: center("validation").x, y: MAIN_CY - 22 },
    { x: center("validation").x, y: NODE_POS.validation.y },
  ],
  remediation: [
    { x: MAIN_LEFT, y: MAIN_CY },
    { x: 232, y: MAIN_CY },
    { x: 232, y: 458 },
    { x: center("remediation").x, y: 458 },
    { x: center("remediation").x, y: NODE_POS.remediation.y },
  ],
  dispatch: [
    { x: MAIN_LEFT, y: MAIN_CY + 22 },
    { x: 246, y: MAIN_CY + 22 },
    { x: 246, y: 472 },
    { x: center("dispatch").x, y: 472 },
    { x: center("dispatch").x, y: NODE_POS.dispatch.y },
  ],
};

const LINKED_AGENTS = Object.keys(LINK_WAYPOINTS) as Array<keyof typeof LINK_WAYPOINTS>;

const LINK_COLORS = {
  active: "rgb(var(--color-warning))",
  done: "rgb(var(--color-secondary))",
  idle: "rgb(var(--color-border-strong))",
  dotFill: "rgb(var(--color-background))",
};

function linkColor(status: AgentStatus): string {
  if (status === "active") return LINK_COLORS.active;
  if (status === "done") return LINK_COLORS.done;
  return LINK_COLORS.idle;
}

export function AgentGraph({
  agents,
  decisionLabel,
  decisionCopy,
  selectedAgent,
  onSelectAgent,
}: {
  agents: Record<AgentId, AgentStatus>;
  decisionLabel: string;
  decisionCopy: string;
  selectedAgent: AgentId | null;
  onSelectAgent: (id: AgentId | null) => void;
}) {
  const selectedInfo = selectedAgent ? AGENTS[selectedAgent] : null;

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
    <div className="flex h-full min-h-0 w-full gap-4 rounded-xl border border-borderSubtle bg-background p-4">
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
          <svg
            className="pointer-events-none absolute inset-0"
            viewBox={`0 0 ${CANVAS.width} ${CANVAS.height}`}
            width={CANVAS.width}
            height={CANVAS.height}
          >
            {LINKED_AGENTS.map((id) => {
              const color = linkColor(agents[id]);
              const waypoints = LINK_WAYPOINTS[id];
              const start = waypoints[0];
              const end = waypoints[waypoints.length - 1];
              return (
                <g key={id}>
                  <path d={roundedOrthogonalPath(waypoints)} fill="none" stroke={color} strokeWidth={2.5} />
                  {[start, end].map((dot, index) => (
                    <circle
                      key={index}
                      cx={dot.x}
                      cy={dot.y}
                      r={6.5}
                      fill={LINK_COLORS.dotFill}
                      stroke={color}
                      strokeWidth={2.5}
                    />
                  ))}
                </g>
              );
            })}
          </svg>

          {(Object.keys(NODE_POS) as AgentId[]).map((id) => {
            const style = STATUS_STYLE[agents[id]];
            const selected = id === selectedAgent;
            return (
              <button
                key={id}
                onClick={() => onSelectAgent(selected ? null : id)}
                className={[
                  "absolute flex flex-col items-center justify-center gap-2.5 rounded-md border-2 p-4 transition-all",
                  style.card,
                  style.glow,
                  selected ? "ring-2 ring-text" : "",
                ].join(" ")}
                style={{ left: NODE_POS[id].x, top: NODE_POS[id].y, width: NODE, height: NODE }}
              >
                <span className={`flex h-12 w-12 items-center justify-center rounded ${style.badge}`}>
                  <RobotIcon className="h-7 w-7" />
                </span>
                <span className="flex flex-col items-center gap-1">
                  <span className="text-body font-medium text-text">{AGENTS[id].name}</span>
                  <span className={`text-body-sm ${style.text}`}>{style.label}</span>
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex w-[266px] shrink-0 flex-col gap-4">
        <div
          key={decisionCopy}
          className="arc-fade-up flex flex-col gap-2.5 rounded-md border border-accent bg-raised p-4 shadow-glow"
        >
          <p className="text-body font-semibold text-accentBright">{decisionLabel}</p>
          <p className="text-body-sm text-textSecondary">{decisionCopy}</p>
        </div>
        {selectedInfo ? (
          <div key={selectedInfo.id} className="arc-fade-up flex flex-1 flex-col gap-2 rounded-md bg-borderSubtle p-4">
            <p className="text-body-sm font-medium text-text">
              {selectedInfo.name} ·{" "}
              <span className={STATUS_STYLE[agents[selectedInfo.id]].text}>
                {STATUS_STYLE[agents[selectedInfo.id]].label}
              </span>
            </p>
            <p className="text-body-sm text-textSecondary">{selectedInfo.role}</p>
          </div>
        ) : (
          <div className="flex flex-1 rounded-md bg-borderSubtle p-4">
            <p className="text-body-sm text-textSecondary">
              Standby agents are visible but not running. The graph lights up only when a real task is delegated.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
