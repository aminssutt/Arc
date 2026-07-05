"use client";

/**
 * Shared kit for the bespoke Arc landing schematics.
 *
 * SURFACE MODEL: the landing's editorial body is a fixed LIGHT canvas (the
 * ported `.section-*` / `.card` / `SectionReveal` classes are all built on the
 * static ink/paper scale), with a dark hero and a dark live section. So the
 * on-paper schematics use the static ink/paper neutrals below — guaranteed to
 * match the canvas regardless of the global theme class — while the always-dark
 * live preview uses the `DARK` set. The tricolore accents are static and read
 * on both paper and surface.
 */
import { useEffect, useRef, useState } from "react";
import { useInView, useReducedMotion } from "framer-motion";

/** Static ink/paper neutrals — match the light editorial canvas. */
export const NEUTRAL = {
  panel: "#FFFFFF",
  panelMuted: "#F3F2EC",
  border: "#E6E5DD",
  borderStrong: "#8A897F",
  text: "#131311",
  textSoft: "#4C4B45",
  muted: "#8A897F",
} as const;

/** Fixed dark-surface neutrals — for the always-dark live section. */
export const DARK = {
  panel: "#161318",
  panelMuted: "#120F16",
  border: "#2A2730",
  text: "#F5F3F0",
  muted: "#8F8C99",
} as const;

/**
 * Sky-blue accent family — ONE hue, tonal variation (white + sky blue DA).
 * The orange/ember + tricolore palette is retired on the landing: every accent
 * key now resolves to a shade of the brand blue (`#0078AE`, the ARC logo colour)
 * / sky `#4d9dff`, plus a single neutral slate for the exception (refused/pivot)
 * path. The keys are unchanged so every schematic keeps compiling — they just
 * render blue. Chosen to stay legible on BOTH the light paper canvas and the
 * dark live-control-room surface.
 */
export const ACCENT = {
  ember: "#0078AE", // brand blue — detection / primary / CTA (was orange)
  arc: "#4d9dff", // sky blue — reasoning / agents / active highlight
  resolve: "#0ea5e9", // bright azure — validated / confirmed
  warn: "#2563eb", // blue — human loop / logistics
  danger: "#64748b", // slate — pivot / refused (neutral exception, not red)
} as const;

export type AccentKey = keyof typeof ACCENT;

/** Text colour to lay over each solid accent fill (contrast-picked). */
export const ON_ACCENT: Record<AccentKey, string> = {
  ember: "#ffffff",
  arc: "#ffffff",
  resolve: "#0b1220", // dark ink over the bright azure fill
  warn: "#ffffff",
  danger: "#ffffff",
};

/**
 * Auto-cycling active index, gated on in-view + reduced motion.
 * Returns the active index and a ref to attach to the diagram container.
 */
export function useAutoCycle(count: number, intervalMs = 1650) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: false, margin: "0px 0px -20% 0px" });
  const reduce = useReducedMotion();
  const [active, setActive] = useState(0);

  useEffect(() => {
    if (!inView || reduce || count <= 0) return;
    const id = setInterval(() => setActive((v) => (v + 1) % count), intervalMs);
    return () => clearInterval(id);
  }, [inView, reduce, count, intervalMs]);

  return { ref, active, inView, reduce };
}
