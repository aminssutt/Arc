"use client";

// Arc landing page — product shell entry. Hero effects, scroll reveals, and
// an auto-looping demo of the investigation state machine, all on the Arc
// design tokens.

import { ArrowRight, Building2, FileText, Network, Radar, UserCheck } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useReducer, useState } from "react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Reveal } from "@/components/Reveal";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AgentGraph } from "@/components/investigation/AgentGraph";
import { InvestigationFlow } from "@/components/investigation/InvestigationFlow";
import type { DemoScenario } from "@/lib/contracts";
import {
  initialInvestigationState,
  investigationReducer,
  scenarioBeats,
  type AgentId,
} from "@/lib/investigation";

function useAutoDemo() {
  const [state, dispatch] = useReducer(investigationReducer, initialInvestigationState);

  useEffect(() => {
    let cancelled = false;
    const timers: number[] = [];

    const runLoop = (scenario: DemoScenario) => {
      if (cancelled) return;
      dispatch({ type: "reset" });
      let elapsed = 800;
      for (const beat of scenarioBeats(scenario)) {
        elapsed += beat.delayMs;
        timers.push(window.setTimeout(() => dispatch(beat.action), elapsed));
      }
      timers.push(
        window.setTimeout(() => runLoop(scenario === "confirm" ? "pivot" : "confirm"), elapsed + 4500),
      );
    };

    runLoop("confirm");
    return () => {
      cancelled = true;
      timers.forEach((id) => window.clearTimeout(id));
    };
  }, []);

  return state;
}

const FLOATING_BADGES: Array<{ label: string; tone: "primary" | "warning" | "secondary"; className: string; delay: string }> = [
  { label: "S1 · Sensor anomaly", tone: "primary", className: "left-[12%] top-[30%]", delay: "0s" },
  { label: "Correlation · active", tone: "warning", className: "right-[14%] top-[26%]", delay: "1.8s" },
  { label: "push sent → field", tone: "secondary", className: "right-[20%] bottom-[24%]", delay: "3.2s" },
];

export default function LandingPage() {
  const demo = useAutoDemo();
  const [selectedAgent, setSelectedAgent] = useState<AgentId | null>(null);

  return (
    <div className="min-h-screen bg-outer">
      {/* Nav */}
      <nav className="sticky top-0 z-40 flex items-center justify-between border-b border-borderSubtle bg-outer/80 px-6 py-4 backdrop-blur">
        <div className="flex items-center gap-4">
          <Image src="/assets/arc-logo.svg" alt="Arc" width={110} height={19} priority />
        </div>
        <div className="flex items-center gap-6">
          <a href="#how" className="text-body-sm text-textSecondary hover:text-text">
            How it works
          </a>
          <a href="#demo" className="text-body-sm text-textSecondary hover:text-text">
            Live demo
          </a>
          <Link href="/reports" className="text-body-sm text-textSecondary hover:text-text">
            Reports
          </Link>
          <ThemeToggle />
          <Link
            href="/login"
            className="inline-flex h-8 items-center rounded-md border border-accent bg-accentSubtle px-3 text-[14px] font-semibold leading-[14px] text-accentBright hover:bg-accentSubtle/70"
          >
            Sign in
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative flex min-h-[88vh] items-center justify-center overflow-hidden px-6">
        <div className="arc-hero-grid absolute inset-0" />
        <div className="arc-float pointer-events-none absolute -top-32 left-1/4 h-[420px] w-[560px] rounded-full bg-accent/10 blur-3xl" />
        <div
          className="arc-float pointer-events-none absolute bottom-0 right-1/4 h-[360px] w-[480px] rounded-full bg-secondary/10 blur-3xl"
          style={{ animationDelay: "2.5s" }}
        />
        <div className="pointer-events-none absolute left-1/2 top-1/2">
          <span className="arc-radar-ring h-[560px] w-[560px]" />
          <span className="arc-radar-ring h-[560px] w-[560px]" style={{ animationDelay: "1.6s" }} />
          <span className="arc-radar-ring h-[560px] w-[560px]" style={{ animationDelay: "3.2s" }} />
        </div>

        {FLOATING_BADGES.map((badge) => (
          <div
            key={badge.label}
            className={`arc-float pointer-events-none absolute hidden lg:block ${badge.className}`}
            style={{ animationDelay: badge.delay }}
          >
            <Badge tone={badge.tone} emphasis="subtle">
              {badge.label}
            </Badge>
          </div>
        ))}

        <div className="relative z-10 flex max-w-3xl flex-col items-center gap-6 text-center">
          <Reveal>
            <span className="inline-flex items-center gap-2 rounded-full border border-borderStrong bg-panelMuted px-4 py-1.5 text-label-sm font-medium text-textSecondary">
              <Radar className="h-3.5 w-3.5 text-accent" />
              Autonomous building incident response
            </span>
          </Reveal>
          <Reveal delay={120}>
            <h1 className="arc-gradient-text text-display font-bold">
              Your building,
              <br />
              investigated by agents.
            </h1>
          </Reveal>
          <Reveal delay={240}>
            <p className="max-w-xl text-body text-textSecondary">
              Arc watches every live feed, wakes the right specialist agent, gathers evidence against
              the building&apos;s own schematics — and hands the final call to a human.
            </p>
          </Reveal>
          <Reveal delay={360}>
            <div className="flex items-center gap-3">
              <Link href="/login?next=/monitor">
                <Button variant="primary" size="lg" trailingIcon={<ArrowRight className="h-5 w-5" />}>
                  Launch control room
                </Button>
              </Link>
              <a href="#how">
                <Button variant="ghost" size="lg">
                  See how it works
                </Button>
              </a>
            </div>
          </Reveal>
        </div>
      </section>

      {/* How it works — the investigation flow rail */}
      <section id="how" className="mx-auto max-w-7xl px-6 py-24">
        <Reveal>
          <p className="text-label-sm font-medium uppercase tracking-wide text-accent">How it works</p>
          <h2 className="mt-2 text-h3 font-semibold text-text">From anomaly to action report</h2>
          <p className="mt-2 max-w-2xl text-body-sm text-textSecondary">
            The pipeline below is live — it replays real confirm and pivot scenarios from the demo
            backend contracts, exactly as the control room renders them.
          </p>
        </Reveal>
        <Reveal delay={150} className="mt-8">
          <InvestigationFlow steps={demo.flow} action={<span />} />
        </Reveal>
      </section>

      {/* Live demo — agent orchestration */}
      <section id="demo" className="mx-auto max-w-7xl px-6 pb-24">
        <Reveal>
          <p className="text-label-sm font-medium uppercase tracking-wide text-accent">Live demo</p>
          <h2 className="mt-2 text-h3 font-semibold text-text">Sub-agents wake only when needed</h2>
        </Reveal>
        <Reveal delay={150} className="mt-8">
          <div className="h-[520px]">
            <AgentGraph
              agents={demo.agents}
              decisionLabel={demo.decisionLabel}
              decisionCopy={demo.decisionCopy}
              selectedAgent={selectedAgent}
              onSelectAgent={setSelectedAgent}
            />
          </div>
        </Reveal>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-7xl px-6 pb-24">
        <div className="grid gap-4 md:grid-cols-3">
          {[
            {
              icon: Building2,
              eyebrow: "Building Situation",
              title: "BIM-grounded evidence",
              body: "Anomalies pin directly onto the building wireframe, so operators see where — not just what.",
            },
            {
              icon: Network,
              eyebrow: "Agent Orchestration",
              title: "Dormant until delegated",
              body: "One main agent decides which specialist wakes up. No idle compute, no noise, full audit trail.",
            },
            {
              icon: UserCheck,
              eyebrow: "Human in the loop",
              title: "Field-validated reports",
              body: "Every diagnosis ends with a technician's verdict and a downloadable action report.",
            },
          ].map((feature, index) => (
            <Reveal key={feature.title} delay={index * 130}>
              <Card
                eyebrow={feature.eyebrow}
                title={feature.title}
                className="h-full"
              >
                <div className="flex flex-col gap-3">
                  <feature.icon className="h-5 w-5 text-accent" />
                  <p>{feature.body}</p>
                </div>
              </Card>
            </Reveal>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-borderSubtle bg-header/60">
        <div className="mx-auto flex max-w-7xl flex-col items-center gap-6 px-6 py-20 text-center">
          <Reveal>
            <h2 className="text-h3 font-semibold text-text">Step into the control room</h2>
          </Reveal>
          <Reveal delay={120}>
            <div className="flex items-center gap-3">
              <Link href="/login?next=/monitor">
                <Button variant="primary" size="md" trailingIcon={<ArrowRight className="h-4 w-4" />}>
                  Sign in
                </Button>
              </Link>
              <Link href="/reports">
                <Button variant="ghost" size="md" leadingIcon={<FileText className="h-4 w-4" />}>
                  Browse action reports
                </Button>
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      <footer className="flex items-center justify-between border-t border-borderSubtle px-6 py-6">
        <Image src="/assets/arc-logo.svg" alt="Arc" width={80} height={14} />
        <p className="text-caption text-muted">Arc — autonomous building operations. Hackathon build.</p>
      </footer>
    </div>
  );
}
