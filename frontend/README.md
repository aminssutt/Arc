# /frontend — Arc control room (Next.js)

- **Owner:** daniwavy5032 · scaffolded by aminssutt — **coordinate before large changes.**
- **Goes here:** Next.js control-room web app (NOC monitoring) — SSE client, event renderers, citations UI, action-report view.
- **Does NOT go here:** the iOS app (`/ios`), backend/API code (`/backend`), design specs/tokens (`/design`).

The NOC **reasoning cockpit**: a live view of the incident as the agents reason,
ground, and act. Consumes the backend SSE stream and drives the demo.

## What it does
- Subscribes to `GET /api/stream` (Server-Sent Events) and renders the incident
  timeline live: fault → correlation/root-cause (with **retrievals** and the
  ranked **diagnosis + citations**) → **field-validation** (human loop) →
  remediation → **action report** with the **citation drill-down** (click any
  source → opens the exact document at its page).
- Trigger a run: `Inject — Confirm` / `Inject — Pivot` (`POST /api/demo/inject-fault`),
  `Reset` (`POST /api/demo/reset`).
- Human loop: while awaiting validation, submit the technician's busbar
  measurement + verdict (`POST /api/validation`) — a healthy float (−53.9 V)
  triggers the live **pivot**.

## Run
The backend (FastAPI) must be running — from the repo root:
```bash
python -m uvicorn backend.app.main:app --port 8000     # backend
```
Then the frontend:
```bash
cd frontend
cp .env.example .env.local        # points at http://localhost:8000 by default
npm install
npm run dev                       # http://localhost:3000
```
Backend CORS is open, so the cross-origin SSE + POST work out of the box.
For a fully live demo with real diagnoses/citations, set the Vultr key in the
backend env (else it runs on the offline dummy agents).

## Structure
```
app/           layout + globals (NOC design tokens, light/dark) + the control-room page
lib/events.ts  event contract types + useIncidentStream() SSE hook
lib/api.ts     API base + inject/reset/validation calls
components/     TriggerBar · EventCard (timeline) · ReportCard · CitationTrail · ValidationForm
```

## Design
Direction: **reasoning-cockpit, anti-dashboard** (per `/design`). Dark NOC ground,
one accent, monospace for codes/IDs, semantic colors for state (confirmed / pivot /
warning). Both themes; manual toggle in the trigger bar.
