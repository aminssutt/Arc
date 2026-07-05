# Arc — 3-minute scenario + build spec (telecom)

Track: Vultr. Format: 3 min, demo-led (no slides, judges said "do not show us a presentation"). You talk while you show.

Surfaces to build: a 2-page web app (landing + control-room) and a minimal native iOS app that talks to the existing backend. Everything below is grounded in the repo seeds and the frozen contract: site PAR-021-NORD, fault DC undervoltage (PWR-DC-UV), rectifier part APR48-3G, crew PWR-2, event stream + `/api/validation` + push already exist.

Stage setup: web control-room on the projector, one iPhone in hand for the push and validation.

## The three hero features (say them out loud)

1. Matchmaking dispatch: routed to the one right technician by skill and location, not broadcast to everyone.
2. Physical validation loop: the technician tests for real and validates, or refuses with a counter-measurement and the agent pivots.
3. Document-grounded reasoning: every cause and every step cites the carrier's own technical docs, clickable.

All reasoning runs on Vultr Serverless Inference.

---

## Beat-by-beat (3:00)

**0:00 - 0:25 — Hook and problem** [WEB: landing page on screen] [SAY]
"A carrier runs tens of thousands of cell sites. When one loses power, the clock starts: SLA penalties and thousands of subscribers losing coverage. The NOC engineers who read a fault instantly are retiring. Today an alarm floods the NOC and someone manually works out what broke and who to send."

**0:25 - 0:45 — What Arc is** [WEB: landing, features section] [SAY]
"Arc takes a telecom site fault and drives it to a resolved, cited action, with a team of agents, not a chatbot. Three things make it real: it dispatches to the right technician, it closes the loop with the real world, and it grounds every decision in your own docs. All on Vultr."

**0:45 - 1:05 — Alarm and matchmaking** [WEB: control-room] [SHOW]
Trigger the fault: DC undervoltage at PAR-021-NORD. The agents locate and diagnose live in the reasoning stream. Then the matchmaking beat: "Arc does not page everyone. This is a power fault needing a senior power specialist, and the nearest qualified technician for this site's zone is this one." The roster narrows on screen to a single matched technician.

**1:05 - 1:25 — Push lands on the technician** [iOS] [SHOW]
The instant matchmaking selects the technician, their iPhone buzzes, and no one else is paged. The push fires on diagnostic_ready, which already carries the matchmaking result, so selection and notification are the same moment. Open it: a short card. Location PAR-021-NORD, the reading, probable cause DC undervoltage. No confidence score, that stays internal.

**1:25 - 1:50 — Validate or refuse** [iOS] [SHOW]
"The technician tests at the site." Either tap Validate (confirm), or tap Refuse and enter the real counter-measurement (for example -53.9V). Money shot: refuse with a contradicting measurement, and the agent pivots and re-diagnoses live. Show the pivot if the corpus supports it, it proves nothing is scripted.

**1:50 - 2:20 — Report and citations** [WEB: control-room] [SHOW]
Back on the control-room, the agent resumes and generates the action report. Walk it: the fault, the ranked cause, the intervention procedure with cited safety steps, the cost avoided, the replacement part matched to real stock (APR48-3G, in stock). Click a source chip: it opens the ingested technical document the claim rests on. "Every line traces back to the carrier's own docs."

**2:20 - 2:40 — Why it is a real agent** [SAY]
"Not retrieve-then-answer. Multiple agents, confidence-gated re-retrieval, real tool calls, a physical human loop, and skill-and-location dispatch. Grounded in documents, telecom-native, on Vultr."

**2:40 - 3:00 — Impact and human close** [SAY]
"Arc protects the technician, cuts mean-time-to-repair and SLA exposure, and scales the expertise walking out the door. The instinct of your best NOC engineer, on every fault, across every site."

---

## Surface 1 — Web page 1: Landing

One page, clean, telecom, matches the control-room's visual language (reasoning cockpit, not a dashboard).
- Hero: the one-liner plus a strong telecom line ("The instinct of your best NOC engineer, on every fault, across every site").
- Problem: two sentences (retiring expertise, SLA and coverage cost of downtime).
- The three hero features, each one line: matchmaking dispatch, physical validation loop, document-grounded reasoning.
- One CTA that opens the control-room page ("See it live").
No forms, no gauges. This is the opening frame of the pitch and the public face.

## Surface 2 — Web page 2: Control-room (the demo page)

This is where the live demo runs. It subscribes to the backend event stream and renders it as a reasoning cockpit.
- Incident header: site, alarm code, timestamp.
- Reasoning stream (the star): renders the frozen events from `contracts/EVENTS.md` in sequence, each step as its own element (dispatch, location, hypothesis with citations, retrieval, request_document, diagnostic_ready, validation_result, phase-2 events). Show the re-retrieval and the pivot when they happen. Sensor values appear only inline as cited evidence, never as a wall of gauges.
- Matchmaking panel: the roster narrowing to the one matched technician (skill level + zone). This is the creativity beat, make it legible.
- Awaiting-validation state: a clear "waiting for field validation" while the phone is in play.
- Report panel: fault, ranked cause, procedure with cited safety steps, cost avoided, part matched to stock. Every citation is a clickable chip that opens the source doc excerpt.
- A trigger control for the demo (inject fault) or auto-play on load.

## Surface 3 — iOS app (2 screens, native SwiftUI)

- Screen A, incoming diagnostic (opened from the push): a short summary card showing Location (PAR-021-NORD), Value (the reading), Probable cause (DC undervoltage). No confidence score. Two buttons: Validate and Refuse.
- Screen B, on Refuse: a field to enter the counter-measurement (value + unit, e.g. -53.9V) and a Send button. The measurement is sent so the agent re-diagnoses: it lowers confidence on the refused cause and looks for the next most probable cause given the new reading.
- After Validate or Send: a simple confirmation state ("sent, agent is finishing"), then done.

## Communication flow (web, backend, iOS)

The backend already exposes all of this, reuse it.
1. Trigger: `POST /api/demo/inject-fault` starts the incident.
2. Web control-room: `GET /api/stream` (SSE) and render every event.
3. On diagnostic_ready, the backend pushes to the matched operator's device (matchmaking picks who), payload = the summary card. Real APNs on device.
4. iOS action: `POST /api/validation`.
   - Validate: `{ incident_id, status: "confirmed" }`
   - Refuse: `{ incident_id, status: "rejected", measurement: { value, unit } }`
5. Backend resumes the state machine: confirmed goes to phase 2 (report), rejected pivots and re-diagnoses. New events stream to the web, which renders the pivot or the final report.

The web shows the brain reasoning, the phone is the operator's action surface, both synced through the stream and the validation call.

## Build checklist

- Web landing (page 1): static, fast, on-brand. Frontend.
- Web control-room (page 2): SSE client + event renderer + matchmaking panel + clickable report. Frontend, against the existing stream and the mock stream for offline work.
- iOS: two screens + push receiver + the two validation payloads. iOS dev, build to device via Xcode.
- Corpus: fetch the doc that currently blocks the pivot re-diagnostic, so the money shot lands.

## Fallbacks (non negotiable)

- Record a clean end-to-end backup video (web + phone) before judging. Narrate over it if anything flakes live.
- Keep a responsive mobile-web version of the two iOS screens in case device push fails on stage.
