"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useIncidentStream, type Responder } from "@/lib/events";
import { EventCard } from "@/components/EventCard";
import { TriggerBar } from "@/components/TriggerBar";
import { ValidationForm } from "@/components/ValidationForm";
import { MatchmakingPanel } from "@/components/MatchmakingPanel";

export default function ControlRoom() {
  const { events, state } = useIncidentStream();

  const currentIncident = events.length ? events[events.length - 1].incident_id : null;
  const incidentEvents = useMemo(
    () => events.filter((e) => e.incident_id === currentIncident),
    [events, currentIncident],
  );

  const fault = incidentEvents.find((e) => e.type === "fault_detected");
  const awaiting = incidentEvents.find((e) => e.type === "awaiting_field_validation");
  const answered = incidentEvents.some(
    (e) => e.type === "validation_received" || e.type === "validation_result",
  );
  const responder = (awaiting?.data as { responders?: Responder[] })?.responders?.[0];
  const failureIds = (awaiting?.data as { failure_ids?: string[] })?.failure_ids ?? [];
  const site = (fault?.data as any)?.site;
  const family = (fault?.data as any)?.family;

  return (
    <main style={{ maxWidth: 1040, margin: "0 auto", padding: "22px 20px 90px" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <Link href="/" style={{ fontWeight: 800, letterSpacing: ".5px", fontSize: 20, textDecoration: "none", color: "var(--txt)" }}>◈ ARC</Link>
        <span style={{ color: "var(--dim)" }}>Network Operations · reasoning cockpit</span>
      </header>

      {/* Incident header — site, alarm, timestamp */}
      {fault && (
        <div className="card" style={{ padding: "14px 18px", marginBottom: 14, display: "flex", gap: 22, flexWrap: "wrap", alignItems: "center" }}>
          <div>
            <div className="eyebrow">Site</div>
            <div className="mono" style={{ fontSize: 16 }}>{site?.id}</div>
            <div style={{ color: "var(--dim)", fontSize: 12 }}>{site?.name}</div>
          </div>
          <div>
            <div className="eyebrow">Fault family</div>
            <div style={{ fontWeight: 700, textTransform: "capitalize" }}>{family}</div>
          </div>
          <div>
            <div className="eyebrow">Detected</div>
            <div className="mono" style={{ fontSize: 13 }}>{new Date(fault.ts).toLocaleTimeString()}</div>
          </div>
          <div style={{ marginLeft: "auto" }} className="mono">{currentIncident}</div>
        </div>
      )}

      <div className="card" style={{ padding: 14, marginBottom: 18 }}>
        <TriggerBar state={state} onReset={() => window.location.reload()} />
      </div>

      {/* Matchmaking beat — routed to the ONE right technician */}
      {responder && <MatchmakingPanel responder={responder} />}

      {/* Human loop — awaiting field validation */}
      {awaiting && !answered && currentIncident && (
        <div className="card" style={{ padding: 16, marginBottom: 18, borderColor: "color-mix(in srgb, var(--accent2) 45%, var(--line))" }}>
          <div className="eyebrow" style={{ marginBottom: 4, color: "var(--accent2)" }}>Awaiting field validation</div>
          <div style={{ color: "var(--dim)", fontSize: 13, marginBottom: 12 }}>The technician tests at the site — validate, or refuse with a counter-measurement and the agent pivots.</div>
          <ValidationForm incidentId={currentIncident} failureIds={failureIds} />
        </div>
      )}

      {incidentEvents.length === 0 ? (
        <div className="card" style={{ padding: 44, textAlign: "center", color: "var(--dim)" }}>
          {state === "open"
            ? "Connected. Inject a fault to watch the agents locate, diagnose, dispatch, and act — live."
            : "Connecting to the backend event stream…"}
          <div style={{ marginTop: 8, fontSize: 12 }}>
            Backend · <span className="mono">{process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}</span>
          </div>
        </div>
      ) : (
        <div>
          <div className="eyebrow" style={{ margin: "6px 0 12px" }}>Reasoning stream</div>
          {incidentEvents.map((env) => (
            <EventCard key={`${env.incident_id}-${env.seq}`} env={env} />
          ))}
        </div>
      )}
    </main>
  );
}
