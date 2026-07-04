import type { Citation } from "@/lib/events";

/** Evidence trail — every claim resolves to its exact source, clickable. */
export function CitationTrail({ citations }: { citations: Citation[] }) {
  if (!citations?.length) return null;
  return (
    <div style={{ display: "grid", gap: 8 }}>
      {citations.map((c, i) => (
        <CitationRow key={`${c.doc_id}-${i}`} c={c} />
      ))}
    </div>
  );
}

function CitationRow({ c }: { c: Citation }) {
  const anchor = c.section || c.claim || "";
  const loc = [anchor, c.page ? `p.${c.page}` : null].filter(Boolean).join(" · ");
  const inner = (
    <>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <span className="chip">{c.doc_id}</span>
        <span style={{ fontWeight: 600 }}>{c.title || c.doc_id}</span>
        {c.publisher && <span style={{ color: "var(--dim)", fontSize: 12 }}>{c.publisher}</span>}
        {c.page ? (
          <span
            style={{
              fontFamily: "ui-monospace, monospace", fontSize: 11,
              color: "var(--accent2)", padding: "1px 7px", borderRadius: 6,
              background: "color-mix(in srgb, var(--accent2) 16%, transparent)",
              border: "1px solid color-mix(in srgb, var(--accent2) 35%, transparent)",
            }}
          >
            page {c.page}
          </span>
        ) : null}
        <span style={{ marginLeft: "auto", fontSize: 12, fontWeight: 700, color: c.openable ? "var(--accent2)" : "var(--dim)" }}>
          {c.openable ? "open ↗" : "cited · not fetchable"}
        </span>
      </div>
      {loc && <div style={{ color: "var(--dim)", fontSize: 12.5, marginTop: 6 }}>{loc}</div>}
      {c.snippet && (
        <div style={{ marginTop: 6, opacity: 0.85, fontStyle: "italic", borderLeft: "2px solid var(--line)", paddingLeft: 10 }}>
          &ldquo;{c.snippet}&rdquo;
        </div>
      )}
    </>
  );

  const boxStyle: React.CSSProperties = {
    display: "block", textDecoration: "none", color: "inherit",
    border: "1px solid var(--line)", borderRadius: 10, padding: "12px 14px",
    background: "var(--panel2)",
  };

  return c.openable && c.open_url ? (
    <a href={c.open_url} target="_blank" rel="noopener noreferrer" style={boxStyle}
       title={`Open ${c.title || c.doc_id}${c.page ? ` at page ${c.page}` : ""}`}>
      {inner}
    </a>
  ) : (
    <div style={{ ...boxStyle, opacity: 0.55 }} title="Source cited but not fetchable (link-only)">
      {inner}
    </div>
  );
}
