"use client";

import { useState } from "react";
import { injectFault, resetDemo } from "@/lib/api";
import type { ConnState } from "@/lib/events";

const btn: React.CSSProperties = {
  padding: "9px 14px", borderRadius: 9, border: "1px solid var(--line)",
  background: "var(--panel)", color: "var(--txt)", fontWeight: 600,
};

export function TriggerBar({ state, onReset }: { state: ConnState; onReset: () => void }) {
  const [busy, setBusy] = useState<string | null>(null);

  async function run(kind: "confirm" | "pivot" | "reset") {
    setBusy(kind);
    try {
      if (kind === "reset") { await resetDemo(); onReset(); }
      else await injectFault(kind);
    } catch { /* surfaced via the stream / connection state */ }
    finally { setBusy(null); }
  }

  const dot = state === "open" ? "var(--accent)" : state === "connecting" ? "var(--warn)" : "var(--danger)";

  return (
    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
      <button style={{ ...btn, borderColor: "color-mix(in srgb, var(--accent) 45%, var(--line))" }}
              disabled={!!busy} onClick={() => run("confirm")}>
        {busy === "confirm" ? "injecting…" : "▶ Inject — Confirm run"}
      </button>
      <button style={{ ...btn, borderColor: "color-mix(in srgb, var(--danger) 45%, var(--line))" }}
              disabled={!!busy} onClick={() => run("pivot")}>
        {busy === "pivot" ? "injecting…" : "▶ Inject — Pivot run"}
      </button>
      <button style={btn} disabled={!!busy} onClick={() => run("reset")}>Reset</button>
      <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, color: "var(--dim)", fontSize: 13 }}>
        <span style={{ width: 9, height: 9, borderRadius: 999, background: dot }} />
        stream {state}
      </span>
      <ThemeToggle />
    </div>
  );
}

function ThemeToggle() {
  function toggle() {
    const root = document.documentElement;
    const cur = root.getAttribute("data-theme");
    const next = cur === "light" ? "dark" : cur === "dark" ? "light"
      : (window.matchMedia("(prefers-color-scheme: dark)").matches ? "light" : "dark");
    root.setAttribute("data-theme", next);
  }
  return <button style={btn} onClick={toggle} title="Toggle theme" aria-label="Toggle theme">◐</button>;
}
