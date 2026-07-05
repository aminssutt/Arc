"use client";

/** A numbered narrative section wrapper (industrial: 01 / eyebrow / title). */
import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { fadeUp, staggerParent, REVEAL_VIEWPORT } from "@/motion/tokens";

interface SectionRevealProps {
  /** e.g. "01" */
  index: string;
  eyebrow: string;
  title: ReactNode;
  intro?: ReactNode;
  children?: ReactNode;
  id?: string;
  /** render on a dark surface */
  dark?: boolean;
}

export function SectionReveal({
  index,
  eyebrow,
  title,
  intro,
  children,
  id,
  dark = false,
}: SectionRevealProps) {
  return (
    <section
      id={id}
      className={`scroll-mt-24 py-20 sm:py-28 ${dark ? "text-paper" : "text-ink"}`}
    >
      <motion.div
        variants={staggerParent(0.1)}
        initial="hidden"
        whileInView="show"
        viewport={REVEAL_VIEWPORT}
        className="max-w-content mx-auto px-6 sm:px-10"
      >
        <motion.div variants={fadeUp} className="flex items-baseline gap-4">
          <span className={`font-mono text-[13px] ${dark ? "text-[#4d9dff]" : "text-[#0078AE]"}`}>
            {index}
          </span>
          <span
            className={`font-mono text-[11px] uppercase tracking-label ${
              dark ? "text-paper/45" : "text-ink-faint"
            }`}
          >
            {eyebrow}
          </span>
        </motion.div>

        <motion.h2
          variants={fadeUp}
          className={`mt-5 font-display tracking-[-0.005em] text-[2rem] sm:text-[2.8rem] leading-[1.08] max-w-3xl ${
            dark ? "text-paper" : "text-ink"
          }`}
        >
          {title}
        </motion.h2>

        {intro && (
          <motion.div
            variants={fadeUp}
            className={`mt-6 lead max-w-prose ${dark ? "text-paper/70" : "text-ink-soft"}`}
          >
            {intro}
          </motion.div>
        )}

        {children && <motion.div variants={fadeUp} className="mt-12">{children}</motion.div>}
      </motion.div>
    </section>
  );
}
