/** Shared motion tokens — one vocabulary for the whole site (ported from ECU). */
import type { Variants, Transition } from "framer-motion";

/** ARIA-style refined easing: fast out, gentle settle. */
export const EASE_EXPO = [0.16, 1, 0.3, 1] as const;
export const EASE_SOFT = [0.4, 0, 0.2, 1] as const;
/** Mechanic signature: crisp fast-in, firm settle — controlled, never bouncy. */
export const EASE_MECH = [0.22, 0.61, 0.18, 1] as const;

export const DURATION = {
  fast: 0.35,
  base: 0.55,
  slow: 0.9,
} as const;

export const springSoft: Transition = {
  type: "spring",
  stiffness: 220,
  damping: 30,
  mass: 0.9,
};

/** Fade + rise, the default reveal — crisp mechanic settle. */
export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 22 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.base, ease: EASE_MECH },
  },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: DURATION.base, ease: EASE_SOFT } },
};

/** Reveal with a subtle scale-settle — for framed/graphic blocks (diagrams, tiles). */
export const revealScale: Variants = {
  hidden: { opacity: 0, y: 16, scale: 0.985 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: DURATION.base, ease: EASE_MECH },
  },
};

/** Precise left-side wipe — for spec tags / eyebrow rows. */
export const wipeRight: Variants = {
  hidden: { opacity: 0, x: -14 },
  show: { opacity: 1, x: 0, transition: { duration: DURATION.fast, ease: EASE_MECH } },
};

/** Shared hover/tap micro-interaction for interactive tiles (no bounce). */
export const hoverLift = {
  whileHover: { y: -3, transition: { duration: 0.2, ease: EASE_MECH } },
  whileTap: { y: -1, scale: 0.995 },
} as const;

/** Parent that staggers its children. */
export const staggerParent = (stagger = 0.09, delay = 0): Variants => ({
  hidden: {},
  show: {
    transition: { staggerChildren: stagger, delayChildren: delay },
  },
});

/** Viewport config shared by scroll-reveal wrappers. */
export const REVEAL_VIEWPORT = { once: true, margin: "0px 0px -12% 0px" } as const;

/** Tricolore brand accents — the motion layer's canonical hex values. */
export const TRICOLORE = {
  ember: "#0078AE",
  arc: "#4d9dff",
  resolve: "#3ecf8e",
} as const;
