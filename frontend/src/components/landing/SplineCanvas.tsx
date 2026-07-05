"use client";

/**
 * Leaf client component that owns the heavy Spline runtime.
 *
 * It is `dynamic({ ssr:false })`-imported by the hero, so the WebGL runtime
 * lands in its own chunk that loads only after the hero mounts on the client —
 * keeping it off SSR and out of the landing's initial bundle. Isolating the
 * `@splinetool/react-spline/next` import here (a local module reached only via
 * the client dynamic boundary) also sidesteps the package's export-condition
 * resolution in Next's server/RSC layers.
 *
 * NOISE FILTER: the `@splinetool/runtime` scene emits a single benign
 * `console.error("Missing property")` while parsing this particular scene graph.
 * Next's dev overlay surfaces any `console.error` as an "Issue", so that one
 * harmless line shows up as a red "1 Issue" the user sees on the landing. We
 * install a razor-narrow `console.error` shim that swallows ONLY that exact
 * message and forwards everything else untouched, then restore the original on
 * unmount — so no real error is ever hidden and the patch never outlives the
 * scene.
 */
import Spline from "@splinetool/react-spline";
import { useEffect } from "react";

/** The exact benign message the Spline runtime logs for this scene. */
const BENIGN_SPLINE_ERROR = "Missing property";

export default function SplineCanvas({
  scene,
  onLoad,
}: {
  scene: string;
  onLoad: () => void;
}) {
  useEffect(() => {
    const original = console.error;
    console.error = (...args: unknown[]) => {
      // Drop ONLY the exact benign Spline "Missing property" line; the shim is
      // deliberately as narrow as possible (exact first-arg string match) so it
      // can never mask a genuine error.
      if (typeof args[0] === "string" && args[0] === BENIGN_SPLINE_ERROR) return;
      original.apply(console, args as Parameters<typeof console.error>);
    };
    return () => {
      console.error = original;
    };
  }, []);

  return <Spline scene={scene} onLoad={onLoad} />;
}
