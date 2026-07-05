/**
 * Arc — the telecom network-operations landing.
 *
 * A numbered editorial "diapo" (ported from the ECU industrial design language,
 * retargeted for telecom) on a white + sky-blue palette: a LIGHT Spline hero,
 * then scroll-revealed numbered sections separated by hairlines, one dark
 * live-control-room "screen" section, and a set of animated sky-blue schematics
 * that explain the multi-agent fault-response system.
 *
 * Server component composing client islands (hero + framer-motion schematics),
 * so the page ships as a thin shell and the heavy motion subtrees are isolated
 * + memoized inside their own components.
 */
import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { SectionReveal } from "@/motion/SectionReveal";
import { FadeIn, Stagger, StaggerItem, AnimatedNumber } from "@/motion/Primitives";
import HeroScene from "@/components/landing/HeroScene";
import AgentOrchestration from "@/components/landing/AgentOrchestration";
import MatchingSchema from "@/components/landing/MatchingSchema";
import FaultPipeline from "@/components/landing/FaultPipeline";
import ValidationLoop from "@/components/landing/ValidationLoop";
import ControlRoomPreview from "@/components/landing/ControlRoomPreview";
import GroundedCitations from "@/components/landing/GroundedCitations";

export const metadata: Metadata = {
  title: "Arc — network operations agents",
  description:
    "Arc is a multi-agent system for telecom network operations: it detects a site fault, diagnoses the root cause grounded in your own technical docs with citations, matches and notifies one field technician, then dispatches — closing with a cited action report. Reasoning on Vultr.",
};

// Sky-blue CTA — replaces the retired ember `.btn-signal`, styled locally (no
// globals.css edits). Brand blue #0078AE (the ARC logo colour).
const BTN_SKY =
  "inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#0078AE] text-white text-sm font-semibold " +
  "transition-all duration-300 ease-expo hover:bg-[#0a6ea0] hover:shadow-[0_0_28px_-6px_rgba(0,120,174,0.65)]";

// ── §01 problem beats ────────────────────────────────────────────────────────
const PROBLEM_BEATS = [
  {
    tag: "Today",
    body: "A national carrier runs tens of thousands of cell sites. Any one can fail at 3am — a rectifier, a transport link, a power plant.",
  },
  {
    tag: "The clock",
    body: "From minute zero an SLA clock is running. The alarm storm lights up dozens of nodes and hides the one site that matters.",
  },
  {
    tag: "The shift",
    body: "The senior engineers who could read a fault by instinct are retiring. That instinct doesn't scale — and it doesn't answer the phone at 3am.",
  },
] as const;

// ── §08 stat tiles ───────────────────────────────────────────────────────────
function StatTile({
  value,
  prefix,
  suffix,
  label,
  sub,
}: {
  value: number;
  prefix?: string;
  suffix?: string;
  label: string;
  sub?: string;
}) {
  return (
    <div className="border-l-2 border-ink-line pl-4 transition-colors duration-300 hover:border-[#0078AE]">
      <p className="font-condensed text-5xl sm:text-6xl font-semibold tabular-nums tracking-tight text-ink">
        {prefix}
        <AnimatedNumber value={value} />
        {suffix}
      </p>
      <p className="text-sm text-ink-soft mt-1">{label}</p>
      {sub && <p className="font-mono text-[11px] text-ink-faint mt-0.5">{sub}</p>}
    </div>
  );
}

function Hairline() {
  return (
    <div className="max-w-content mx-auto px-6 sm:px-10">
      <div className="hairline" />
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="bg-paper">
      {/* ── Hero (light, Spline) ────────────────────────────────────────── */}
      <HeroScene />

      {/* ── 01 The problem ──────────────────────────────────────────────── */}
      <SectionReveal
        id="problem"
        index="01"
        eyebrow="The problem"
        title="A fault fires at 3am. The clock is already running."
        intro="A race against an SLA clock, run by fewer and fewer people who can read a fault by instinct."
      >
        <div className="grid lg:grid-cols-[1.12fr_0.88fr] gap-10 lg:gap-16 items-start">
          {/* annotated spine of beats */}
          <div role="list" className="relative border-l border-ink-line pl-7 space-y-9">
            {PROBLEM_BEATS.map((beat, i) => (
              <FadeIn role="listitem" key={beat.tag} delay={i * 0.08} className="relative">
                <span
                  className={`absolute -left-[35px] top-1 h-3.5 w-3.5 rounded-full border-2 border-paper ${
                    i === PROBLEM_BEATS.length - 1 ? "bg-[#0078AE]" : "bg-ink-line"
                  }`}
                />
                <p className="section-label mb-2">{beat.tag}</p>
                <p className="font-display text-lg sm:text-xl leading-snug text-ink-soft text-balance">
                  {beat.body}
                </p>
              </FadeIn>
            ))}
          </div>

          {/* the question — sticky card */}
          <FadeIn className="card-padded bg-[#0078AE]/[0.04] border-[#0078AE]/25 lg:sticky lg:top-24">
            <p className="section-label text-[#0078AE] mb-3">The question</p>
            <p className="font-display text-xl sm:text-2xl leading-snug text-ink text-balance">
              What if every fault got the instinct of your best engineer — grounded in your own docs,
              and never dispatching a crew without a human&apos;s say-so?
            </p>
            <div className="hairline my-5" />
            <p className="text-[13px] text-ink-soft leading-relaxed">
              That is Arc: specialist agents under one Orchestrator, reasoning on Vultr and answering to
              a human in the field.
            </p>
          </FadeIn>
        </div>
      </SectionReveal>

      <Hairline />

      {/* ── 02 The agent team ───────────────────────────────────────────── */}
      <SectionReveal
        id="method"
        index="02"
        eyebrow="The agent team"
        title="One Orchestrator. Six agents. One human veto."
        intro="Typed state routed to the right specialist at each step — with a human field-validation loop before anything moves."
      >
        <div className="space-y-14">
          <div className="card-padded mx-auto w-full max-w-4xl !p-4 sm:!p-6">
            <AgentOrchestration />
          </div>

          <div className="grid lg:grid-cols-[1fr_1.1fr] gap-8 lg:gap-12 items-center">
            <ValidationLoop compact />
            <div>
              <p className="section-label mb-3">Directed, not autonomous</p>
              <p className="section-desc">
                One specialist at a time over typed state. Every diagnosis opens a field-validation loop —
                a real technician holds the veto. Confirm, and it flows to remediation and dispatch;
                refuse, and it pivots to re-diagnose.
              </p>
            </div>
          </div>
        </div>
      </SectionReveal>

      <Hairline />

      {/* ── 03 The matching process ─────────────────────────────────────── */}
      <SectionReveal
        id="matching"
        index="03"
        eyebrow="The matching process"
        title="One fault, one responder — scored, not broadcast."
        intro="Arc scores every field technician on competence, seniority fit and zone, then pages only the single best responder."
      >
        <div className="card-padded !p-4 sm:!p-6">
          <MatchingSchema />
        </div>
      </SectionReveal>

      <Hairline />

      {/* ── 04 The pipeline (signature diagram) ─────────────────────────── */}
      <SectionReveal
        id="pipeline"
        index="04"
        eyebrow="The pipeline"
        title="From a live fault to a cited action report."
        intro="Detect, diagnose with citations, match a responder, a human's on-site verdict, then remediation and a cited report. Refusal pivots — it never stalls."
      >
        <div className="card-padded !p-4 sm:!p-6">
          <FaultPipeline />
        </div>
      </SectionReveal>

      {/* ── 05 Live control room (dark screen) ──────────────────────────── */}
      <section id="live" className="scroll-mt-16 bg-surface text-paper py-20 sm:py-28">
        <div className="max-w-content mx-auto px-6 sm:px-10">
          <div className="flex items-baseline gap-4">
            <span className="font-mono text-[13px] text-[#4d9dff]">05</span>
            <span className="font-mono text-[11px] uppercase tracking-label text-paper/45">
              Live control room
            </span>
          </div>
          <p className="mt-5 lead text-paper/70 max-w-prose">
            The live event log, the network topology, and the agent&apos;s reasoning — from the first
            anomaly at PAR-021-NORD to the confirmed dispatch, on one screen.
          </p>

          <div className="mt-10">
            <ControlRoomPreview />
          </div>

          <div className="mt-8">
            <Link href="/login?next=/monitor" className={`${BTN_SKY} group`}>
              <span className="inline-flex h-1.5 w-1.5 rounded-full bg-white" />
              Launch the control room
              <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── 06 Human-in-the-loop ────────────────────────────────────────── */}
      <SectionReveal
        id="validation"
        index="06"
        eyebrow="Human in the loop"
        title="The agent proposes. The field decides."
        intro="No crew moves on a hunch — every diagnosis is validated against reality by the person at the cabinet."
      >
        <div className="grid lg:grid-cols-[1.1fr_1fr] gap-10 lg:gap-14 items-center">
          <div>
            <p className="section-label mb-3">The field-validation loop</p>
            <p className="section-desc">
              The moment Root-Cause lands a hypothesis, a push hits the on-call technician&apos;s phone.
              They test it on-site: confirm, and the pipeline advances; refuse — with a
              counter-measurement — and the agent pivots and re-diagnoses. The human always holds the veto.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <span className="chip">push → phone</span>
              <span className="chip">on-site test</span>
              <span className="chip">confirm / refuse</span>
              <span className="chip">counter-measurement</span>
              <span className="chip">pivot</span>
            </div>
          </div>
          <ValidationLoop />
        </div>
      </SectionReveal>

      <Hairline />

      {/* ── 07 Grounded & cited ─────────────────────────────────────────── */}
      <SectionReveal
        id="grounded"
        index="07"
        eyebrow="Grounded & cited"
        title="Every cause cites your own docs — down to the page."
        intro="Each claim is tethered to a specific page of the carrier's own library — and those exact sources ship, clickable, in the final report."
      >
        <div className="card-padded !p-5 sm:!p-8">
          <GroundedCitations />
        </div>
      </SectionReveal>

      <Hairline />

      {/* ── 08 By the numbers ───────────────────────────────────────────── */}
      <SectionReveal
        id="numbers"
        index="08"
        eyebrow="By the numbers"
        title="Grounded, validated, fast."
        intro="One demo incident, end to end: PAR-021-NORD, an energy / rectifier fault, part PN-RECT-48-2000."
      >
        <Stagger className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <StaggerItem>
            <StatTile value={6} label="specialist agents" sub="under one Orchestrator" />
          </StaggerItem>
          <StaggerItem>
            <StatTile value={1} label="human veto" sub="field-validated" />
          </StaggerItem>
          <StaggerItem>
            <StatTile value={100} suffix="%" label="cited claims" sub="grounded on your docs" />
          </StaggerItem>
          <StaggerItem>
            <StatTile value={3} prefix="<" suffix=" min" label="to first action" sub="detect → dispatch" />
          </StaggerItem>
        </Stagger>
      </SectionReveal>

      <Hairline />

      {/* ── Close + footer (light) ──────────────────────────────────────── */}
      <section className="bg-paper text-ink">
        <div className="max-w-content mx-auto px-6 sm:px-10 py-20 sm:py-28 text-center">
          <p className="font-mono text-[11px] uppercase tracking-label text-[#0078AE]">Arc · network operations</p>
          <h2 className="mt-5 mx-auto max-w-2xl font-display font-semibold tracking-[-0.02em] text-[clamp(1.9rem,4vw,3rem)] leading-[1.05] text-ink text-balance">
            Not retrieve-then-answer. A real agent — grounded, telecom-native, on Vultr.
          </h2>
          <div className="mt-9 flex justify-center">
            <Link href="/login?next=/monitor" className={`${BTN_SKY} group`}>
              <span className="inline-flex h-1.5 w-1.5 rounded-full bg-white" />
              Launch the control room
              <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" />
            </Link>
          </div>
        </div>
        <div className="border-t border-ink-line">
          <div className="max-w-content mx-auto px-6 sm:px-10 py-6 flex flex-col sm:flex-row items-center justify-between gap-3">
            <Image src="/assets/arc-logo.svg" alt="Arc" width={142} height={24} className="h-[20px] w-auto" />
            <p className="font-mono text-[11px] text-ink-faint">
              Arc · live event stream · site PAR-021-NORD
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
