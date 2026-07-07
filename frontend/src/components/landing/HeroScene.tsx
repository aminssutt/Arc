"use client";

/**
 * Arc hero — a full-height split on a LIGHT canvas (white + sky-blue DA).
 *
 * LEFT: the real ARC wordmark + eyebrow + a tight telecom headline (with a
 * sky-blue emphasis fragment) + one short subline + a sky-blue CTA → the control
 * room + a "see how it works" anchor. RIGHT: a native, full-bleed Spline robot,
 * dropped into a subtle sky-tinted glass container so it reads on white.
 *
 * Respects prefers-reduced-motion: a static sky-blue poster replaces the live
 * scene, so the heavy Spline runtime is never even downloaded. The scene is
 * loaded via `next/dynamic({ ssr:false })` so it stays out of SSR and off the
 * initial bundle.
 */
import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { motion, useMotionValue, useReducedMotion, useSpring } from "framer-motion";
import type { MotionProps } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { EASE_MECH } from "@/motion/tokens";

// The heavy WebGL runtime lives in a local leaf component, loaded only on the
// client after mount — its own chunk, off SSR and off the initial bundle.
const SplineCanvas = dynamic(() => import("./SplineCanvas"), { ssr: false });

// Client-provided PROD scene (reused verbatim from the ECU hero).
const SPLINE_SCENE = "https://prod.spline.design/3rRIg77tfThLkLW7/scene.splinecode";

// Sky-blue CTA — replaces the retired ember `.btn-signal`, styled locally so we
// don't touch globals.css.
const BTN_SKY =
  "inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#0078AE] text-white text-sm font-semibold " +
  "transition-all duration-300 ease-expo hover:bg-[#0a6ea0] hover:shadow-[0_0_28px_-6px_rgba(0,120,174,0.65)] " +
  "disabled:opacity-40 disabled:cursor-not-allowed";

/** Subtle spinner shown until the scene reports loaded (no layout shift). */
function SplineSkeleton() {
  return (
    <div className="absolute inset-0 z-[1] grid place-items-center">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_45%,rgba(0,120,174,0.10),transparent_62%)]" />
      <div className="relative flex flex-col items-center gap-3">
        <span className="h-9 w-9 rounded-full border-2 border-[#0078AE]/25 border-t-[#0078AE] animate-wheel-spin" />
        <span className="font-mono text-[10px] uppercase tracking-label text-ink-faint">
          booting scene
        </span>
      </div>
    </div>
  );
}

/** Static poster used under reduced-motion (no live 3D, no runtime download). */
function SplinePoster() {
  return (
    <div className="absolute inset-0 grid place-items-center">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_45%,rgba(77,157,255,0.14),transparent_60%)]" />
      <div className="absolute inset-0 grid-lines opacity-60" />
      <div className="relative h-40 w-40 rounded-full border border-[#0078AE]/25 bg-white/70 grid place-items-center shadow-[0_20px_60px_-24px_rgba(0,120,174,0.4)]">
        <span className="font-mono text-[10px] uppercase tracking-label text-[#0078AE]">
          arc · noc
        </span>
      </div>
    </div>
  );
}

/** Size of the pointer-tracked sky spotlight. */
const GLOW = 560;
const GLOW_HALF = GLOW / 2;

const NAV_LINKS = [
  { href: "#problem", label: "Problem" },
  { href: "#method", label: "The agents" },
  { href: "#matching", label: "Matching" },
  { href: "#pipeline", label: "Pipeline" },
  { href: "#live", label: "Control room" },
];

export default function HeroScene() {
  const reduced = useReducedMotion();
  const [loaded, setLoaded] = useState(false);
  // Wrapper around the Spline canvas — see the wheel effect below.
  const splineWrapRef = useRef<HTMLDivElement>(null);

  // ── pointer-tracked sky spotlight ────────────────────────────────────────
  const gx = useMotionValue(-9999);
  const gy = useMotionValue(-9999);
  const glowX = useSpring(gx, { stiffness: 140, damping: 22, mass: 0.5 });
  const glowY = useSpring(gy, { stiffness: 140, damping: 22, mass: 0.5 });
  const onPointerMove = (e: ReactPointerEvent<HTMLElement>) => {
    if (reduced) return;
    const r = e.currentTarget.getBoundingClientRect();
    gx.set(e.clientX - r.left - GLOW_HALF);
    gy.set(e.clientY - r.top - GLOW_HALF);
  };

  // macOS trackpad/scroll momentum over the robot was being consumed by the
  // Spline runtime's own canvas `wheel` listener, orbiting the camera until the
  // robot drifted out of frame. Swallow wheel in the capture phase on the
  // wrapper so it never reaches the canvas: the page scrolls normally (we never
  // preventDefault) and pointer tracking is untouched, so the robot still
  // follows the cursor. The same hijack happens on touch: a vertical swipe over
  // the canvas is otherwise consumed as a camera orbit, trapping the page scroll.
  // Swallow `touchmove` in capture too (never preventDefault — `touch-action:
  // pan-y` on the wrapper lets the browser own the vertical scroll), so a finger
  // drag scrolls the page while the canvas stops eating it.
  useEffect(() => {
    const el = splineWrapRef.current;
    if (!el) return;
    const swallow = (e: Event) => e.stopPropagation();
    el.addEventListener("wheel", swallow, { capture: true });
    el.addEventListener("touchmove", swallow, { capture: true, passive: true });
    return () => {
      el.removeEventListener("wheel", swallow, { capture: true });
      el.removeEventListener("touchmove", swallow, { capture: true });
    };
  }, []);

  // Entrance reveals — disabled under reduced motion (no offset, no delay).
  const reveal = (y: number, delay = 0): MotionProps =>
    reduced
      ? { initial: false }
      : {
          initial: { opacity: 0, y },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.75, ease: EASE_MECH, delay },
        };

  return (
    <section
      onPointerMove={onPointerMove}
      className="relative isolate bg-paper text-ink min-h-[100svh] flex flex-col overflow-hidden"
    >
      {/* atmosphere: soft sky-blue gradient mesh + engineering grid */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_74%_34%,rgba(0,120,174,0.12),transparent_55%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_22%_82%,rgba(77,157,255,0.12),transparent_52%)]" />
      </div>
      {!reduced && (
        <motion.div
          aria-hidden
          className="absolute top-0 left-0 z-[1] rounded-full blur-3xl pointer-events-none will-change-transform"
          style={{
            x: glowX,
            y: glowY,
            height: GLOW,
            width: GLOW,
            background:
              "radial-gradient(circle, rgba(0,120,174,0.16) 0%, rgba(77,157,255,0.07) 38%, transparent 68%)",
          }}
        />
      )}
      <div className="absolute inset-0 z-[1] grid-lines opacity-70 pointer-events-none" />
      <div className="absolute inset-x-0 bottom-0 h-28 z-[1] bg-gradient-to-t from-paper to-transparent pointer-events-none" />

      {/* ── nav (transparent, over the light hero) ──────────────────────── */}
      <nav className="relative z-20 w-full max-w-content mx-auto px-6 sm:px-10 py-5 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5" aria-label="Arc home">
          <Image
            src="/assets/arc-logo.svg"
            alt="Arc"
            width={142}
            height={24}
            priority
            className="h-[22px] w-auto"
          />
        </Link>
        <div className="flex items-center gap-6">
          <div className="hidden md:flex items-center gap-6">
            {NAV_LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="link-underline font-mono text-[12px] uppercase tracking-[0.14em] text-ink-soft hover:text-ink transition-colors"
              >
                {l.label}
              </a>
            ))}
          </div>
          <Link
            href="/login"
            className="inline-flex h-8 items-center rounded-md border border-ink-line px-3.5 font-mono text-[12px] uppercase tracking-[0.12em] text-ink-soft hover:border-[#0078AE]/50 hover:text-ink transition-colors"
          >
            Sign in
          </Link>
        </div>
      </nav>

      {/* ── hero body ───────────────────────────────────────────────────── */}
      <div className="relative z-10 flex-1 w-full max-w-content mx-auto px-6 sm:px-10 py-10 lg:py-0 grid lg:grid-cols-[0.9fr_1.1fr] gap-10 lg:gap-16 items-center">
        {/* content — LEFT */}
        <div className="max-w-xl">
          <motion.div {...reveal(16)} className="flex items-center gap-3">
            <span className="inline-flex h-2 w-2 rounded-full bg-[#0078AE] animate-signal-pulse" />
            <span className="font-mono text-[11px] uppercase tracking-label text-ink-soft">
              Network operations agents · Vultr
            </span>
          </motion.div>

          <motion.h1
            {...reveal(24, 0.08)}
            className="mt-6 font-display font-semibold text-ink leading-[0.98] tracking-[-0.03em] text-[clamp(2.3rem,5.2vw,4rem)] text-balance"
          >
            The instinct of your best NOC engineer,{" "}
            <span className="text-[#0078AE]">on every site.</span>
          </motion.h1>

          <motion.p
            {...reveal(18, 0.2)}
            className="mt-6 text-base sm:text-lg text-ink-soft leading-relaxed max-w-md"
          >
            Multi-agent diagnosis of every fault against your own docs — cited —
            then a field tech in the loop before dispatch.
          </motion.p>

          <motion.div {...reveal(14, 0.32)} className="mt-9 flex flex-wrap items-center gap-3">
            <Link href="/login?next=/monitor" className={`${BTN_SKY} group`}>
              <span className="inline-flex h-1.5 w-1.5 rounded-full bg-white" />
              Launch the control room
              <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" />
            </Link>
            <a href="#method" className="btn-secondary">
              See how it works
            </a>
          </motion.div>

          <motion.div
            {...(reduced
              ? { initial: false }
              : { initial: { opacity: 0 }, animate: { opacity: 1 }, transition: { duration: 1, delay: 0.6 } })}
            className="mt-12 flex flex-col gap-1.5 font-mono text-[11px] text-ink-faint"
          >
            <span>6 agents · 1 human veto · reasoning on Vultr serverless inference</span>
            <span>grounded on your carrier&apos;s own docs — every claim cited</span>
          </motion.div>
        </div>

        {/* Spline robot in a subtle sky-tinted container — RIGHT */}
        <motion.div
          {...(reduced
            ? { initial: false }
            : { initial: { opacity: 0, scale: 0.98 }, animate: { opacity: 1, scale: 1 }, transition: { duration: 1, ease: EASE_MECH, delay: 0.18 } })}
          className="relative w-full"
        >
          <div
            aria-hidden
            className="absolute -inset-8 z-0 bg-[radial-gradient(circle_at_55%_45%,rgba(0,120,174,0.12),transparent_62%)] blur-2xl pointer-events-none"
          />
          <div className="relative z-[1]">
            <div ref={splineWrapRef} className="spline-hero relative h-[320px] touch-pan-y sm:h-[420px] lg:h-[500px] xl:h-[540px]">
              {reduced ? (
                <SplinePoster />
              ) : (
                <>
                  {!loaded && <SplineSkeleton />}
                  <motion.div
                    className="spline-stage"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: loaded ? 1 : 0 }}
                    transition={{ duration: 0.6, ease: EASE_MECH }}
                  >
                    <SplineCanvas scene={SPLINE_SCENE} onLoad={() => setLoaded(true)} />
                  </motion.div>
                </>
              )}
            </div>
          </div>
          <p className="mt-3 font-mono text-[10px] uppercase tracking-label text-ink-faint text-center">
            {reduced ? "live scene paused · reduced motion" : "live scene · follows your cursor"}
          </p>
        </motion.div>
      </div>

      {/* scroll hint (skipped under reduced motion) */}
      {!reduced && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 1 }}
          className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 hidden sm:flex flex-col items-center gap-2"
        >
          <span className="font-mono text-[10px] uppercase tracking-label text-ink-faint">scroll</span>
          <span className="h-8 w-[1px] bg-gradient-to-b from-[#0078AE]/70 to-transparent" />
        </motion.div>
      )}
    </section>
  );
}
