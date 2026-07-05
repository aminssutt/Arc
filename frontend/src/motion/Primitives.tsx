"use client";

/** Reusable Framer Motion primitives — scroll reveals & staggers. */
import { useEffect, useRef, useState } from "react";
import { motion, animate, useInView, useReducedMotion } from "framer-motion";
import type { HTMLMotionProps } from "framer-motion";
import type { ReactNode } from "react";
import { fadeUp, fadeIn, staggerParent, REVEAL_VIEWPORT, EASE_MECH } from "@/motion/tokens";

type DivProps = HTMLMotionProps<"div">;

interface FadeInProps extends DivProps {
  children: ReactNode;
  /** delay in seconds */
  delay?: number;
  /** rise from below (default) or pure fade */
  variant?: "up" | "in";
}

/** Reveal on scroll into view, once. */
export function FadeIn({ children, delay = 0, variant = "up", ...rest }: FadeInProps) {
  const variants = variant === "up" ? fadeUp : fadeIn;
  return (
    <motion.div
      variants={variants}
      initial="hidden"
      whileInView="show"
      viewport={REVEAL_VIEWPORT}
      transition={delay ? { delay } : undefined}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

interface StaggerProps extends DivProps {
  children: ReactNode;
  stagger?: number;
  delay?: number;
}

/** Container that reveals its <StaggerItem> children in sequence. */
export function Stagger({ children, stagger = 0.09, delay = 0, ...rest }: StaggerProps) {
  return (
    <motion.div
      variants={staggerParent(stagger, delay)}
      initial="hidden"
      whileInView="show"
      viewport={REVEAL_VIEWPORT}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

/** A child of <Stagger>. */
export function StaggerItem({ children, ...rest }: DivProps & { children: ReactNode }) {
  return (
    <motion.div variants={fadeUp} {...rest}>
      {children}
    </motion.div>
  );
}

interface AnimatedNumberProps {
  /** target value */
  value: number;
  /** decimal places (default 0) */
  decimals?: number;
  /** animate on scroll-into-view (true) or on every value change (false) */
  onView?: boolean;
  duration?: number;
  className?: string;
}

/**
 * Count-up numerals — instrument-readout style. Animates once on scroll-in
 * (or on value change when `onView` is false, e.g. live coverage). Fully
 * static under prefers-reduced-motion.
 */
export function AnimatedNumber({
  value,
  decimals = 0,
  onView = true,
  duration = 0.9,
  className,
}: AnimatedNumberProps) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "0px 0px -10% 0px" });
  const [display, setDisplay] = useState(reduce ? value : 0);

  useEffect(() => {
    if (reduce) {
      setDisplay(value);
      return;
    }
    if (onView && !inView) return;
    const controls = animate(display, value, {
      duration,
      ease: EASE_MECH,
      onUpdate: (v) => setDisplay(v),
    });
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, inView, onView, reduce]);

  return (
    <span ref={ref} className={className}>
      {display.toFixed(decimals)}
    </span>
  );
}
