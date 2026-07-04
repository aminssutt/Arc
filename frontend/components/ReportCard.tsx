import type { ActionReport } from "@/lib/events";
import { CitationTrail } from "./CitationTrail";

const usd = (n: number, ccy: string) =>
  `${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${ccy}`;

function Row({ k, v, accent }: { k: string; v: React.ReactNode; accent?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, padding: "6px 0", borderBottom: "1px dashed var(--line)" }}>
      <span style={{ color: "var(--dim)" }}>{k}</span>
      <span style={{ textAlign: "right", color: accent }}>{v}</span>
    </div>
  );
}

/** The prioritized action report — the deliverable, with the citation drill-down. */
export function ReportCard({ report }: { report: ActionReport }) {
  const c = report.cost;
  const inv = report.inventory;
  const disp = report.dispatch;
  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div className="card" style={{ padding: 16, gridColumn: "1 / -1" }}>
          <div className="eyebrow" style={{ marginBottom: 8 }}>Diagnosis</div>
          <div style={{ fontSize: 16, fontWeight: 600 }}>{report.diagnosis.cause}</div>
          <div style={{ marginTop: 8 }}>
            <Row k="Confidence" v={<span className="mono">{report.diagnosis.confidence.toFixed(2)}</span>} />
          </div>
        </div>

        <div className="card" style={{ padding: 16 }}>
          <div className="eyebrow" style={{ marginBottom: 8 }}>Prioritized actions</div>
          {report.actions.map((a, i) => (
            <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "8px 0", borderBottom: "1px dashed var(--line)" }}>
              <span className="chip" style={{ fontWeight: 800, color: a.priority === "P1" ? "var(--danger)" : "var(--warn)" }}>{a.priority}</span>
              <div>
                <div>{a.action}</div>
                {a.owner && <div style={{ color: "var(--dim)", fontSize: 12 }}>owner · <span className="mono">{a.owner}</span></div>}
              </div>
            </div>
          ))}
        </div>

        <div className="card" style={{ padding: 16 }}>
          <div className="eyebrow" style={{ marginBottom: 8 }}>Cost impact</div>
          <div style={{ fontSize: 12, color: "var(--dim)" }}>Cost avoided</div>
          <div style={{ fontSize: 26, fontWeight: 800, color: "var(--accent)" }} className="mono">{usd(c.avoided, c.currency)}</div>
          <div style={{ marginTop: 6 }}>
            <Row k="Intervention" v={<span className="mono">{usd(c.intervention, c.currency)}</span>} />
          </div>
        </div>

        {inv && (
          <div className="card" style={{ padding: 16 }}>
            <div className="eyebrow" style={{ marginBottom: 8 }}>Part · inventory</div>
            <Row k="Part" v={<span className="mono">{inv.part_no || "—"}</span>} />
            <Row k="In stock" v={inv.in_stock ? `yes · ${inv.qty_available}` : "no"} accent={inv.in_stock ? "var(--accent)" : "var(--danger)"} />
            <Row k="Warehouse" v={<span className="mono">{inv.location || "—"}</span>} />
          </div>
        )}

        {disp && (
          <div className="card" style={{ padding: 16 }}>
            <div className="eyebrow" style={{ marginBottom: 8 }}>Crew · dispatch</div>
            <Row k="Crew" v={<span className="mono">{disp.crew || "—"}</span>} />
            <Row k="Status" v={disp.conflict ? disp.conflict : "booked"} accent={disp.conflict ? "var(--warn)" : "var(--accent)"} />
          </div>
        )}
      </div>

      {report.honesty_notes && report.honesty_notes.length > 0 && (
        <div className="card" style={{ padding: "12px 16px", borderColor: "color-mix(in srgb, var(--warn) 40%, var(--line))" }}>
          <div className="eyebrow" style={{ marginBottom: 6, color: "var(--warn)" }}>Honesty notes</div>
          {report.honesty_notes.map((n, i) => (
            <div key={i} style={{ color: "var(--dim)", fontSize: 13 }}>• {n}</div>
          ))}
        </div>
      )}

      <div className="card" style={{ padding: 16 }}>
        <div className="eyebrow" style={{ marginBottom: 10 }}>
          Sources · evidence trail <span style={{ textTransform: "none", letterSpacing: 0, color: "var(--dim)" }}>— click a source to open the exact document</span>
        </div>
        <CitationTrail citations={report.citations} />
      </div>
    </div>
  );
}
