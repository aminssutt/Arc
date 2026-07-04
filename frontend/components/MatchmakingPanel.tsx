import type { Responder } from "@/lib/events";

/**
 * The matchmaking beat: Arc does not page everyone — it routes to the ONE
 * qualified technician by skill + zone. This panel makes that legible.
 */
export function MatchmakingPanel({ responder: r }: { responder: Responder }) {
  const initials = r.name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div className="card" style={{ padding: 16, marginBottom: 18, borderColor: "color-mix(in srgb, var(--accent) 45%, var(--line))" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <span className="eyebrow" style={{ color: "var(--accent)" }}>Matchmaking · dispatch</span>
        <span style={{ color: "var(--dim)", fontSize: 12 }}>routed to one qualified technician — not broadcast</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
        <div
          aria-hidden
          style={{
            width: 46, height: 46, borderRadius: 12, flex: "0 0 auto",
            display: "grid", placeItems: "center", fontWeight: 800,
            color: "var(--accent)", background: "color-mix(in srgb, var(--accent) 16%, transparent)",
            border: "1px solid color-mix(in srgb, var(--accent) 40%, transparent)",
          }}
        >
          {initials}
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>
            {r.name} <span className="mono" style={{ fontSize: 13, color: "var(--dim)", fontWeight: 400 }}>· {r.employee_id}</span>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 6 }}>
            {r.tier && <span className="chip">{r.tier}</span>}
            {r.region && <span className="chip">{r.region}</span>}
            {r.out_of_zone && <span className="badge warn">out of zone — nearest available</span>}
          </div>
        </div>
        <div style={{ marginLeft: "auto", textAlign: "right", color: "var(--accent)", fontWeight: 700, fontSize: 13 }}>
          push sent ↗
        </div>
      </div>
      {r.reason && (
        <div style={{ color: "var(--dim)", fontSize: 12.5, marginTop: 12, borderTop: "1px dashed var(--line)", paddingTop: 10 }}>
          {r.reason}
        </div>
      )}
    </div>
  );
}
