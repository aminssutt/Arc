# Frontend — Arc control room (web)

The web surface lives in `frontend/`. It is a Next.js 15 App Router app (React
19, TypeScript, Tailwind 3) that plays two roles for the demo:

1. a **pitch landing** (`/`) that explains the multi-agent fault-response system;
2. a **live control room** (`/monitor`) that renders the backend's incident
   lifecycle from the SSE stream, closes each case with a cited action report,
   and archives it.

Package name `arc-control-room`, version `0.1.0` (`frontend/package.json`).
Notable dependencies: `next` ^15, `react` ^19, `framer-motion` (motion),
`lenis` (smooth scroll on the landing), `@splinetool/react-spline` +
`@splinetool/runtime` (the 3D hero), `jspdf` (client-side PDF export),
`lucide-react` (icons), `tailwindcss` ^3.

## Routes

All routes live under `frontend/src/app/`.

| Route | File | What it is |
|-------|------|------------|
| `/` | `src/app/page.tsx` | Landing. A numbered editorial page (light + sky-blue), Spline 3D hero, eight numbered sections (`01 The problem` -> `08 By the numbers`), one of which (`05`) is a dark live-control-room screen embedding `ControlRoomPreview`, closing with two `Launch the control room` CTAs to `/login?next=/monitor`. Server component composing client "islands" from `src/components/landing/`. |
| `/login` | `src/app/login/page.tsx` | Client-side sign-in. Name + role picker (`NOC Engineer`, `Facility Manager`, `Field Technician`). No real auth — `signIn()` writes a `Session` to `localStorage` under `arc-session` (`src/lib/session.ts`) and redirects to the `next` query param (default `/monitor`). |
| `/monitor` | `src/app/monitor/page.tsx` | **The control room** — the primary demo surface. Detailed below. Guarded: redirects to `/login?next=/monitor` when there is no session. |
| `/reports` | `src/app/reports/page.tsx` | Action-report archive. Reads `listReports()` from `localStorage` (`arc-reports`), seeded with two sample reports. Each card expands to the diagnosis, priority actions, investigation flow, evidence, clickable sources, and PDF/JSON export. Session-guarded. |
| `/console` | `src/app/console/page.tsx` | Raw contract console. An **editable backend URL** field plus buttons for health, start/stop stream, inject confirm/pivot, submit real/false, reset. Shows the last 12 events and the current incident payload. The low-level surface for poking the backend directly. |
| `/design-review` | `src/app/design-review/page.tsx` | Design-system showcase (Button / Badge / Card variants). Not part of the demo flow. |

The session model (`src/lib/session.ts`) is deliberately minimal — real auth is
out of scope for the hackathon; the comment in that file says so.

## The control room (`/monitor`)

One full-screen viewport at a time, switched by a segmented control in the
header. Evidence and agent state are shared across both views.

### Two views: Simple vs Technical

`viewMode` state (`src/app/monitor/page.tsx:61`) toggles between:

- **Simple** — `BuildingSituation` (`src/components/investigation/BuildingSituation.tsx`).
  The equipment-shelter wireframe for site `PAR-021-NORD`, with fault-location
  dot markers synced to the shared evidence bar. A legend maps marker tone to
  `fault` / `standard match` / `field handoff` / `resolved`.
- **Technical** — `AgentGraph` (`src/components/investigation/AgentGraph.tsx`).
  The live agentic pipeline. A **COMMAND** band (the Watchdog opens the
  incident, the LangGraph Orchestrator routes the typed state) feeds a
  **PIPELINE** rail of six agents in the exact backend order:
  `Correlation -> Root-Cause -> Matching -> Validation -> Remediation ->
  Cost/Dispatch`. The active agent gets a "working" treatment; the right rail
  carries the live decision label, the matching beat (the ONE chosen
  responder), and the append-only reasoning stream.

> **Demo recommendation:** the default is **Simple** (`useState("simple")`), but
> the multi-agent orchestration — the centrepiece of the pitch — only shows in
> **Technical**. Switch to Technical before running the incident.

### Driving the demo

Two independent control clusters:

- `SituationLauncher` (`src/components/investigation/SituationLauncher.tsx`) —
  the primary bar in the header. Idle: `Run incident` (confirm path) and
  `Run pivot path` (pivot path). When the case is `awaiting-validation`:
  `Confirm verdict` / `Pivot diagnosis`, which POST the field verdict from the
  web (see below).
- `DebugDock` (`src/components/investigation/DebugDock.tsx`) — a bug button
  bottom-right that expands to Confirm/Pivot, Reset, a **Stream on/off** toggle,
  a link to `/console`, and demo `Field validate` buttons.

### Live stream vs local replay

The page can run against the backend or entirely offline:

- **Streaming mode (default).** On mount, `startStream()` opens the SSE
  connection and the backend drives state. `Run incident` then calls
  `POST /api/demo/reset` followed by `POST /api/demo/inject-fault` (reset first
  because inject-fault returns 409 while an incident is active —
  `src/app/monitor/page.tsx:130`). The stream reconnects with a capped
  exponential backoff; reconnecting is safe because the backend replays event
  history and the reducer dedupes by event `id`.
- **Local replay (offline).** Toggle `Stream` off in the Debug dock, then
  `Run incident` / `Run pivot`. `scenarioBeats(scenario)`
  (`src/lib/investigation.ts:402`) drives a timed, client-side replay with no
  backend at all — baked demo evidence, a demo responder (`DEMO_RESPONDER`, the
  in-zone energy senior `EMP-003`), and full demo reports
  (`DEMO_REPORT_CONFIRM` / `DEMO_REPORT_PIVOT`) whose citations carry `open_url`
  and are therefore clickable.

### Field validation from the web

`submitFieldValidation()` POSTs `makeDemoValidation(incident, verdict)` to
`POST /api/validation` — the **same** call the iOS app makes
(`src/lib/contracts.ts:93`). It exists so the end-to-end finale can complete
without a phone. It is explicitly *additive* and does not replace the real iOS
validation path (see `docs/IOS.md`). The payload is fixed for the demo:
technician `daniwavy5032`, one `dc_plant_voltage_v` busbar measurement of
`43.9 V`.

## SSE client and backend URL

The client is `BackendClient` (`src/lib/backend-client.ts`). It wraps:

- `health()` -> `GET /health`
- `injectFault(req)` -> `POST /api/demo/inject-fault`
- `reset()` -> `POST /api/demo/reset`
- `submitValidation(sub)` -> `POST /api/validation`
- `streamEvents(onEvent, signal)` -> `GET /api/stream`

`streamEvents` reads the response body as a stream, splits on the SSE `\n\n`
delimiter, keeps `data:` lines, and `JSON.parse`s each chunk into a
`BackendEventEnvelope` (`{ seq, id, ts, incident_id, type, data }`).

**Backend URL configuration.** The base URL comes from the
`NEXT_PUBLIC_ARC_BACKEND_URL` environment variable, defaulting to
`http://127.0.0.1:8000`. It is referenced in exactly two places:
`src/app/monitor/page.tsx:30` and `src/app/console/page.tsx:15`. The `/console`
page additionally exposes the URL as an **editable field**, so you can repoint
it live in the browser without an env var.

> **Finding — stale env example.** `frontend/.env.example` declares
> `NEXT_PUBLIC_API_BASE=http://localhost:8000`, but no code reads that name —
> the code reads `NEXT_PUBLIC_ARC_BACKEND_URL`. `frontend/README.md` documents
> the correct variable. If you copy `.env.example` to `.env.local`, rename the
> variable to `NEXT_PUBLIC_ARC_BACKEND_URL` or it will have no effect.

## The event reducer

`src/lib/investigation.ts` is the state machine behind `/monitor`.
`investigationReducer` applies `apply` / `reset` actions;
`actionForBackendEvent(event)` translates a wire event into an action. Both the
live stream and the local replay feed the same reducer.

Wire agent names are mapped to graph nodes by `WIRE_AGENT_TO_NODE`:
`correlation`, `root_cause`, `validation`, `remediation`,
`cost_inventory_dispatch`.

**Event types the reducer consumes** (from `contracts/EVENTS.md`):

`fault_detected`, `phase_started` (only when `data.cause === "pivot"`),
`agent_started`, `agent_completed`, `retrieval_performed`, `diagnostic_ready`,
`push_sent`, `awaiting_field_validation`, `validation_received`,
`validation_result`, `remediation_ready`, `action_report_ready`,
`doc_requested`, `incident_resolved`.

Behaviour notes:

- `fault_detected` wipes the previous run (evidence, flow, activity, responder,
  report) so replayed histories with several incidents back-to-back each start
  clean.
- Lists (`evidence`, `flow`, `activity`) are append-only and deduped by `id`.
- The responder card is coerced from `awaiting_field_validation.data.responders[0]`
  (`coerceResponder`); the finale report from `action_report_ready.data.report`
  (`coerceReport`). Both are lenient — a degraded/missing payload yields `null`
  and the run continues rather than crashing the stream.

## Citations, the action report, and PDF

When `action_report_ready` lands (or the case resolves), `MonitorPage` builds an
`ActionReport` (`src/lib/reports.ts`), archives it to `localStorage`
(`arc-reports`), and raises `ActionReportPanel`
(`src/components/investigation/ActionReportPanel.tsx`).

The panel renders the diagnosis + confidence, recommended actions, an
operational summary (cost / inventory / dispatch), `honesty_notes` (shown as
"Limitations and assumptions"), and a **References** section. Each reference is
a clickable `<a href={source.open_url || source.url}>` **when a link is
present**; otherwise it renders as plain text. The same logic backs the source
list on `/reports`.

`Export PDF` calls `reportToPdf(report)` (`src/lib/reports.ts:210`): a
client-side jsPDF A4 document (dynamically imported) with the diagnosis,
actions, cost/dispatch, flow, evidence, and clickable source links
(`doc.textWithLink`, page-anchored via `open_url` when known). `/reports` also
offers a JSON export.

## Known limitations (verified)

- **`responder_matched` is not consumed by the reducer.** The backend emits a
  dedicated `responder_matched` event carrying the full scored shortlist (`data`
  keys: `fault`, `difficulty`, `chosen`, `candidates` — confirmed in
  `contracts/mock_stream/run_confirm.ndjson`), but `actionForBackendEvent` has
  no case for it, so it falls through to `default -> null`. The web builds the
  responder card only from the single pick on `awaiting_field_validation`. The
  consequence: the **candidate competition** (all technicians scored) is never
  surfaced in the UI; only the winner appears.
- **Citations are not clickable in mock-replay mode.** The static ndjson
  fixtures (`contracts/mock_stream/*.ndjson`) carry citations with only a
  `doc_id` — no `title` / `url` / `open_url` / `openable`, because the backend's
  `enrich_citations()` runs live and is not baked into the fixtures. Since the
  UI links a source only when `open_url || url` exists, the References render as
  plain, non-clickable text when the frontend is pointed at the replay server.
  Against the **live backend** and in the **local client-side replay**
  (`DEMO_SOURCES`), citations *are* clickable. Note also that `replay.py` serves
  only `/api/stream` and `/health` — `inject-fault`, `reset`, and `validation`
  are not available in replay mode (the validation events are already inside the
  fixture, so the loop still plays back; you just cannot drive it).
- **Default view is Simple.** As above, switch to **Technical** for the demo so
  the multi-agent orchestration is visible.

## Running the frontend

Dev, against a local backend:

```sh
# 1. backend, from the repository root
python -m uvicorn backend.app.main:app --port 8000

# 2. frontend
cd frontend
npm install
# optional: point at a non-default backend (see the env note above)
echo 'NEXT_PUBLIC_ARC_BACKEND_URL=http://127.0.0.1:8000' > .env.local
npm run dev            # http://localhost:3000
```

Production build: `npm run build` then `npm run start` (port 3000). Lint:
`npm run lint`. Type-check: `npm run typecheck`.

Fully offline (no backend, no phone): open `/monitor`, open the Debug dock,
toggle **Stream off**, switch to **Technical**, and press **Run incident** /
**Run pivot path** — the timed local replay plays the full lifecycle including a
cited action report.

Against the mock SSE replay server (real stream, static fixtures):

```sh
python contracts/mock_stream/replay.py contracts/mock_stream/run_confirm.ndjson
# serves /api/stream on port 8010; then set
# NEXT_PUBLIC_ARC_BACKEND_URL=http://localhost:8010 (or type it in /console)
```
