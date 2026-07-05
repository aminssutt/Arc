"use client";

import { Fragment, ReactNode } from "react";
import { FlowChevron } from "@/components/icons";
import type { FlowStep, FlowTone } from "@/lib/investigation";
import { PanelButton } from "./PanelButton";

// Investigation Flow panel — Figma node 84:943.
// Upcoming stages render as dimmed pending slots so the rail always reads as
// a four-step pipeline instead of an empty placeholder.
const STEP_TONES: Record<FlowTone, { card: string; badge: string }> = {
  primary: { card: "border-accent bg-raised", badge: "bg-accent text-background" },
  warning: { card: "border-warningBright bg-warningDeep", badge: "bg-warningBright text-background" },
  neutral: { card: "border-borderStrong bg-borderSubtle", badge: "bg-borderStrong text-background" },
  secondary: { card: "border-secondary bg-raised", badge: "bg-secondary text-background" },
};

const PENDING_TEMPLATE = [
  { title: "Detect", hint: "Main agent watches the live sensor feed." },
  { title: "Delegate", hint: "The right sub-agent is woken up." },
  { title: "Retrieve", hint: "Schematics and SOPs enter the context." },
  { title: "Handoff", hint: "A human gets the next field action." },
];

export function InvestigationFlow({
  steps,
  action,
}: {
  steps: FlowStep[];
  action?: ReactNode;
}) {
  const pending = PENDING_TEMPLATE.slice(steps.length);

  return (
    <section className="flex w-full shrink-0 flex-col gap-4 rounded-xl bg-panel p-4">
      <div className="flex w-full items-center justify-between">
        <div className="flex flex-col gap-1">
          <h2 className="text-h5 font-semibold text-text">Investigation Flow</h2>
          <p className="text-body-sm text-textSecondary">
            A step-by-step view of how the main agent detects an issue, activates the right sub-agent,
            gathers evidence, and hands off the next action to a human operator.
          </p>
        </div>
        {action ?? <PanelButton>timeline minimized</PanelButton>}
      </div>

      <div className="flex w-full items-stretch gap-2.5 overflow-x-auto rounded-md bg-background p-6">
        {steps.map((step, index) => {
          const tone = STEP_TONES[step.tone];
          return (
            <Fragment key={step.id}>
              {index > 0 && <FlowChevron className="h-12 w-[29px] shrink-0 self-center" />}
              <article
                className={`arc-fade-up flex min-w-0 flex-1 flex-col gap-4 rounded-md border-[1.5px] p-4 ${tone.card}`}
              >
                <div className="flex items-center gap-2.5">
                  <span
                    className={`flex w-10 items-center justify-center self-stretch rounded text-h6 font-semibold ${tone.badge}`}
                  >
                    {step.index}
                  </span>
                  <h3 className="text-h5 font-semibold text-text">{step.title}</h3>
                </div>
                <p className="text-body text-textSecondary">{step.body}</p>
                <p className="mt-auto text-body-sm text-muted">
                  {step.timestamp} / {step.source}
                </p>
              </article>
            </Fragment>
          );
        })}
        {pending.map((slot, index) => {
          const stepNumber = steps.length + index + 1;
          return (
            <Fragment key={slot.title}>
              {(steps.length > 0 || index > 0) && (
                <FlowChevron className="h-12 w-[29px] shrink-0 self-center opacity-40" />
              )}
              <article className="flex min-w-0 flex-1 flex-col gap-4 rounded-md border-[1.5px] border-borderSubtle bg-panelMuted p-4 opacity-60">
                <div className="flex items-center gap-2.5">
                  <span className="flex w-10 items-center justify-center self-stretch rounded bg-borderSubtle text-h6 font-semibold text-muted">
                    {String(stepNumber).padStart(2, "0")}
                  </span>
                  <h3 className="text-h5 font-semibold text-muted">{slot.title}</h3>
                </div>
                <p className="text-body text-muted">{slot.hint}</p>
                <p className="mt-auto text-body-sm text-muted/70">standby</p>
              </article>
            </Fragment>
          );
        })}
      </div>
    </section>
  );
}
