# VALIDATION LANE — "Does Arc work in a real-case scenario?"

> **Status: COMPLETE.** Self-contained validation lane for Arc.
> This lane does NOT overlap the build (roadmap/board, agents, backend, apps — team-owned).
> Docs only: no build code lives here. The eval runner (when written) talks to the
> backend over HTTP and lives in `/backend` (or here), never in `/data` or `/docs`.

## 📦 What lives here and who owns what

| File | Owner | What they do with it |
|---|---|---|
| `DATA_MANIFEST.md` (waves 1+2+3) | `/data` owner | Execute the fetch plan: commit-safe items in, fetch-at-build script for the rest |
| `VULTRONRETRIEVER_BRIEF.md` | vgtray (retriever) | Page-image indexing pipeline + the ViDoRe #1-on-Energy/Industrial pitch line |
| `GROUND_TRUTH_SCENARIOS.md` | injector + eval | The 2 demo runs (values pinned to manifest IDs) + 16 fault cases + 2 negative controls |
| `EVAL_SPEC.md` | simerugby | Tier-1 5/5 demo gate; Tier-2 generalization number for the pitch |

Two companion docs (sponsor-resource notes, demo-rig plan) are team-internal and are
shared on Discord, not committed to the public repo.

## What "works for real" means (the 5 checkable claims)

1. **Real inputs** — alarm names are real Eltek SNMP traps; voltage envelopes from ETSI
   EN 300 132-2; thermal shapes from a real labeled sensor stream; severities per X.733.
2. **Real knowledge** — ~145 verified sources across 3 waves, every URL refetched by an
   adversarial verifier, each carrying a rights class safe for a PUBLIC repo.
3. **Verified behavior** — 16 fault scenarios + 2 negative controls with documented
   ground truth; diagnosis accuracy becomes a number said out loud in the pitch.
4. **Honest judgment** — remediation steps cite public-domain procedures (FIST 3-6,
   TM 5-693 matrices, UFC series); costs use real prices and real SLA clocks.
5. **Reliability** — Tier-1 gate: both demo runs 5/5 consecutive before any judge sees
   them; E4 held out as the unseen overfit check.

## The corpus in one paragraph

Waves 1–3 verified **~145 sources**: open standards (ETSI/ITU-T/3GPP/IETF/O-RAN),
vendor controller manuals + MIBs (Eltek/Vertiv — real alarm names), US public-domain
manuals (TM/UFC/FIST/NAVFAC — committable symptom→fix matrices), real incident postmortems
(FCC T-Mobile/CenturyLink/AT&T, CRTC Rogers "14 h to find root cause" — the pitch foil),
real SLAs with penalty clocks (Lumen, Verizon, CALNET), open datasets (EAGLE-I grid
outages CC-BY, NASA battery aging, NAB thermal MIT, SMD attribution-labeled MIT, Huawei
gCastle alarm→causal-graph MIT), EU statistics (ENISA 2024: 188 incidents, 1,743M
user-hours, CC-BY), and the French vein: **ANFR's registry makes the demo site a real
Paris cell site**, ARCEP publishes live operator outage CSVs, Schneider CT-199 is the
bilingual retrieval beat, INRS grounds French safety steps. Prices are real ($1,329.79
rectifier, $314.95/battery, $35.73/hr labor, $150–500 truck roll).

## ⚠️ Documented limitations (critic-audited — say these, don't hide them)

1. **Radio thermal spec:** the only vendor radio thermal doc (V9) carries confidential
   footers → NEVER cite it. The citable basis is EN 300 019 class 3.1 (S4). Scenarios
   already re-pinned.
2. **RF alarm dictionary:** no public per-alarm cause→action matrix exists for RAN gear
   (they're vendor-portal-gated). RF alarm names come from O-RAN fault.rst (CC-BY);
   RF depth is framed as coverage-by-architecture, exactly per the taxonomy doc.
3. **Transport equipment manuals:** none public. Transport remediation legitimately stops
   at what a real NOC does anyway — dispatch fiber crew / escalate to provider per SLA
   clocks (Lumen TTR + AFL 13.8 h mean repair). Framed that way, it's accurate, not thin.

## Anti-overlap rule

Nothing in this folder creates GitHub issues, boards, roadmaps, agents, backend, frontend,
or iOS code. The eval runner (when written) talks to the backend over HTTP only.
