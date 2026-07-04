import type { ActionReport, Cause, Envelope, Responder } from "@/lib/events";
import { CitationTrail } from "./CitationTrail";
import { ReportCard } from "./ReportCard";

const LABELS: Record<string, string> = {
  fault_detected: "Fault detected",
  phase_started: "Phase started",
  agent_started: "Agent started",
  agent_completed: "Agent completed",
  retrieval_performed: "Retrieval",
  diagnostic_ready: "Diagnostic ready",
  doc_requested: "Missing document",
  push_sent: "Push sent to technician",
  awaiting_field_validation: "Awaiting field validation",
  validation_received: "Validation received",
  validation_result: "Validation result",
  remediation_ready: "Remediation ready",
  action_report_ready: "Action report",
  incident_resolved: "Incident resolved",
};

const dotColor = (t: string) =>
  t === "action_report_ready" || t === "incident_resolved" ? "var(--accent)"
  : t === "diagnostic_ready" || t === "awaiting_field_validation" ? "var(--accent2)"
  : t === "doc_requested" ? "var(--warn)"
  : "var(--dim)";

export function EventCard({ env }: { env: Envelope }) {
  const t = env.type;
  const d = env.data as Record<string, any>;
  return (
    <div style={{ display: "flex", gap: 14 }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <span style={{ width: 10, height: 10, borderRadius: 999, background: dotColor(t), marginTop: 6, boxShadow: `0 0 0 4px color-mix(in srgb, ${dotColor(t)} 18%, transparent)` }} />
        <span style={{ flex: 1, width: 2, background: "var(--line)", marginTop: 4 }} />
      </div>
      <div className="card" style={{ padding: "12px 16px", flex: 1, marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span className="mono" style={{ fontSize: 12, color: "var(--dim)" }}>#{env.seq}</span>
          <strong>{LABELS[t] || t}</strong>
          {t === "agent_completed" && <span className="chip">{d.agent}</span>}
          {t === "phase_started" && <span className="chip">phase {d.phase}{d.cause === "pivot" ? " · PIVOT" : ""}</span>}
          {t === "validation_result" && (
            <span className={`badge ${d.result === "pivot" ? "pivot" : "ok"}`}>{d.result}</span>
          )}
        </div>
        <div style={{ marginTop: 8 }}>{renderBody(t, d)}</div>
      </div>
    </div>
  );
}

function renderBody(t: string, d: Record<string, any>) {
  switch (t) {
    case "fault_detected":
      return (
        <div style={{ color: "var(--dim)", fontSize: 13 }}>
          <span className="mono">{d.site?.id}</span> · {d.site?.name} · family <strong style={{ color: "var(--txt)" }}>{d.family}</strong>
          {d.failures?.length ? <> · {d.failures.length} failure(s)</> : null}
        </div>
      );
    case "agent_completed":
      return (
        <div style={{ color: "var(--dim)", fontSize: 13 }}>
          {d.status !== "ok" && <span className="badge warn" style={{ marginRight: 8 }}>{d.status}</span>}
          {d.summary} {typeof d.duration_ms === "number" && <span className="mono">· {d.duration_ms}ms</span>}
        </div>
      );
    case "retrieval_performed":
      return (
        <div style={{ color: "var(--dim)", fontSize: 13 }}>
          pass {d.pass} · <span className="mono">{d.query}</span> → {d.results?.length ?? 0} hits
        </div>
      );
    case "diagnostic_ready": {
      const causes = (d.causes || []) as Cause[];
      const top = causes[0];
      return (
        <div>
          {top && (
            <div>
              <div style={{ fontWeight: 600 }}>{top.cause}</div>
              <div style={{ color: "var(--dim)", fontSize: 12, margin: "2px 0 8px" }}>
                confidence <span className="mono">{top.confidence?.toFixed?.(2) ?? top.confidence}</span>
                {d.correlation?.equipment?.length ? <> · equipment <span className="mono">{d.correlation.equipment.join(", ")}</span></> : null}
              </div>
              {top.citations?.length ? <CitationTrail citations={top.citations} /> : null}
            </div>
          )}
        </div>
      );
    }
    case "awaiting_field_validation": {
      const responders = (d.responders || []) as Responder[];
      const r = responders[0];
      return (
        <div style={{ color: "var(--dim)", fontSize: 13 }}>
          {r ? (
            <div>
              Notify <strong style={{ color: "var(--txt)" }} className="mono">{r.employee_id}</strong> {r.name}
              {r.tier ? <> · {r.tier}</> : null}{r.region ? <> · {r.region}</> : null}
              {r.out_of_zone ? <span className="badge warn" style={{ marginLeft: 8 }}>out of zone</span> : null}
              {r.reason ? <div style={{ marginTop: 4, opacity: 0.8 }}>{r.reason}</div> : null}
            </div>
          ) : (
            <>awaiting technician measurement…</>
          )}
        </div>
      );
    }
    case "validation_result":
      return <div style={{ color: "var(--dim)", fontSize: 13 }}>{d.rationale}</div>;
    case "doc_requested":
      return <div style={{ color: "var(--warn)", fontSize: 13 }}>{d.description}</div>;
    case "incident_resolved":
      return <div style={{ color: "var(--dim)", fontSize: 13 }}>{d.summary} · <strong style={{ color: "var(--txt)" }}>{d.outcome}</strong></div>;
    case "action_report_ready":
      return <div style={{ marginTop: 6 }}><ReportCard report={d.report as ActionReport} /></div>;
    default:
      return null;
  }
}
