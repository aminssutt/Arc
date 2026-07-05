"use client";

import { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { fadeUp, REVEAL_VIEWPORT } from "@/motion/tokens";

// Scroll-into-view reveal wrapper for landing sections. Now driven by Framer
// Motion's shared `fadeUp` variant (was a CSS IntersectionObserver). Same props
// API — `delay` is still in milliseconds. Static under prefers-reduced-motion.
export function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();

  if (reduce) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      variants={fadeUp}
      initial="hidden"
      whileInView="show"
      viewport={REVEAL_VIEWPORT}
      transition={delay ? { delay: delay / 1000 } : undefined}
    >
      {children}
    </motion.div>
  );
}
