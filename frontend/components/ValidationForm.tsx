"use client";

import { useState } from "react";
import { submitValidation } from "@/lib/api";

const btn: React.CSSProperties = {
  padding: "9px 14px", borderRadius: 9, border: "1px solid var(--line)", fontWeight: 700,
};

/**
 * Field-technician veracity check (human loop). In production this comes from
 * the iOS app; here it lets the NOC drive the demo: a measured busbar voltage
 * under -47 V confirms the undervoltage, a healthy float (e.g. -53.9) pivots.
 */
export function ValidationForm({ incidentId, failureIds }: { incidentId: string; failureIds: string[] }) {
  const [value, setValue] = useState("-44.8");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  async function submit(verdict: "real" | "false") {
    setBusy(true);
    try {
      await submitValidation({
        incident_id: incidentId,
        client_event_id: `ui-${Date.now()}`,
        submitted_at: new Date().toISOString(),
        validations: (failureIds.length ? failureIds : ["F1"]).map((id) => ({ failure_id: id, verdict })),
        measurements: [{ metric: "dc_voltage_v", point: "busbar", value: parseFloat(value), unit: "V" }],
      });
      setDone(`submitted: busbar ${value} V, verdict ${verdict}`);
    } catch {
      setDone("submit failed — is the backend reachable?");
    } finally { setBusy(false); }
  }

  if (done) return <div style={{ color: "var(--dim)", fontSize: 13 }}>✓ {done}</div>;

  return (
    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
      <label style={{ color: "var(--dim)", fontSize: 13 }}>
        busbar dc_voltage_v{" "}
        <input value={value} onChange={(e) => setValue(e.target.value)} inputMode="decimal"
               style={{ width: 90, padding: "7px 9px", borderRadius: 8, border: "1px solid var(--line)", background: "var(--panel2)", color: "var(--txt)" }} />
        {" "}V
      </label>
      <button style={{ ...btn, background: "color-mix(in srgb, var(--accent) 16%, var(--panel))", color: "var(--accent)", borderColor: "color-mix(in srgb, var(--accent) 45%, var(--line))" }}
              disabled={busy} onClick={() => submit("real")}>Report REAL</button>
      <button style={{ ...btn, background: "color-mix(in srgb, var(--danger) 12%, var(--panel))", color: "var(--danger)", borderColor: "color-mix(in srgb, var(--danger) 40%, var(--line))" }}
              disabled={busy} onClick={() => submit("false")}>Report FALSE</button>
      <span style={{ color: "var(--dim)", fontSize: 12 }}>≥ −47 V confirms · healthy float (−53.9) pivots</span>
    </div>
  );
}
