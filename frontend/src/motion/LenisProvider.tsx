"use client";

/**
 * LenisProvider — site-wide buttery smooth scrolling.
 *
 * Initialises a single Lenis instance behind a requestAnimationFrame loop and
 * exposes it via context so any component can request a smooth `scrollTo`.
 * A global click handler upgrades every in-page anchor (`a[href^="#"]`) to a
 * Lenis-driven scroll so nav links and CTAs share the same eased motion.
 *
 * Fully DISABLED under prefers-reduced-motion: no Lenis instance is created,
 * the rAF loop never runs, and `scrollTo` falls back to native scrolling.
 * SSR-safe: the effect only runs client-side; children render untouched on the
 * server so this can wrap the whole app in layout.tsx.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Lenis from "lenis";

type ScrollTarget = string | HTMLElement | number;
interface ScrollToOptions {
  offset?: number;
  immediate?: boolean;
}

interface LenisContextValue {
  scrollTo: (target: ScrollTarget, opts?: ScrollToOptions) => void;
}

const LenisContext = createContext<LenisContextValue | null>(null);

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  );
}

/** Fixed nav is ~56px — keep anchored sections clear of it. */
const NAV_OFFSET = -72;

export function LenisProvider({ children }: { children: ReactNode }) {
  const lenisRef = useRef<Lenis | null>(null);
  const [reduced] = useState(prefersReducedMotion);

  useEffect(() => {
    if (reduced) return; // native scroll fallback — no instance, no loop
    const lenis = new Lenis({
      // Snappy but still smooth: short settle + a lerp so the wheel tracks the
      // input quickly. Reads fast and mechanical without a hard native jump.
      duration: 0.7,
      lerp: 0.14,
      // crisp mechanic settle (fast-in, firm stop) — matches EASE_MECH
      easing: (t: number) => 1 - Math.pow(1 - t, 3),
      smoothWheel: true,
      wheelMultiplier: 1.25,
      touchMultiplier: 1.6,
    });
    lenisRef.current = lenis;

    let rafId = 0;
    const raf = (time: number) => {
      lenis.raf(time);
      rafId = requestAnimationFrame(raf);
    };
    rafId = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(rafId);
      lenis.destroy();
      lenisRef.current = null;
    };
  }, [reduced]);

  const scrollTo = useCallback((target: ScrollTarget, opts: ScrollToOptions = {}) => {
    const offset = opts.offset ?? NAV_OFFSET;
    const lenis = lenisRef.current;
    if (lenis) {
      lenis.scrollTo(target, { offset, immediate: opts.immediate });
      return;
    }
    // reduced-motion / no instance → native
    if (typeof target === "number") {
      window.scrollTo({ top: target + offset, behavior: "auto" });
      return;
    }
    const el = typeof target === "string" ? document.querySelector(target) : target;
    if (el instanceof HTMLElement) {
      const top = el.getBoundingClientRect().top + window.scrollY + offset;
      window.scrollTo({ top, behavior: "auto" });
    }
  }, []);

  // Upgrade every same-page anchor to Lenis-driven scrolling.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey) return;
      const anchor = (e.target as HTMLElement | null)?.closest?.(
        'a[href^="#"]',
      ) as HTMLAnchorElement | null;
      if (!anchor) return;
      const hash = anchor.getAttribute("href");
      if (!hash || hash === "#") return;
      const el = document.querySelector(hash);
      if (!el) return;
      e.preventDefault();
      scrollTo(el as HTMLElement);
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, [scrollTo]);

  return <LenisContext.Provider value={{ scrollTo }}>{children}</LenisContext.Provider>;
}

/** Access the shared smooth-scroll controller. */
export function useLenisScroll(): LenisContextValue {
  const ctx = useContext(LenisContext);
  // Safe no-op fallback if used outside the provider.
  return (
    ctx ?? {
      scrollTo: (target) => {
        if (typeof target === "string") {
          document.querySelector(target)?.scrollIntoView({ behavior: "smooth" });
        }
      },
    }
  );
}
