# /backend

- **Owner:** simerugby
- **Goes here:** FastAPI app, deterministic watchdog, SSE stream, push service, validation intake, the 3 tools (Cost/Inventory/Dispatch), orchestrator runtime, data loading.
- **Does NOT go here:** agent reasoning/prompts (`/agents`), UI (`/frontend`, `/ios`), frozen schemas (`/contracts`).
- **Requires Python ≥ 3.12 — see root README / `.python-version`.**

## Run (BE.1)

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --port 8000    # from the repo root
# or: python backend/run.py
curl localhost:8000/health
```

Settings are **env-only** — see `.env.example` (`ARC_PORT`, `ARC_DATA_DIR`,
`ARC_PUSH_MODE`, …). No secrets, ever (public repo).

## Demo flow (one command each)

```bash
curl -X POST localhost:8000/api/demo/inject-fault -H 'Content-Type: application/json' \
     -d '{"scenario":"confirm"}'                      # or "pivot", or {"alarm_code":"RF-VSWR-HIGH"}
curl -N localhost:8000/api/stream                     # SSE: watch the run live
# push payload is written to $ARC_PUSH_OUT_DIR/push_<incident>.json — on the demo
# Mac (ARC_PUSH_MODE=simctl) it is also delivered: xcrun simctl push booted <file>
curl -X POST localhost:8000/api/validation -H 'Content-Type: application/json' -d '{
  "incident_id":"INC-LIVE-001","client_event_id":"demo-1",
  "submitted_at":"2026-07-05T09:33:00Z",
  "validations":[{"failure_id":"F1","verdict":"real"}],
  "measurements":[{"metric":"dc_plant_voltage_v","point":"busbar","value":43.9,"unit":"V"}]}'
curl -X POST localhost:8000/api/demo/reset            # back to idle < 5 s, retake-ready
```

A verdict of `"false"` anywhere triggers the **pivot loop**: re-diagnosis with the
field measurement as ground truth, revised report, `outcome: downgraded`.

## Architecture (issue ↔ module)

| Module | Issue | Role |
|---|---|---|
| `app/main.py` | BE.1 | app factory, `/health`, lifespan wiring |
| `app/watchdog.py` | BE.2 | deterministic ingest→normalize→threshold→debounce; ZERO LLM; fully data-driven from `alarm_dictionary.csv` |
| `app/orchestrator.py` | BE.3 | state machine + pivot loop; agents pluggable via the FROZEN `contracts.Agent` protocol; holds state, never diagnoses |
| `app/api/routes_stream.py` | BE.4 | SSE per contract (heartbeat, Last-Event-ID resume, concurrent clients) |
| `app/push_service.py` | BE.5 | contract push payload on diagnostic_ready; simctl primary, APNs flag-gated |
| `app/api/routes_validation.py` | BE.6 | schema-validated, idempotent intake; 409 on wrong state |
| `app/tools/` | BE.7-9 | Cost Engine, Inventory Lookup, Crew Dispatch — deterministic over seeds, frozen `Tool` protocol |
| `app/seeds.py` | BE.10 | loads `/data` per `data/schema.md`, FK-validated, loud errors; falls back to `seed_defaults/` until DEMO.2 |
| `app/api/routes_demo.py` | BE.11 | inject-fault (drives the REAL watchdog path) + reset |
| `app/dummy_agents.py` | BE.3 | canned stand-ins (no diagnosis logic); real agents replace them by registry name. `cost_inventory_dispatch` stand-in calls the 3 REAL tools |

Every emitted envelope is validated against `contracts/events.schema.json` in the
test suite — the backend cannot drift from what frontend/iOS build against.

## Tests

```bash
pip install -r backend/requirements-dev.txt
cd backend && python -m pytest      # 23 tests: watchdog, state machine incl. pivot, intake, tools, seeds, SSE-over-HTTP
```

## Plugging real agents (vgtray / aminssutt)

The orchestrator takes `dict[str, contracts.Agent]` keyed by
`correlation | root_cause | validation | remediation | cost_inventory_dispatch`
(see `dummy_agents.default_registry`). Implement the frozen protocol, swap the
registry entry in `main.py`'s lifespan — nothing else changes. Agent payload
conventions the runtime maps into events: `retrievals` (list of
`{pass, query, results[]}` → `retrieval_performed`), `diagnostic`
(`{causes[], urgency, verification_requests[]}` → `diagnostic_ready`),
`procedure`/`parts`/`action_hints` (remediation), `result`/`rationale`/
`contradictions` (validation).
