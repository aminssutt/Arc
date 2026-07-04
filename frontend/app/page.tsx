import Link from "next/link";
import Spline from "@splinetool/react-spline/next";

const FEATURES = [
  {
    k: "01",
    title: "Matchmaking dispatch",
    body: "Routed to the one right technician by skill and location — a senior power specialist in the site's zone. Not broadcast to everyone.",
  },
  {
    k: "02",
    title: "Physical validation loop",
    body: "The technician tests for real and confirms — or refuses with a counter-measurement, and the agent pivots and re-diagnoses live.",
  },
  {
    k: "03",
    title: "Document-grounded reasoning",
    body: "Every cause and every step cites the carrier's own technical docs — clickable, down to the exact page. No hallucinated fixes.",
  },
];

export default function Landing() {
  return (
    <main>
      {/* Hero — interactive Spline scene behind the thesis line */}
      <section style={{ position: "relative", height: "100vh", minHeight: 640, overflow: "hidden" }}>
        <div style={{ position: "absolute", inset: 0 }}>
          <Spline scene="https://prod.spline.design/Th8T7W2tHlzmSvb1/scene.splinecode" style={{ width: "100%", height: "100%" }} />
        </div>

        {/* overlay: forced-dark (the 3D scene is dark). pointer-events pass
            through to the scene except nav + CTAs. */}
        <div style={{ position: "absolute", inset: 0, pointerEvents: "none", display: "flex", flexDirection: "column",
          background: "linear-gradient(180deg, rgba(6,10,16,.72) 0%, rgba(6,10,16,.18) 26%, transparent 46%, rgba(6,10,16,.55) 74%, rgba(6,10,16,.9) 100%)" }}>
          <nav style={{ pointerEvents: "auto", display: "flex", alignItems: "center", gap: 12, padding: "22px 28px", color: "#eaf1f9" }}>
            <span style={{ fontWeight: 800, letterSpacing: ".5px", fontSize: 20 }}>◈ ARC</span>
            <span className="eyebrow" style={{ opacity: .8, color: "#9fb4cc" }}>Network operations agent · Vultr</span>
            <Link href="/control-room" className="cta" style={{ marginLeft: "auto", color: "#eaf1f9", background: "rgba(20,30,44,.55)" }}>See it live →</Link>
          </nav>

          <div style={{ marginTop: "auto", padding: "0 28px 8vh", maxWidth: 840 }}>
            <p className="eyebrow" style={{ color: "#3fe0a0", marginBottom: 14 }}>Telecom site fault → resolved, cited action</p>
            <h1 style={{ fontSize: "clamp(30px, 5.2vw, 60px)", lineHeight: 1.04, margin: 0, fontWeight: 800, letterSpacing: "-.02em",
              color: "#f4f8fd", textShadow: "0 2px 30px rgba(0,0,0,.55)" }}>
              The instinct of your best NOC engineer, on every fault, across every site.
            </h1>
            <p style={{ fontSize: "clamp(15px, 1.9vw, 19px)", color: "rgba(214,226,242,.92)", maxWidth: 640, marginTop: 18, textShadow: "0 1px 18px rgba(0,0,0,.5)" }}>
              Arc drives a telecom site fault to a resolved, cited action — a team of agents, not a chatbot. It dispatches to the right technician, closes the loop with the real world, and grounds every decision in your own docs.
            </p>
            <div style={{ pointerEvents: "auto", display: "flex", gap: 12, marginTop: 26, flexWrap: "wrap" }}>
              <Link href="/control-room" className="cta cta-solid">Run the live demo →</Link>
              <span style={{ alignSelf: "center", color: "rgba(214,226,242,.75)", fontSize: 13 }}>drag the scene to look around</span>
            </div>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section style={{ maxWidth: 880, margin: "0 auto", padding: "84px 28px 40px" }}>
        <p className="eyebrow" style={{ marginBottom: 16 }}>The problem</p>
        <p style={{ fontSize: "clamp(19px, 2.6vw, 27px)", lineHeight: 1.35, fontWeight: 500, textWrap: "balance", margin: 0 }}>
          A carrier runs tens of thousands of cell sites. When one loses power, the clock starts — SLA penalties, thousands of subscribers going dark. And the NOC engineers who read a fault instantly are retiring.
        </p>
      </section>

      {/* Three hero features */}
      <section style={{ maxWidth: 1040, margin: "0 auto", padding: "24px 28px 40px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
          {FEATURES.map((f) => (
            <div key={f.k} className="card" style={{ padding: "22px 20px" }}>
              <div className="mono" style={{ color: "var(--accent2)", fontSize: 13 }}>{f.k}</div>
              <h3 style={{ margin: "10px 0 8px", fontSize: 18 }}>{f.title}</h3>
              <p style={{ margin: 0, color: "var(--dim)", fontSize: 14, lineHeight: 1.5 }}>{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Close */}
      <section style={{ maxWidth: 880, margin: "0 auto", padding: "48px 28px 100px", textAlign: "center" }}>
        <h2 style={{ fontSize: "clamp(22px, 3.4vw, 34px)", fontWeight: 800, textWrap: "balance", margin: 0 }}>
          Not retrieve-then-answer. A real agent — grounded, telecom-native, on Vultr.
        </h2>
        <div style={{ marginTop: 24 }}>
          <Link href="/control-room" className="cta cta-solid">See it live →</Link>
        </div>
        <p style={{ color: "var(--dim)", fontSize: 12, marginTop: 40 }}>Arc · demo on the live event stream · site PAR-021-NORD</p>
      </section>
    </main>
  );
}
