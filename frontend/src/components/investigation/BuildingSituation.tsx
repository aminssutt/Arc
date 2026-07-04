"use client";

import Image from "next/image";
import type { EvidenceItem, EvidenceTone } from "@/lib/investigation";

// Building Situation viewport — Figma node 133:287. The plain (non-activated)
// floor plan variants from the 도면 component set (84:211 light / 84:213 dark)
// fill the panel; fault locations are shown by the interactive dot markers
// synced with the shared evidence bar, not by a pre-highlighted image.
const MARKER_TONES: Record<EvidenceTone, string> = {
  primary: "bg-accent",
  primarySubtle: "bg-accent",
  warning: "bg-warning",
  secondary: "bg-secondary",
};

export function BuildingSituation({
  evidence,
  selectedId,
  onSelect,
}: {
  evidence: EvidenceItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="relative h-full min-h-0 w-full overflow-hidden rounded-xl border border-borderSubtle bg-background">
      {/* unoptimized: serve the transparent PNGs verbatim — the optimizer's
          cache kept resurrecting older, background-baked variants. */}
      <Image
        src="/assets/bim-floorplan-light.png"
        alt="B5 electrical room BIM wireframe"
        fill
        sizes="100vw"
        className="select-none object-contain p-4 dark:hidden"
        priority
        unoptimized
      />
      <Image
        src="/assets/bim-floorplan-dark.png"
        alt="B5 electrical room BIM wireframe"
        fill
        sizes="100vw"
        className="hidden select-none object-contain p-4 dark:block"
        priority
        unoptimized
      />
      {evidence
        .filter((item) => item.marker)
        .map((item) => {
          const selected = item.id === selectedId;
          return (
            <button
              key={item.id}
              aria-label={`${item.id} ${item.title}`}
              onClick={() => onSelect(item.id)}
              className="absolute -translate-x-1/2 -translate-y-1/2"
              style={{ left: `${item.marker!.x}%`, top: `${item.marker!.y}%` }}
            >
              <span
                className={`absolute inset-0 rounded-full ${MARKER_TONES[item.tone]}`}
                style={{ animation: "arc-marker-ping 1.8s ease-out infinite" }}
              />
              <span
                className={[
                  "relative flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-semibold text-background",
                  MARKER_TONES[item.tone],
                  selected ? "ring-2 ring-text" : "",
                ].join(" ")}
              >
                {item.id.slice(0, 2)}
              </span>
            </button>
          );
        })}
    </div>
  );
}
