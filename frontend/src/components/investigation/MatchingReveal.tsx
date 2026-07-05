"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Ban, Check, MapPin, ShieldCheck, Smartphone } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { EASE_MECH } from "@/motion/tokens";
import type { ChosenResponder, MatchingCard, MatchingSnapshot } from "@/lib/investigation";

// MatchingReveal — the live employee-selection viz, as a roster of profile
// FICHES. Drives off the REAL `responder_matched` slate (`state.matching`): every
// on-call technician mounts as a little profile card (avatar, name, role, zone,
// skills, score ring); then the non-chosen ones are flagged (✕ reason) and
// collapse out one by one until only the chosen tech remains — growing into a
// highlighted "paged" card with a sky-blue ring, glow and the push line. Falls
// back to a single card synthesized from `state.responder` if the narrowing
// event hasn't arrived. Reduced-motion jumps to the end state.

const BLUE = "#0078AE";

function tierFor(difficulty: string): string {
  if (difficulty === "complex") return "senior";
  if (difficulty === "simple") return "junior";
  return "best-fit";
}

// Why an alternative lost — prefers the backend `reason`, else derives it from
// the same axes the matcher scores on (zone, seniority-fit, competence gate).
function elimReason(card: MatchingCard, chosen: MatchingCard, difficulty: string): string {
  if (card.reason) return card.reason;
  if (card.outOfZone) return "out-of-zone";
  if (difficulty === "complex" && /junior/i.test(card.tier)) return "junior · complex fault";
  if (!card.matchedSkills.length) return "wrong family · gated";
  if (card.score < chosen.score) return "lower score";
  return "not retained";
}

// Elimination order — weakest alternatives first, closest contender last, so
// the roster visibly narrows from clearly-wrong picks down to THE ONE. Out-of-
// zone is penalised hard (an in-zone tech is preferred), then raw score.
function eliminationOrder(snap: MatchingSnapshot): string[] {
  const chosenId = snap.chosen.employeeId;
  const keep = (c: MatchingCard) => c.score - (c.outOfZone ? 0.5 : 0);
  return snap.candidates
    .filter((c) => c.employeeId !== chosenId)
    .slice()
    .sort((a, b) => keep(a) - keep(b))
    .map((c) => c.employeeId);
}

function synthFromResponder(r: ChosenResponder): MatchingSnapshot {
  const chosen: MatchingCard = {
    employeeId: r.employeeId,
    name: r.name,
    tier: r.tier,
    region: r.region ?? "",
    matchedSkills: r.matchedSkills ?? [],
    score: r.score ?? 1,
    reason: r.reason,
    outOfZone: r.outOfZone,
  };
  return {
    fault: { family: "", equipmentClass: "", code: "", region: r.region ?? "" },
    difficulty: r.difficulty ?? "",
    chosen,
    candidates: [chosen],
  };
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

// Compact circular score gauge — the "profile stat" of each fiche.
function ScoreRing({ value, off, lit }: { value: number; off: boolean; lit: boolean }) {
  const pct = Math.max(0, Math.min(1, value));
  const r = 15;
  const circ = 2 * Math.PI * r;
  const color = lit ? BLUE : off ? "#4a4654" : "#6fb2ff";
  return (
    <div className="relative grid h-12 w-12 shrink-0 place-items-center">
      <svg viewBox="0 0 40 40" className="h-12 w-12 -rotate-90" aria-hidden>
        <circle cx="20" cy="20" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="3.5" />
        <motion.circle
          cx="20"
          cy="20"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeDasharray={circ}
          animate={{ strokeDashoffset: off ? circ : circ * (1 - pct) }}
          transition={{ duration: 0.5, ease: EASE_MECH }}
        />
      </svg>
      <span className="absolute font-mono text-[11px] font-semibold tabular-nums text-white/85">
        {value.toFixed(2)}
      </span>
    </div>
  );
}

function Chip({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "sky" | "zone" | "off" | "danger" }) {
  const cls =
    tone === "sky"
      ? "border-[#0078AE]/50 bg-[#0078AE]/15 text-[#6fb2ff]"
      : tone === "zone"
        ? "border-[#4fdca0]/40 bg-[#4fdca0]/10 text-[#4fdca0]"
        : tone === "danger"
          ? "border-[#f2999d]/40 bg-[#f2999d]/10 text-[#f2999d]"
          : tone === "off"
            ? "border-white/10 bg-white/5 text-white/40"
            : "border-white/12 bg-white/5 text-white/60";
  return (
    <span className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[9.5px] font-semibold uppercase tracking-wide ${cls}`}>
      {children}
    </span>
  );
}

export function MatchingReveal({
  matching,
  responder,
}: {
  matching: MatchingSnapshot | null;
  responder: ChosenResponder | null;
}) {
  const reduce = useReducedMotion();
  const snap = useMemo<MatchingSnapshot | null>(
    () => matching ?? (responder ? synthFromResponder(responder) : null),
    [matching, responder],
  );

  const total = snap?.candidates.length ?? 0;
  const allIds = useMemo(() => snap?.candidates.map((c) => c.employeeId) ?? [], [snap]);
  const key = snap ? `${snap.chosen.employeeId}:${total}` : "none";

  // Progressive-elimination state machine. All fiches mount lit and equal; then,
  // one at a time (~900ms apart), a non-chosen card is FLAGGED (its reason
  // flashes, it desaturates) for a beat, then REMOVED from `remainingIds` so
  // AnimatePresence collapses it out of the grid. Weakest first, chosen last.
  // Reduced-motion jumps straight to the end state (only the chosen remains).
  const [remainingIds, setRemainingIds] = useState<string[]>(allIds);
  const [flaggedId, setFlaggedId] = useState<string | null>(null);
  useEffect(() => {
    if (!snap) return;
    const chosenId = snap.chosen.employeeId;
    if (reduce) {
      setRemainingIds([chosenId]);
      setFlaggedId(null);
      return;
    }
    setRemainingIds(snap.candidates.map((c) => c.employeeId));
    setFlaggedId(null);
    const order = eliminationOrder(snap);
    const timers: number[] = [];
    let t = 1400; // "all technicians on call" opening beat — roster reads before narrowing
    for (const id of order) {
      timers.push(window.setTimeout(() => setFlaggedId(id), t)); // flash the reason
      timers.push(
        window.setTimeout(() => {
          setFlaggedId((cur) => (cur === id ? null : cur));
          setRemainingIds((cur) => cur.filter((x) => x !== id)); // collapse it out
        }, t + 750),
      );
      t += 1150;
    }
    return () => timers.forEach((x) => window.clearTimeout(x));
  }, [key, reduce, snap]);

  if (!snap) {
    return (
      <div className="flex h-full min-h-0 items-center justify-center rounded-lg border border-surface-line bg-surface p-8 text-center">
        <div className="flex flex-col items-center gap-2 text-white/45">
          <span className="h-2 w-2 rounded-full bg-[#3ea9db] animate-signal-pulse" />
          <p className="font-mono text-[12px] uppercase tracking-label">awaiting matching…</p>
          <p className="max-w-xs text-body-sm text-white/35">
            The matching agent will score the roster and narrow to THE ONE technician once the diagnosis is ready.
          </p>
        </div>
      </div>
    );
  }

  const { fault, difficulty, chosen, candidates } = snap;
  const chosenId = chosen.employeeId;
  const remainingSet = new Set(remainingIds);
  const visible = candidates.filter((c) => remainingSet.has(c.employeeId));
  const chosenLit = remainingIds.length <= 1;
  const sig = [
    fault.family && { k: "family", v: fault.family },
    fault.equipmentClass && { k: "equipment", v: fault.equipmentClass },
    fault.code && { k: "code", v: fault.code },
    (fault.region || chosen.region) && { k: "region", v: fault.region || chosen.region },
  ].filter(Boolean) as { k: string; v: string }[];

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-hidden">
      {/* fault signature header */}
      <motion.header
        initial={reduce ? false : { opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: EASE_MECH }}
        className="shrink-0 rounded-lg border border-surface-line bg-surface-raised px-4 py-3"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-label text-white/40">fault signature</span>
            {sig.map((s) => (
              <span key={s.k} className="inline-flex items-baseline gap-1 font-mono text-[11px]">
                <span className="text-white/35">{s.k}</span>
                <span className="text-white/85">{s.v}</span>
              </span>
            ))}
          </div>
          {difficulty && (
            <span
              className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.1em]"
              style={{ background: `${BLUE}22`, border: `1px solid ${BLUE}55`, color: "#6fb2ff" }}
            >
              <span className="h-1.5 w-1.5 rounded-full animate-signal-pulse" style={{ background: "#6fb2ff" }} />
              difficulty {difficulty} → {tierFor(difficulty)}
            </span>
          )}
        </div>
      </motion.header>

      {/* narrowing counter */}
      <div className="flex shrink-0 items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-label text-white/40">
          {chosenLit ? "the one responder" : `${total} technicians on call`}
        </span>
        <span className="inline-flex items-center gap-1.5 font-mono text-[10px]" style={{ color: "#6fb2ff" }}>
          {!chosenLit && <span className="h-1.5 w-1.5 rounded-full animate-signal-pulse" style={{ background: "#6fb2ff" }} />}
          <span className="tabular-nums">
            narrowing {remainingIds.length} → {chosenLit ? "" : "…→ "}1
          </span>
        </span>
      </div>

      {/* roster of profile fiches — collapses one by one to THE ONE */}
      <div className="scroll-slim min-h-0 flex-1 overflow-y-auto pr-1">
        <div className="grid auto-rows-min grid-cols-1 gap-3 sm:grid-cols-2">
          <AnimatePresence initial={false}>
            {visible.map((card) => {
              const isChosen = card.employeeId === chosenId;
              const flagged = card.employeeId === flaggedId;
              const lit = isChosen && chosenLit;
              return (
                <motion.div
                  key={card.employeeId}
                  layout={!reduce}
                  initial={reduce ? false : { opacity: 0, y: 14, scale: 0.96 }}
                  animate={{
                    opacity: flagged ? 0.55 : 1,
                    y: 0,
                    scale: 1,
                    filter: flagged ? "grayscale(0.9)" : "grayscale(0)",
                  }}
                  exit={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.9, y: -6 }}
                  transition={{ duration: 0.4, ease: EASE_MECH }}
                  className={`relative overflow-hidden rounded-xl border p-4 ${lit ? "sm:col-span-2" : ""}`}
                  style={{
                    borderColor: lit ? BLUE : flagged ? "rgba(242,153,157,0.5)" : "#2A2730",
                    background: lit
                      ? `linear-gradient(135deg, ${BLUE}1f, #161318 60%)`
                      : "linear-gradient(135deg, #1b1820, #141118)",
                    boxShadow: lit ? `0 0 40px -8px ${BLUE}, inset 0 0 0 1px ${BLUE}55` : "none",
                  }}
                >
                  {/* top accent strip */}
                  <span
                    className="pointer-events-none absolute inset-x-0 top-0 h-[3px]"
                    style={{ background: lit ? BLUE : flagged ? "rgba(242,153,157,0.6)" : "rgba(255,255,255,0.06)" }}
                  />

                  {/* identity row: avatar · name/id/tier · score ring */}
                  <div className="flex items-start gap-3">
                    <span className="relative shrink-0">
                      <span
                        className="grid h-12 w-12 place-items-center rounded-full font-mono text-base font-bold text-white ring-1 ring-white/10"
                        style={{ background: lit ? BLUE : "linear-gradient(140deg, #2f2b38, #211d28)" }}
                      >
                        {initials(card.name)}
                      </span>
                      <span
                        className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-[#161318]"
                        style={{ background: lit ? "#4fdca0" : flagged ? "#f2999d" : "#6fb2ff" }}
                      />
                    </span>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <span className="truncate text-body-sm font-semibold text-white">{card.name}</span>
                        {lit && (
                          <motion.span
                            initial={reduce ? false : { opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.3, ease: EASE_MECH }}
                            className="inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.08em] text-white"
                            style={{ background: BLUE }}
                          >
                            <Check className="h-2.5 w-2.5" /> chosen → paged
                          </motion.span>
                        )}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5">
                        <span className="font-mono text-[10px] text-white/40">{card.employeeId}</span>
                        <Chip tone={flagged ? "off" : "sky"}>
                          <ShieldCheck className="h-3 w-3" />
                          {card.tier}
                        </Chip>
                        <span
                          className="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[9.5px] font-semibold uppercase tracking-wide"
                          style={
                            card.outOfZone
                              ? { color: "#f2999d", background: "rgba(242,153,157,0.1)", borderColor: "rgba(242,153,157,0.35)" }
                              : { color: "#4fdca0", background: "rgba(79,220,160,0.1)", borderColor: "rgba(79,220,160,0.35)" }
                          }
                        >
                          <MapPin className="h-2.5 w-2.5" /> {card.region || "—"}
                        </span>
                      </div>
                    </div>

                    <ScoreRing value={card.score} off={flagged} lit={lit} />
                  </div>

                  {/* skills */}
                  {card.matchedSkills.length > 0 && (
                    <div className="mt-3 flex flex-wrap items-center gap-1.5">
                      <span className="font-mono text-[9px] uppercase tracking-[0.12em] text-white/30">skills</span>
                      {card.matchedSkills.map((s) => (
                        <Chip key={s} tone={flagged ? "off" : "neutral"}>
                          {s}
                        </Chip>
                      ))}
                      {!card.outOfZone && !flagged && <Chip tone="zone">in-zone</Chip>}
                    </div>
                  )}

                  {/* elimination reason — flashes as the card is being removed */}
                  {flagged && (
                    <motion.div
                      initial={reduce ? false : { opacity: 0, x: -4 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.25 }}
                      className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-[#f2999d]/30 bg-[#f2999d]/10 px-2 py-1 font-mono text-[10.5px] text-[#f2999d]"
                    >
                      <Ban className="h-3 w-3" />
                      <span>✕ {elimReason(card, chosen, difficulty)}</span>
                    </motion.div>
                  )}

                  {/* chosen → push line */}
                  {lit && (
                    <motion.div
                      initial={reduce ? false : { opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.35, ease: EASE_MECH }}
                      className="mt-3 flex flex-wrap items-center gap-2.5"
                    >
                      <svg viewBox="0 0 60 16" width="56" height="16" className="shrink-0" aria-hidden>
                        <path d="M 2,8 L 50,8" fill="none" stroke={BLUE} strokeWidth={1.5} strokeDasharray="3 6" strokeLinecap="round" className={reduce ? "" : "animate-dash-flow"} />
                        <path d="M 46,3 L 54,8 L 46,13" fill="none" stroke={BLUE} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      <span className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 font-mono text-[10.5px] text-white" style={{ background: BLUE }}>
                        <Smartphone className="h-3 w-3" /> 1 push · phone (iOS)
                      </span>
                      <span className="font-mono text-[10.5px] text-white/40 line-through decoration-white/25">
                        not a broadcast
                      </span>
                    </motion.div>
                  )}
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>

      {/* live caption */}
      <p className="shrink-0 font-mono text-[11px] text-white/45" aria-live="polite">
        {chosenLit
          ? `${chosen.name} paged — one technician, not a broadcast.`
          : flaggedId
            ? "eliminating…"
            : `Narrowing ${total} candidate${total === 1 ? "" : "s"} to THE ONE…`}
      </p>
    </div>
  );
}
