"use client";

import Image from "next/image";
import { Radio } from "lucide-react";
import type { EvidenceItem, EvidenceTone } from "@/lib/investigation";

// Site situation viewport — the equipment-shelter wireframe for the cell/power
// site (telecom reframe of the original BIM floor plan). The plain wireframe
// variants fill the panel; fault locations are shown by the interactive dot
// markers synced with the shared evidence bar, not by a pre-highlighted image.
// A light telecom framing (site chip + marker legend) keeps the view legible
// without competing with the wireframe.
const MARKER_TONES: Record<EvidenceTone, string> = {
  primary: "bg-ember",
  primarySubtle: "bg-arc",
  warning: "bg-warn",
  secondary: "bg-resolve",
};

const LEGEND: Array<{ tone: EvidenceTone; label: string }> = [
  { tone: "primary", label: "fault" },
  { tone: "primarySubtle", label: "standard match" },
  { tone: "warning", label: "field handoff" },
  { tone: "secondary", label: "resolved" },
];

export function BuildingSituation({
  evidence,
  selectedId,
  onSelect,
}: {
  evidence: EvidenceItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const markers = evidence.filter((item) => item.marker);

  return (
    <div className="relative h-full min-h-0 w-full overflow-hidden rounded-xl border border-borderSubtle bg-background">
      {/* telecom framing — site reference */}
      <div className="pointer-events-none absolute left-4 top-4 z-10 inline-flex items-center gap-2 rounded-md border border-borderSubtle bg-panel/85 px-3 py-1.5 backdrop-blur">
        <Radio className="h-3.5 w-3.5 text-[#0078AE]" />
        <span className="font-mono text-[11px] uppercase tracking-wide text-textSecondary">
          PAR-021-NORD · equipment shelter
        </span>
      </div>

      {/* unoptimized: serve the transparent PNGs verbatim — the optimizer's
          cache kept resurrecting older, background-baked variants. */}
      <Image
        src="/assets/bim-floorplan-light.png"
        alt="PAR-021-NORD equipment shelter wireframe"
        fill
        sizes="100vw"
        className="select-none object-contain p-4 dark:hidden"
        priority
        unoptimized
      />
      <Image
        src="/assets/bim-floorplan-dark.png"
        alt="PAR-021-NORD equipment shelter wireframe"
        fill
        sizes="100vw"
        className="hidden select-none object-contain p-4 dark:block"
        priority
        unoptimized
      />

      {markers.map((item) => {
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

      {/* marker legend */}
      <div className="pointer-events-none absolute bottom-4 left-4 z-10 flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-md border border-borderSubtle bg-panel/85 px-3 py-2 backdrop-blur">
        {LEGEND.map((entry) => (
          <span key={entry.tone} className="inline-flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${MARKER_TONES[entry.tone]}`} />
            <span className="font-mono text-[10px] uppercase tracking-wide text-muted">{entry.label}</span>
          </span>
        ))}
      </div>

      {markers.length === 0 && (
        <div className="pointer-events-none absolute inset-x-0 bottom-16 flex justify-center">
          <p className="rounded-md border border-dashed border-borderStrong bg-panel/70 px-3 py-1.5 text-body-sm text-muted backdrop-blur">
            No fault markers yet — launch a situation to populate the shelter.
          </p>
        </div>
      )}
    </div>
  );
}
