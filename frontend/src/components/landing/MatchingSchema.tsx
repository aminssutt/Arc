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
 * Demo pick: a complex rectifier fault in IDF-North → a senior energy specialist,
 * competence 1.00 (power, rectifier), in-zone. A scan highlights each candidate;
 * the winner keeps a persistent ring and the notify tether. Sky-blue, dash-flow,
 * in-view autocycle, reduced-motion safe, role=img + aria-label.
 */
import { memo } from "react";
import { motion } from "framer-motion";
import { Ban, Check, MapPin, Smartphone } from "lucide-react";
import { ACCENT, useAutoCycle, type AccentKey } from "./schematic-kit";

const BLUE = "#0078AE";
const SKY = ACCENT.arc;

interface Candidate {
  id: string;
  name: string;
  role: string;
  region: string;
  competence: number; // 0..1
  fit: number; // 0..1 difficulty/seniority fit
  score: number; // 0..1
  tier: string;
  inZone: boolean;
  eligible: boolean;
  winner: boolean;
  note: string;
  caption: string;
  accent: AccentKey;
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
    competence: 1.0, fit: 0.98, score: 0.99, tier: "senior", inZone: true, eligible: true, winner: true,
    note: "power, rectifier · in-zone", accent: "ember",
    caption: "Competence 1.00 (power, rectifier), senior level fits a complex fault, and in the site's zone → the one notified.",
  },
  {
    id: "E-142", name: "L. Bianchi", role: "Junior field tech", region: "IDF-North",
    competence: 0.6, fit: 0.32, score: 0.46, tier: "junior", inZone: true, eligible: true, winner: false,
    note: "competent · but junior for a complex fault", accent: "arc",
    caption: "Competent but junior — a complex rectifier fault needs seniority, so the difficulty-fit drops.",
  },
  {
    id: "E-088", name: "M. Conti", role: "Senior energy specialist", region: "IDF-South",
    competence: 1.0, fit: 0.98, score: 0.99, tier: "senior", inZone: false, eligible: true, winner: false,
    note: "great fit · but out-of-zone", accent: "warn",
    caption: "Perfect skills and level — but out-of-zone. An in-zone senior is preferred, so not this one.",
  },
  {
    id: "E-210", name: "S. Ferrari", role: "Transport / fibre tech", region: "IDF-North",
    competence: 0.0, fit: 0.0, score: 0.0, tier: "—", inZone: true, eligible: false, winner: false,
    note: "gated · wrong family", accent: "danger",
    caption: "A fibre tech fails the hard competence gate — wrong family, never eligible.",
  },
];

const WINNER = CANDIDATES.find((c) => c.winner)!;

function Bar({ value, color, label }: { value: number; color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-[9px] uppercase tracking-[0.1em] text-ink-faint w-[74px] shrink-0">{label}</span>
      <span className="relative h-1.5 flex-1 rounded-full bg-ink-line/70 overflow-hidden">
        <motion.span
          className="absolute inset-y-0 left-0 rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          whileInView={{ width: `${Math.round(value * 100)}%` }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        />
      </span>
      <span className="font-mono text-[10px] tabular-nums text-ink-soft w-8 text-right">{value.toFixed(2)}</span>
    </div>
  );
}

function MatchingSchemaImpl() {
  const { ref, active } = useAutoCycle(CANDIDATES.length, 1900);
  const activeCand = CANDIDATES[active];

  return (
    <div
      ref={ref}
      role="img"
      aria-label="Responder-matching: the diagnosed fault signature — family energy, equipment class rectifier, alarm code PWR-RECT-FAIL, region IDF-North — is scored against candidate technicians on competence, difficulty and seniority fit, and zone. A senior energy specialist in-zone with competence 1.00 wins and is the single technician notified by push — not a broadcast."
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

        {/* ── candidate scoring ───────────────────────────────────────── */}
        <div className="rounded-card border border-ink-line bg-paper-raised p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="section-label">Scoring the candidates</p>
            <span className="inline-flex items-center gap-1.5 font-mono text-[10px]" style={{ color: SKY }}>
              <span className="h-1.5 w-1.5 rounded-full animate-signal-pulse" style={{ background: SKY }} />
              scanning
            </span>
          </div>
          <div className="space-y-2.5">
            {CANDIDATES.map((cand, i) => {
              const on = i === active;
              const c = ACCENT[cand.accent];
              return (
                <motion.div
                  key={cand.id}
                  className="rounded-[11px] border p-3"
                  animate={{
                    borderColor: cand.winner ? BLUE : on ? c : "#E6E5DD",
                    backgroundColor: cand.winner ? `${BLUE}0A` : on ? "#FFFFFF" : "#F7F6F1",
                    opacity: cand.eligible ? (on || cand.winner ? 1 : 0.72) : 0.5,
                  }}
                  transition={{ duration: 0.35 }}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[13.5px] font-semibold text-ink truncate">{cand.name}</span>
                        {cand.winner && (
                          <span className="inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.08em] text-white" style={{ background: BLUE }}>
                            <Check className="h-2.5 w-2.5" /> chosen
                          </span>
                        )}
                      </div>
                      <span className="font-mono text-[10px] text-ink-faint">{cand.id} · {cand.role}</span>
                    </div>
                    <span
                      className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-mono text-[9.5px] shrink-0"
                      style={{
                        color: cand.inZone ? BLUE : "#8A897F",
                        background: cand.inZone ? `${BLUE}12` : "#EEEDE6",
                      }}
                    >
                      <MapPin className="h-2.5 w-2.5" /> {cand.region}
                    </span>
                  </div>

                  {cand.eligible ? (
                    <div className="mt-2.5 space-y-1.5">
                      <Bar value={cand.competence} color={SKY} label="competence" />
                      <Bar value={cand.fit} color={BLUE} label="senior-fit" />
                    </div>
                  ) : (
                    <div className="mt-2.5 flex items-center gap-1.5 font-mono text-[10.5px]" style={{ color: "#64748b" }}>
                      <Ban className="h-3 w-3" /> {cand.note}
                    </div>
                  )}

                  {cand.eligible && (
                    <div className="mt-2 flex items-center justify-between">
                      <span className="font-mono text-[10px] text-ink-faint">{cand.note}</span>
                      <span className="font-mono text-[11px] tabular-nums" style={{ color: cand.winner ? BLUE : "#8A897F" }}>
                        score {cand.score.toFixed(2)}
                      </span>
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* ── chosen + notify ─────────────────────────────────────────── */}
        <div className="rounded-card border p-4 flex flex-col" style={{ borderColor: `${BLUE}40`, background: `${BLUE}08` }}>
          <p className="section-label mb-3" style={{ color: BLUE }}>The one responder</p>
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-white font-display text-[15px] font-semibold" style={{ background: BLUE }}>
              {WINNER.name.split(" ").map((p) => p[0]).join("")}
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

      {/* live caption — why this candidate scores as it does */}
      <div className="mt-5 flex items-start gap-3 min-h-[2.5rem]">
        <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ background: ACCENT[activeCand.accent] }} />
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
