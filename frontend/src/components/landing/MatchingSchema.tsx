"use client";

/**
 * §03 — THE matching-process schematic, faithful to
 * `agents/responder_matching/matcher.py`.
 *
 * The diagnosed fault SIGNATURE {family, equipment class, alarm code, region}
 * is scored against candidate field technicians on three axes:
 *   · competence      = 0.6·skill-overlap + 0.4·family-match   (a HARD gate)
 *   · difficulty-fit  = how well the person's seniority level fits the task
 *                       (complex → senior, simple → junior)
 *   · zone            = in the site's region is preferred (fallback out-of-zone)
 * score = 0.5·competence + 0.5·difficulty-fit  → the SINGLE best responder is
 * notified (one push to their phone) — NOT a broadcast.
 *
 * The middle column is a live ROSTER OF FICHES: every technician mounts as a
 * profile card (avatar, tier, skills, zone, a score ring + competence/fit bars),
 * then the non-retained ones are flagged (✕ reason) and collapse out one by one
 * — weakest first — until only the chosen tech stays, ringed, with the notify
 * tether. It narrows on a loop while in view; reduced-motion jumps to the winner.
 *
 * Demo pick: a complex rectifier fault in IDF-North → a senior energy specialist,
 * competence 1.00 (power, rectifier), in-zone.
 */
import { memo, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useInView, useReducedMotion } from "framer-motion";
import { Ban, Check, MapPin, ShieldCheck, Smartphone } from "lucide-react";
import { ACCENT } from "./schematic-kit";

const BLUE = "#0078AE";
const SKY = ACCENT.arc;
const RED = "#c9433f";
const EASE = [0.16, 1, 0.3, 1] as const;

interface Candidate {
  id: string;
  name: string;
  role: string;
  region: string;
  competence: number; // 0..1
  fit: number; // 0..1 difficulty/seniority fit
  score: number; // 0..1
  tier: string;
  skills: string[];
  inZone: boolean;
  eligible: boolean;
  winner: boolean;
  note: string;
  elim: string; // why this candidate is dropped (✕ reason)
  caption: string;
}

const SIGNATURE = [
  { k: "family", v: "energy" },
  { k: "equipment class", v: "rectifier" },
  { k: "alarm code", v: "PWR-RECT-FAIL" },
  { k: "region", v: "IDF-North" },
] as const;

const CANDIDATES: Candidate[] = [
  {
    id: "E-107", name: "A. Rossi", role: "Senior energy specialist", region: "IDF-North",
    competence: 1.0, fit: 0.98, score: 0.99, tier: "senior", skills: ["power", "rectifier"],
    inZone: true, eligible: true, winner: true, note: "power, rectifier · in-zone", elim: "",
    caption: "Competence 1.00 (power, rectifier), senior level fits a complex fault, and in the site's zone → the one notified.",
  },
  {
    id: "E-142", name: "L. Bianchi", role: "Junior field tech", region: "IDF-North",
    competence: 0.6, fit: 0.32, score: 0.46, tier: "junior", skills: ["power", "rectifier"],
    inZone: true, eligible: true, winner: false, note: "competent · junior", elim: "junior · complex fault",
    caption: "Competent but junior — a complex rectifier fault needs seniority, so the difficulty-fit drops.",
  },
  {
    id: "E-088", name: "M. Conti", role: "Senior energy specialist", region: "IDF-South",
    competence: 1.0, fit: 0.98, score: 0.99, tier: "senior", skills: ["power", "rectifier"],
    inZone: false, eligible: true, winner: false, note: "great fit · out-of-zone", elim: "out-of-zone",
    caption: "Perfect skills and level — but out-of-zone. An in-zone senior is preferred, so not this one.",
  },
  {
    id: "E-210", name: "S. Ferrari", role: "Transport / fibre tech", region: "IDF-North",
    competence: 0.0, fit: 0.0, score: 0.0, tier: "—", skills: ["fibre"],
    inZone: true, eligible: false, winner: false, note: "wrong family", elim: "wrong family · gated",
    caption: "A fibre tech fails the hard competence gate — wrong family, never eligible.",
  },
];

const WINNER = CANDIDATES.find((c) => c.winner)!;
const ALL_IDS = CANDIDATES.map((c) => c.id);

// Elimination order — weakest first, closest contender last (out-of-zone is
// penalised hard, then raw score), so the roster narrows from clearly-wrong
// picks down to THE ONE. Mirrors the live matcher's ranking.
const ELIM_ORDER = CANDIDATES.filter((c) => !c.winner)
  .slice()
  .sort((a, b) => (a.score - (a.inZone ? 0 : 0.5)) - (b.score - (b.inZone ? 0 : 0.5)))
  .map((c) => c.id);

function initials(name: string): string {
  return name.replace(/\.\s*/g, "").split(/\s+/).map((p) => p[0]).join("").slice(0, 2).toUpperCase();
}

// Circular score gauge — the fiche's headline stat.
function ScoreRing({ value, tone }: { value: number; tone: "winner" | "flagged" | "idle" }) {
  const pct = Math.max(0, Math.min(1, value));
  const r = 16;
  const circ = 2 * Math.PI * r;
  const color = tone === "winner" ? BLUE : tone === "flagged" ? "#b9b8ae" : SKY;
  return (
    <div className="relative grid h-[46px] w-[46px] shrink-0 place-items-center">
      <svg viewBox="0 0 42 42" className="h-[46px] w-[46px] -rotate-90" aria-hidden>
        <circle cx="21" cy="21" r={r} fill="none" stroke="#E6E5DD" strokeWidth="3.5" />
        <motion.circle
          cx="21" cy="21" r={r} fill="none" stroke={color} strokeWidth="3.5" strokeLinecap="round"
          strokeDasharray={circ}
          animate={{ strokeDashoffset: tone === "flagged" ? circ : circ * (1 - pct) }}
          transition={{ duration: 0.6, ease: EASE }}
        />
      </svg>
      <div className="absolute flex flex-col items-center leading-none">
        <span className="font-mono text-[11px] font-semibold tabular-nums text-ink">{value.toFixed(2)}</span>
        <span className="font-mono text-[6.5px] uppercase tracking-[0.12em] text-ink-faint">score</span>
      </div>
    </div>
  );
}

function MiniBar({ value, color, label, off }: { value: number; color: string; label: string; off?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-[68px] shrink-0 font-mono text-[8.5px] uppercase tracking-[0.1em] text-ink-faint">{label}</span>
      <span className="relative h-1 flex-1 overflow-hidden rounded-full bg-ink-line/70">
        <motion.span
          className="absolute inset-y-0 left-0 rounded-full"
          style={{ background: color }}
          animate={{ width: off ? "0%" : `${Math.round(value * 100)}%` }}
          transition={{ duration: 0.55, ease: EASE }}
        />
      </span>
      <span className="w-7 shrink-0 text-right font-mono text-[9px] tabular-nums text-ink-soft">{value.toFixed(2)}</span>
    </div>
  );
}

function Pill({ children, tone }: { children: React.ReactNode; tone: "senior" | "junior" | "skill" | "zone" | "ooz" | "gate" | "off" }) {
  const style: Record<string, React.CSSProperties> = {
    senior: { color: BLUE, background: `${BLUE}12`, borderColor: `${BLUE}40` },
    junior: { color: "#9a6a1e", background: "#f5eddc", borderColor: "#e4d3ad" },
    skill: { color: "#4C4B45", background: "#F0EFE8", borderColor: "#E1E0D7" },
    zone: { color: "#127a52", background: "#e3f5ec", borderColor: "#bfe6d3" },
    ooz: { color: RED, background: "#fbeceb", borderColor: "#f0cbc9" },
    gate: { color: RED, background: "#fbeceb", borderColor: "#f0cbc9" },
    off: { color: "#8A897F", background: "#F0EFE8", borderColor: "#E1E0D7" },
  };
  return (
    <span
      className="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wide"
      style={style[tone]}
    >
      {children}
    </span>
  );
}

// Looping progressive-narrowing state machine, gated on in-view + reduced motion.
function useNarrowing() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: false, margin: "0px 0px -20% 0px" });
  const reduce = useReducedMotion();
  const [remaining, setRemaining] = useState<string[]>(ALL_IDS);
  const [flagged, setFlagged] = useState<string | null>(null);

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setRemaining([WINNER.id]);
      setFlagged(null);
      return;
    }
    const timers: number[] = [];
    const run = () => {
      setRemaining(ALL_IDS);
      setFlagged(null);
      let t = 1500; // "all technicians on call" opening beat — roster reads first
      for (const id of ELIM_ORDER) {
        timers.push(window.setTimeout(() => setFlagged(id), t)); // flash the reason
        timers.push(
          window.setTimeout(() => {
            setFlagged((cur) => (cur === id ? null : cur));
            setRemaining((cur) => cur.filter((x) => x !== id)); // collapse it out
          }, t + 900),
        );
        t += 1350;
      }
      timers.push(window.setTimeout(run, t + 3000)); // hold on the winner, then loop
    };
    run();
    return () => timers.forEach((x) => window.clearTimeout(x));
  }, [inView, reduce]);

  return { ref, remaining, flagged, reduce };
}

function MatchingSchemaImpl() {
  const { ref, remaining, flagged, reduce } = useNarrowing();
  const remainingSet = new Set(remaining);
  const visible = CANDIDATES.filter((c) => remainingSet.has(c.id));
  const chosenLit = remaining.length <= 1;

  const flaggedCand = CANDIDATES.find((c) => c.id === flagged);
  const activeCand = flaggedCand ?? WINNER;

  return (
    <div
      ref={ref}
      role="img"
      aria-label="Responder-matching: the diagnosed fault signature — family energy, equipment class rectifier, alarm code PWR-RECT-FAIL, region IDF-North — is scored against candidate technicians on competence, difficulty and seniority fit, and zone. Candidates are eliminated one by one — a gated fibre tech, a junior, an out-of-zone senior — until a senior energy specialist in-zone with competence 1.00 wins and is the single technician notified by push, not a broadcast."
    >
      <div className="grid gap-5 lg:grid-cols-[0.92fr_1.3fr_0.92fr] items-stretch">
        {/* ── fault signature ─────────────────────────────────────────── */}
        <div className="rounded-card border border-ink-line bg-paper-raised p-4 flex flex-col">
          <p className="section-label mb-3">Diagnosed fault signature</p>
          <div className="space-y-2">
            {SIGNATURE.map((s) => (
              <div key={s.k} className="flex items-center justify-between gap-3 border-b border-ink-line/60 pb-1.5 last:border-0">
                <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-ink-faint">{s.k}</span>
                <span className="font-mono text-[12px] text-ink">{s.v}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 inline-flex items-center gap-2 self-start rounded-md px-2.5 py-1" style={{ background: `${BLUE}14`, border: `1px solid ${BLUE}40` }}>
            <span className="h-1.5 w-1.5 rounded-full animate-signal-pulse" style={{ background: BLUE }} />
            <span className="font-mono text-[10px] uppercase tracking-[0.1em]" style={{ color: BLUE }}>
              difficulty: complex → senior
            </span>
          </div>
          <p className="mt-4 text-[12px] text-ink-soft leading-relaxed">
            score = 0.5·competence + 0.5·difficulty-fit, in-zone preferred.
          </p>
        </div>

        {/* ── candidate fiches — narrow one by one to THE ONE ──────────── */}
        <div className="rounded-card border border-ink-line bg-paper-raised p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="section-label">{chosenLit ? "The one responder" : "On-call technicians"}</p>
            <span className="inline-flex items-center gap-1.5 font-mono text-[10px] tabular-nums" style={{ color: SKY }}>
              {!chosenLit && <span className="h-1.5 w-1.5 rounded-full animate-signal-pulse" style={{ background: SKY }} />}
              {chosenLit ? "narrowed → 1" : `narrowing ${remaining.length} → 1`}
            </span>
          </div>
          <div className="space-y-2.5">
            <AnimatePresence initial={false}>
              {visible.map((cand, i) => {
                const isFlagged = cand.id === flagged;
                const lit = cand.winner && chosenLit;
                const tone = lit ? "winner" : isFlagged ? "flagged" : "idle";
                return (
                  <motion.div
                    key={cand.id}
                    layout={!reduce}
                    initial={reduce ? false : { opacity: 0, y: 12 }}
                    animate={{
                      opacity: isFlagged ? 0.6 : 1,
                      y: 0,
                      filter: isFlagged ? "grayscale(0.9)" : "grayscale(0)",
                    }}
                    exit={reduce ? { opacity: 0 } : { opacity: 0, height: 0, marginTop: 0, y: -6, scale: 0.97 }}
                    transition={{ duration: 0.42, ease: EASE, delay: reduce ? 0 : i * 0.05 }}
                    className="relative overflow-hidden rounded-[13px] border p-3.5"
                    style={{
                      borderColor: lit ? BLUE : isFlagged ? `${RED}66` : "#E6E5DD",
                      background: lit
                        ? `radial-gradient(120% 140% at 100% 0%, ${BLUE}12, #FFFFFF 62%)`
                        : "#FFFFFF",
                      boxShadow: lit
                        ? `0 0 0 1px ${BLUE}, 0 18px 40px -18px ${BLUE}99`
                        : "0 1px 2px rgba(19,19,17,0.04)",
                    }}
                  >
                    {/* top accent strip */}
                    <span
                      className="pointer-events-none absolute inset-x-0 top-0 h-[3px]"
                      style={{ background: lit ? BLUE : isFlagged ? `${RED}88` : "transparent" }}
                    />

                    {/* identity row: avatar · name/id/role · score ring */}
                    <div className="flex items-start gap-3">
                      <span className="relative shrink-0">
                        <span
                          className="grid h-11 w-11 place-items-center rounded-full font-display text-[14px] font-semibold text-white ring-1 ring-black/5"
                          style={{ background: lit ? `linear-gradient(140deg, #17a0d4, ${BLUE})` : "linear-gradient(140deg, #c9c8be, #a9a89e)" }}
                        >
                          {initials(cand.name)}
                        </span>
                        <span
                          className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white"
                          style={{ background: lit ? "#16a34a" : isFlagged ? RED : SKY }}
                        />
                      </span>

                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                          <span className="text-[13.5px] font-semibold text-ink truncate">{cand.name}</span>
                          {lit && (
                            <motion.span
                              initial={reduce ? false : { opacity: 0, scale: 0.8 }}
                              animate={{ opacity: 1, scale: 1 }}
                              transition={{ duration: 0.3, ease: EASE }}
                              className="inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.08em] text-white"
                              style={{ background: BLUE }}
                            >
                              <Check className="h-2.5 w-2.5" /> chosen → paged
                            </motion.span>
                          )}
                        </div>
                        <span className="font-mono text-[10px] text-ink-faint">{cand.id} · {cand.role}</span>

                        {/* tier · skills · zone */}
                        <div className="mt-2 flex flex-wrap items-center gap-1.5">
                          {cand.eligible ? (
                            <Pill tone={cand.tier === "senior" ? "senior" : "junior"}>
                              <ShieldCheck className="h-2.5 w-2.5" /> {cand.tier}
                            </Pill>
                          ) : (
                            <Pill tone="gate"><Ban className="h-2.5 w-2.5" /> gated</Pill>
                          )}
                          {cand.skills.map((s) => (
                            <Pill key={s} tone="skill">{s}</Pill>
                          ))}
                          <Pill tone={cand.inZone ? "zone" : "ooz"}>
                            <MapPin className="h-2.5 w-2.5" /> {cand.inZone ? "in-zone" : "out-of-zone"}
                          </Pill>
                        </div>
                      </div>

                      <ScoreRing value={cand.score} tone={tone} />
                    </div>

                    {/* competence / senior-fit bars, or the gate note */}
                    {cand.eligible ? (
                      <div className="mt-3 space-y-1.5">
                        <MiniBar value={cand.competence} color={SKY} label="competence" off={isFlagged} />
                        <MiniBar value={cand.fit} color={BLUE} label="senior-fit" off={isFlagged} />
                      </div>
                    ) : (
                      <div className="mt-3 flex items-center gap-1.5 font-mono text-[10.5px]" style={{ color: RED }}>
                        <Ban className="h-3 w-3" /> {cand.note}
                      </div>
                    )}

                    {/* elimination reason — flashes as the fiche is removed */}
                    {isFlagged && (
                      <motion.div
                        initial={reduce ? false : { opacity: 0, x: -4 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.25 }}
                        className="mt-2.5 inline-flex items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-[10px]"
                        style={{ color: RED, borderColor: `${RED}33`, background: `${RED}0d` }}
                      >
                        <Ban className="h-3 w-3" />
                        <span className="line-through decoration-ink-faint/40">✕ {cand.elim}</span>
                      </motion.div>
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        </div>

        {/* ── chosen + notify ─────────────────────────────────────────── */}
        <div className="rounded-card border p-4 flex flex-col" style={{ borderColor: `${BLUE}40`, background: `${BLUE}08` }}>
          <p className="section-label mb-3" style={{ color: BLUE }}>The one responder</p>
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-white font-display text-[15px] font-semibold" style={{ background: `linear-gradient(140deg, #17a0d4, ${BLUE})` }}>
              {initials(WINNER.name)}
            </div>
            <div className="min-w-0">
              <p className="text-[14px] font-semibold text-ink">{WINNER.name}</p>
              <p className="font-mono text-[10.5px] text-ink-soft">{WINNER.role}</p>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            <span className="chip" style={{ borderColor: `${BLUE}55`, color: BLUE }}>senior</span>
            <span className="chip" style={{ borderColor: `${BLUE}55`, color: BLUE }}>competence 1.00</span>
            <span className="chip" style={{ borderColor: `${BLUE}55`, color: BLUE }}>in-zone</span>
          </div>

          {/* notify tether → phone */}
          <div className="mt-4 flex items-center gap-2.5">
            <svg viewBox="0 0 60 20" width="60" height="20" className="shrink-0" aria-hidden>
              <path d="M 2,10 L 54,10" fill="none" stroke={BLUE} strokeWidth={1.5} strokeDasharray="3 6" strokeLinecap="round" className="animate-dash-flow" />
              <path d="M 50,5 L 58,10 L 50,15" fill="none" stroke={BLUE} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-white font-mono text-[10.5px]" style={{ background: BLUE }}>
              <Smartphone className="h-3 w-3" /> 1 push · phone (iOS)
            </span>
          </div>

          <div className="mt-auto pt-4">
            <div className="flex items-center gap-1.5 font-mono text-[10.5px] text-ink-faint line-through decoration-ink-faint/70">
              <Ban className="h-3 w-3" /> broadcast to every on-call tech
            </div>
            <p className="mt-1 text-[11px] text-ink-soft">Only the best-fit responder is paged — not a broadcast.</p>
          </div>
        </div>
      </div>

      {/* live caption — why the current candidate is dropped, or why the winner wins */}
      <div className="mt-5 flex items-start gap-3 min-h-[2.5rem]">
        <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ background: flaggedCand ? RED : BLUE }} />
        <p className="text-[14px] text-ink-soft leading-relaxed">
          <span className="font-mono text-[12px] text-ink mr-1.5">{activeCand.name}</span>
          {activeCand.caption}
        </p>
      </div>
    </div>
  );
}

export const MatchingSchema = memo(MatchingSchemaImpl);
export default MatchingSchema;
