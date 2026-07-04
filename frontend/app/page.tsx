"use client";

import { useMemo } from "react";
import { useIncidentStream } from "@/lib/events";
import { EventCard } from "@/components/EventCard";
import { TriggerBar } from "@/components/TriggerBar";
import { ValidationForm } from "@/components/ValidationForm";

export default function ControlRoom() {
  const { events, state } = useIncidentStream();

  // Focus on the most recent incident in the stream.
  const currentIncident = events.length ? events[events.length - 1].incident_id : null;
  const incidentEvents = useMemo(
    () => events.filter((e) => e.incident_id === currentIncident),
    [events, currentIncident],
  );

  // Human loop: show the field-validation form while awaiting, before a result.
  const awaiting = incidentEvents.find((e) => e.type === "awaiting_field_validation");
  const answered = incidentEvents.some(
    (e) => e.type === "validation_received" || e.type === "validation_result",
  );
  const failureIds = (awaiting?.data as { failure_ids?: string[] })?.failure_ids ?? [];

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: "26px 20px 80px" }}>
      <header style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 18 }}>
        <div style={{ fontWeight: 800, letterSpacing: ".5px", fontSize: 20 }}>◈ ARC</div>
        <div style={{ color: "var(--dim)" }}>Network Operations · reasoning cockpit</div>
        {currentIncident && <div style={{ marginLeft: "auto" }} className="mono">{currentIncident}</div>}
      </header>

      <div className="card" style={{ padding: 14, marginBottom: 22 }}>
        <TriggerBar state={state} onReset={() => window.location.reload()} />
      </div>

      {awaiting && !answered && currentIncident && (
        <div className="card" style={{ padding: 16, marginBottom: 22, borderColor: "color-mix(in srgb, var(--accent2) 45%, var(--line))" }}>
          <div className="eyebrow" style={{ marginBottom: 10, color: "var(--accent2)" }}>Human loop · field validation</div>
          <ValidationForm incidentId={currentIncident} failureIds={failureIds} />
        </div>
      )}

      {incidentEvents.length === 0 ? (
        <div className="card" style={{ padding: 40, textAlign: "center", color: "var(--dim)" }}>
          {state === "open"
            ? "Connected. Inject a fault to watch the agents reason, ground, and act — live."
            : "Connecting to the backend event stream…"}
          <div style={{ marginTop: 8, fontSize: 12 }}>
            Backend expected at <span className="mono">{process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}</span>
          </div>
        </div>
      ) : (
        <div>
          {incidentEvents.map((env) => (
            <EventCard key={`${env.incident_id}-${env.seq}`} env={env} />
          ))}
        </div>
      )}
    </main>
  );
}
