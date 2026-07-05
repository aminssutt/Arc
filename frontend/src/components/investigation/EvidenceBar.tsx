"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { EASE_MECH } from "@/motion/tokens";
import type { EvidenceItem, EvidenceTone } from "@/lib/investigation";

// Shared evidence bar — full-width chips shown under both monitor views.
// Chips animate in (AnimatePresence + stagger) as the agents collect evidence;
// clicking a chip highlights its marker on the Site situation floor plan.
const CHIP_TONES: Record<EvidenceTone, { card: string; badge: string }> = {
  primary: { card: "border-ember bg-raised", badge: "bg-ember text-surface" },
  primarySubtle: { card: "border-arc/60 bg-arc/[0.08]", badge: "bg-arc text-surface" },
  warning: { card: "border-warn bg-warn/10", badge: "bg-warn text-surface" },
  secondary: { card: "border-resolve bg-raised", badge: "bg-resolve text-surface" },
};

export function EvidenceBar({
  evidence,
  selectedId,
  onSelect,
}: {
  evidence: EvidenceItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const reduce = useReducedMotion();

  if (evidence.length === 0) {
    return (
      <div className="flex w-full shrink-0 rounded-md border border-dashed border-borderStrong p-4">
        <p className="text-body-sm text-muted">
          Evidence collected by the agents will appear here as the investigation progresses.
        </p>
      </div>
    );
  }

  return (
    <div className="flex w-full shrink-0 gap-4 overflow-x-auto">
      <AnimatePresence initial={false}>
        {evidence.map((item, index) => {
          const tone = CHIP_TONES[item.tone];
          const selected = item.id === selectedId;
          return (
            <motion.button
              key={item.id}
              layout={!reduce}
              initial={reduce ? false : { opacity: 0, y: 14, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={reduce ? undefined : { opacity: 0, scale: 0.97 }}
              transition={{ duration: 0.4, ease: EASE_MECH, delay: reduce ? 0 : index * 0.04 }}
              onClick={() => onSelect(item.id)}
              className={[
                "flex min-w-48 flex-1 gap-4 rounded-md border p-4 text-left transition-shadow",
                tone.card,
                selected ? "shadow-glow" : "",
              ].join(" ")}
            >
              <span
                className={`flex w-10 shrink-0 items-center justify-center self-stretch rounded text-h6 font-semibold ${tone.badge}`}
              >
                {item.id.slice(0, 2)}
              </span>
              <span className="flex min-w-0 flex-col gap-1">
                <span className="truncate text-body-sm font-medium text-text">{item.title}</span>
                <span className="truncate font-mono text-caption text-muted">{item.meta}</span>
              </span>
            </motion.button>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
