"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  AGENTS,
  type ActivityEntry,
  type ActivityKind,
  type AgentId,
  type AgentStatus,
} from "@/lib/investigation";

// AgentTerminal — a terminal-STYLED live console for a single agent. There is
// no per-agent shell server; this replays the REAL SSE activity already in
// state (`ActivityEntry[]`, filtered to this node) as if we were watching the
// agent's stdout: a boot prompt, tool-call lines coloured by kind, output
// blocks, the newest line typing in under a blinking block cursor. Standby
// agents show an "awaiting orchestration…" waiting state. Reduced-motion safe:
// typing + blink collapse to the final frame.

// Terminal palette — legible on the dark surface, mapped to the brand tokens.
const TERM = {
  dim: "text-white/35",
  comment: "text-white/30",
  sky: "text-[#3ea9db]", // ember.dim — working / info
  tool: "text-[#6fb2ff]", // arc — tool-calls
  ok: "text-[#4fdca0]", // resolve — output / done
  warn: "text-[#7dd3fc]", // warn — human loop
  err: "text-[#f2999d]", // danger.dim — pivot / degraded
} as const;

const KIND: Record<ActivityKind, { cls: string; tag: string }> = {
  detect: { cls: TERM.sky, tag: "watch" },
  route: { cls: TERM.sky, tag: "route" },
  agent: { cls: TERM.sky, tag: "exec" },
  retrieval: { cls: TERM.tool, tag: "retrieve" },
  diagnosis: { cls: TERM.tool, tag: "diagnose" },
  match: { cls: TERM.tool, tag: "match" },
  handoff: { cls: TERM.sky, tag: "notify" },
  validation: { cls: TERM.warn, tag: "verify" },
  pivot: { cls: TERM.err, tag: "pivot" },
  remediation: { cls: TERM.tool, tag: "repair" },
  report: { cls: TERM.ok, tag: "report" },
  resolve: { cls: TERM.ok, tag: "done" },
  degraded: { cls: TERM.err, tag: "warn" },
};

type TermLine =
  | { id: string; role: "meta" | "comment" | "output"; text: string }
  | { id: string; role: "cmd"; cls: string; tag: string; text: string; ts: string };

function buildLines(agent: AgentId, entries: ActivityEntry[]): TermLine[] {
  const info = AGENTS[agent];
  const lines: TermLine[] = [
    { id: "head", role: "meta", text: `arc@orchestrator:~$ attach --agent ${info.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}` },
    { id: "role", role: "comment", text: `// ${info.role}` },
  ];
  for (const e of entries) {
    const k = KIND[e.kind];
    lines.push({ id: `${e.id}-c`, role: "cmd", cls: k.cls, tag: k.tag, text: e.label, ts: e.timestamp });
    // Rich reasoning breakdown (ranked causes, retrieval hits, procedure steps,
    // contradictions) streams as indented sub-lines; fall back to the one-line
    // detail when the event carried no structured reasoning.
    if (e.lines && e.lines.length) {
      e.lines.forEach((ln, i) => lines.push({ id: `${e.id}-l${i}`, role: "output", text: ln }));
    } else if (e.detail) {
      lines.push({ id: `${e.id}-o`, role: "output", text: e.detail });
    }
  }
  return lines;
}

// Per-glyph accent for reasoning sub-lines — selected (⇒) reads resolve-green,
// rejected/contradiction (✗) danger, safety (⚠) warn, retrieval (↳) arc-dim.
function outputClass(text: string): string {
  const t = text.trimStart();
  if (t.startsWith("⇒")) return "pl-[3.4em] text-[#4fdca0]";
  if (t.startsWith("✗")) return "pl-[3.4em] text-[#f2999d]";
  if (t.startsWith("⚠")) return "pl-[3.4em] text-[#7dd3fc]";
  if (t.startsWith("↳")) return "pl-[3.4em] text-white/45";
  return "pl-[3.4em] text-white/60";
}

// Typewriter for the newest line only — re-runs whenever the last line id
// changes. Reduced-motion returns the full text immediately.
function useTypewriter(text: string, key: string, reduce: boolean, speed = 14) {
  const [count, setCount] = useState(reduce ? text.length : 0);
  useEffect(() => {
    if (reduce) {
      setCount(text.length);
      return;
    }
    setCount(0);
    let raf = 0;
    let start: number | null = null;
    const tick = (t: number) => {
      if (start === null) start = t;
      const chars = Math.floor((t - start) / speed);
      setCount(Math.min(chars, text.length));
      if (chars < text.length) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [key, text, reduce, speed]);
  return text.slice(0, count);
}

function Cursor({ reduce }: { reduce: boolean }) {
  return (
    <motion.span
      aria-hidden
      className="ml-0.5 inline-block h-[1.05em] w-[0.55em] translate-y-[0.15em] bg-[#6fb2ff]"
      animate={reduce ? { opacity: 1 } : { opacity: [1, 1, 0, 0] }}
      transition={reduce ? undefined : { duration: 1.05, ease: "linear", repeat: Infinity, times: [0, 0.5, 0.5, 1] }}
    />
  );
}

const STATUS_DOT: Record<AgentStatus, { cls: string; label: string }> = {
  monitoring: { cls: "bg-[#6fb2ff]", label: "monitoring" },
  active: { cls: "bg-[#3ea9db]", label: "working" },
  standby: { cls: "bg-white/25", label: "standby" },
  done: { cls: "bg-[#4fdca0]", label: "done" },
};

export function AgentTerminal({
  agent,
  status,
  activity,
}: {
  agent: AgentId;
  status: AgentStatus;
  activity: ActivityEntry[];
}) {
  const reduce = !!useReducedMotion();
  const info = AGENTS[agent];

  const entries = useMemo(() => activity.filter((e) => e.agent === agent), [activity, agent]);
  const lines = useMemo(() => buildLines(agent, entries), [agent, entries]);

  const last = lines[lines.length - 1];
  const typed = useTypewriter(last.text, last.id, reduce);

  // Auto-scroll to the freshest line as it streams in.
  const bodyRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines.length, typed]);

  const working = status === "active";
  const dot = STATUS_DOT[status];
  const waiting = entries.length === 0;

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-lg border border-surface-line bg-surface shadow-[0_20px_60px_-24px_rgba(0,0,0,0.8)]">
      {/* chrome bar */}
      <div className="flex shrink-0 items-center gap-3 border-b border-surface-line bg-surface-raised px-3.5 py-2.5">
        <span className="flex items-center gap-1.5" aria-hidden>
          <span className="h-2.5 w-2.5 rounded-full bg-[#f2999d]/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#7dd3fc]/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#4fdca0]/70" />
        </span>
        <span className="font-mono text-[11px] text-white/45">
          agent://{info.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}
        </span>
        <span className="ml-auto inline-flex items-center gap-1.5">
          <span
            className={[
              "h-1.5 w-1.5 rounded-full",
              dot.cls,
              working && !reduce ? "animate-signal-pulse" : "",
            ].join(" ")}
          />
          <span className="font-mono text-[10px] uppercase tracking-wide text-white/45">{dot.label}</span>
        </span>
      </div>

      {/* body */}
      <div
        ref={bodyRef}
        className="scroll-slim relative min-h-0 flex-1 overflow-y-auto px-4 py-3.5 font-mono text-[12.5px] leading-relaxed"
      >
        {/* scanline + grid texture */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.5]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(111,178,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(111,178,255,0.03) 1px, transparent 1px)",
            backgroundSize: "100% 3px, 34px 100%",
          }}
        />

        <div className="relative flex flex-col gap-0.5">
          {lines.map((line, i) => {
            const isLast = i === lines.length - 1;
            const shown = isLast ? typed : line.text;
            // While the agent is working, the block cursor lives on the
            // reasoning row below; when idle/done it caps the last output line.
            const cursorHere = isLast && !working;
            if (line.role === "cmd") {
              return (
                <motion.p
                  key={line.id}
                  initial={reduce ? false : { opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.25 }}
                  className="flex items-baseline gap-2"
                >
                  <span className="shrink-0 text-white/25">$</span>
                  <span className={`shrink-0 ${line.cls}`}>{line.tag}</span>
                  <span className="text-white/85">
                    {shown}
                    {cursorHere && <Cursor reduce={reduce} />}
                  </span>
                  <span className="ml-auto shrink-0 pl-3 text-[10px] text-white/25">{line.ts}</span>
                </motion.p>
              );
            }
            const cls =
              line.role === "meta"
                ? "text-white/45"
                : line.role === "comment"
                  ? `${TERM.comment} italic`
                  : outputClass(line.text);
            return (
              <motion.p
                key={line.id}
                initial={reduce || line.role !== "output" ? false : { opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25 }}
                className={cls}
              >
                {shown}
                {cursorHere && <Cursor reduce={reduce} />}
              </motion.p>
            );
          })}

          {/* live "thinking" row — the agent is still reasoning, more streams in */}
          {working && !waiting && (
            <p className="mt-1 flex items-center gap-2 text-[#3ea9db]">
              <span className="text-white/25">$</span>
              <span>reasoning</span>
              <span className="inline-flex gap-0.5" aria-hidden>
                {[0, 1, 2].map((d) => (
                  <motion.span
                    key={d}
                    className="inline-block"
                    animate={reduce ? undefined : { opacity: [0.2, 1, 0.2] }}
                    transition={{ duration: 1.1, repeat: Infinity, delay: d * 0.18 }}
                  >
                    .
                  </motion.span>
                ))}
              </span>
              <Cursor reduce={reduce} />
            </p>
          )}

          {waiting && (
            <div className="mt-3 flex items-center gap-2 text-white/40">
              <span className="h-1.5 w-1.5 rounded-full bg-[#3ea9db] animate-signal-pulse" />
              <span>awaiting orchestration</span>
              <span className="inline-flex gap-0.5">
                {[0, 1, 2].map((d) => (
                  <motion.span
                    key={d}
                    className="inline-block"
                    animate={reduce ? undefined : { opacity: [0.2, 1, 0.2] }}
                    transition={{ duration: 1.1, repeat: Infinity, delay: d * 0.18 }}
                  >
                    .
                  </motion.span>
                ))}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
