"use client";

import type { EvidenceItem, EvidenceTone } from "@/lib/investigation";

// Shared evidence bar — Figma node 133:530 / 133:608. Full-width chips shown
// under both monitor views; clicking a chip highlights its marker on the
// Building Situation floor plan.
const CHIP_TONES: Record<EvidenceTone, { card: string; badge: string }> = {
  primary: { card: "border-accent bg-raised", badge: "bg-accent text-background" },
  primarySubtle: { card: "border-accent bg-accentSubtle", badge: "bg-accent text-background" },
  warning: { card: "border-warning bg-warningDeep", badge: "bg-warning text-background" },
  secondary: { card: "border-secondary bg-raised", badge: "bg-secondary text-background" },
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
      {evidence.map((item) => {
        const tone = CHIP_TONES[item.tone];
        const selected = item.id === selectedId;
        return (
          <button
            key={item.id}
            onClick={() => onSelect(item.id)}
            className={[
              "arc-fade-up flex min-w-48 flex-1 gap-4 rounded-md border p-4 text-left transition-shadow",
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
              <span className="truncate text-caption text-muted">{item.meta}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
