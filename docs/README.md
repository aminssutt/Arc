# Arc documentation

Arc is a multi-agent system for **telecom site fault response** (RAISE Summit,
Vultr track). A deterministic Watchdog ingests the site alarm feed and triggers
an Orchestrator that runs specialist agents in two phases, with a **human
validation loop on a native iOS app** in the middle. All reasoning runs on
**Vultr Serverless Inference**, grounded via **VultronRetriever** in real telecom
documents. The output is a prioritized action report with a full citation trail.

This folder is the project's technical documentation. Start with `ARCHITECTURE.md`
for the big picture, then read the surface you care about.

## Contents

### System

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — the whole system end to end: Watchdog →
  Orchestrator → phase-1 (diagnosis) and phase-2 (action) agents, the human loop,
  the event stream, and how the pieces connect.
- **[AGENTS.md](AGENTS.md)** — the specialist agents (Correlation, Root-Cause,
  Validation, Remediation, Cost/Inventory/Dispatch, Responder-Matching): what each
  one does, its inputs/outputs, and its frozen contract.
- **[BACKEND-API.md](BACKEND-API.md)** — the FastAPI backend: the HTTP endpoints
  (`/api/stream`, `/api/demo/inject-fault`, `/api/demo/reset`, `/api/validation`,
  `/api/devices`, `/health`), the SSE event contract, and the push service.
- **[VULTR.md](VULTR.md)** — the Vultr Serverless Inference client, the pinned
  model, the concurrency guard, and the JSON safety net.
- **[CORPUS.md](CORPUS.md)** — the grounding corpus and the retriever: the
  manifest, the chunking builder, the `doc_id` namespace, and the citation trail.

### Surfaces

- **[FRONTEND.md](FRONTEND.md)** — the Next.js control room (web): pages, the
  Simple/Technical control-room views, the SSE client and backend-URL config, the
  event reducer, the citation/PDF viewer, and the offline mock/replay mode.
- **[IOS.md](IOS.md)** — the SwiftUI operator app: the two screens and their
  states, the APNs push flow, the frozen `/api/validation` payloads, the in-app
  config, the XcodeGen build, and device setup.

### History

- **[MILESTONES.md](MILESTONES.md)** — how Arc was built, milestone by milestone
  (M1–M8), reconstructed from the git history, the merged PRs, and
  `../contracts/decisions.md`.

### Pitch and reference

- **[arc-pitch-scenario-3min.md](arc-pitch-scenario-3min.md)** — the beat-by-beat
  3-minute demo script (what to say and show, in order).
- **[arc-pitch.md](arc-pitch.md)** — the full pitch narrative.
- **[arc-agents-spec.md](arc-agents-spec.md)** — the agents specification.
- **[arc-architecture-v2.mermaid](arc-architecture-v2.mermaid)** — the
  architecture diagram (Mermaid source).

> `CURRENT_STATE.md` is a stale local scratch file — not part of this
> documentation set; ignore it.

## Demo quickstart

```sh
# 1. Backend (Python 3.12+, .env filled with Vultr keys — see ../.env.example)
python -m uvicorn backend.app.main:app --port 8000

# 2. Frontend
cd frontend && npm install && npm run dev          # http://localhost:3000

# 3. iOS: open ios/Arc.xcodeproj in Xcode, Run to a plugged-in iPhone,
#    then gear → set Backend to the Mac's LAN IP (e.g. http://192.168.1.10:8000)

# 4. In the browser: sign in at /login, open /monitor, switch to the Technical
#    view, and make sure Stream is on (Debug dock, bottom-right).

# 5. Inject the incident (or press "Run incident" in the control room):
curl -X POST http://127.0.0.1:8000/api/demo/inject-fault \
  -H 'Content-Type: application/json' -d '{"scenario":"confirm"}'
```

The agents diagnose live in the control room, the push lands on the phone,
the technician **Validates** (or **Refuses** with a counter-measurement, driving
a pivot), and the finale is a cited action report you can open and export as PDF.
Use `{"scenario":"pivot"}` to demo the refuse-and-re-diagnose path. No backend or
phone? See the fully-offline replay in [FRONTEND.md](FRONTEND.md).
