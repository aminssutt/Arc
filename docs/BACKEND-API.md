# Arc — Backend API Reference

The backend is a FastAPI app (`backend/app/main.py`, boot: `python -m uvicorn
backend.app.main:app` from the repo root, or `python backend/run.py`). It exposes
one health probe, a live SSE stream, two demo-control endpoints, the validation
intake, a device registry, and a citation resolver. Everything is configured by
environment variables (all with sane defaults). CORS is open (`allow_origins=["*"]`).

The frozen event / push / validation contracts are the source of truth
([`contracts/EVENTS.md`](../contracts/EVENTS.md) and the three
`contracts/*.schema.json`); the HTTP endpoints below are the additive surface the
web control room and the iOS app consume.

## Endpoint summary

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/health` | Liveness + which agents are real vs. dummy + seed sources |
| `GET`  | `/api/stream` | SSE broadcast of all orchestrator events (with resume) |
| `POST` | `/api/demo/inject-fault` | Trigger a scenario or an alarm-code fault |
| `POST` | `/api/demo/reset` | Return the system to idle |
| `POST` | `/api/validation` | Field technician's verdict + measurement (2 shapes) |
| `POST` | `/api/devices` | Register an APNs device token |
| `GET`  | `/api/citations/{doc_id}` | Resolve a citation to an openable source |

---

## `GET /health`

Liveness probe and an integration smoke check at a glance. Reports the current
orchestrator state, the concrete class of each registered agent (so you can see
which lanes are real vs. dummy), and where each seed entity loaded from.

```json
{
  "status": "ok",
  "state": "idle",
  "agents": {
    "correlation": "CorrelationAgentAdapter",
    "root_cause": "RootCauseAgentAdapter",
    "validation": "ValidationAgentAdapter",
    "remediation": "RemediationAgentAdapter",
    "cost_inventory_dispatch": "CostInventoryDispatchAgent",
    "responder_matching": "ResponderMatchingAgent"
  },
  "seeds": { "alarm_dictionary.csv": "/…/data/alarm_dictionary.csv", "…": "…" }
}
```

---

## `GET /api/stream` (SSE)

`text/event-stream`. On connect the server **replays the full incident history**,
then streams live events; a `: hb` heartbeat comment is sent every `heartbeat_s`
(default 15 s) when idle. Each event is written in standard SSE framing, and the
`data:` field carries the **entire envelope** as one-line JSON, so a client can
parse `data` alone:

```
id: INC-LIVE-001-0006
event: diagnostic_ready
data: {"seq":6,"id":"INC-LIVE-001-0006","ts":"2026-07-05T09:24:10Z","incident_id":"INC-LIVE-001","type":"diagnostic_ready","data":{…}}
```

**Resume:** reconnect with the standard `Last-Event-ID` header (or `?lastEventId=`
query param); the server replays every event after that id (`EventBus.replay_after`).
The envelope shape `{seq, id, ts, incident_id, type, data}` is frozen by
`contracts/events.schema.json`; `seq` is per-incident and gapless. The 15 event
types and their `data` payloads are cataloged in
[`contracts/EVENTS.md`](../contracts/EVENTS.md).

The same wire is served offline by `python contracts/mock_stream/replay.py
run_confirm.ndjson` — frontend and iOS swap mock ↔ live by changing the base URL
only.

---

## The action report (`action_report_ready`)

The prioritized action report rides the SSE stream as the `action_report_ready`
event (full `data.report` shape in [`contracts/EVENTS.md`](../contracts/EVENTS.md)
event #12). The **shape is identical on every run**, but `inventory` and `cost`
depend on the incident outcome (`Orchestrator._assemble_report`):

| `report` field | Confirmed (genuine rectifier fault) | Pivot → downgraded (sensing fault) |
|---|---|---|
| `diagnosis.cause` | rectifier module failure (cites V4/V6) | supervision / measurement-path fault (cites S2/V2) |
| `inventory.part_no` | `APR48-3G` | `SP2-MU` |
| `inventory.in_stock` / `qty_available` | `true` / 3 | `false` / 0 |
| `inventory.location` | `WH-PAR-EST` | `""` (unstocked) |
| `cost.intervention` | 1165.50 | 396.46 |
| `cost.avoided` | 6800.00 | 1165.50 |
| `incident_resolved.outcome` | `resolved` | `downgraded` |

`cost.intervention` is `part + 2 h labor (71.46) + truck roll (325.00)`: `769.04 +
71.46 + 325.00` on confirm, and `71.46 + 325.00` on pivot (the supervision part is
not stocked, so it contributes 0). `cost.avoided` is the prevented outage on
confirm (`5.00/min * 240 min * 1.5 + 5000.00` SLA penalty = 6800.00) and, on a
pivot, the needless emergency replacement the false alarm would have triggered
(the *original* rectifier part `769.04 + 71.46 + 325.00 = 1165.50`). `SP2-MU` is
the deterministic dummy/fallback part; the pivot never books the rectifier spare
because `_suspect_part()` returns `None` after a pivot. See the
Cost/Inventory/Dispatch chapter in [AGENTS.md](AGENTS.md).

---

## `POST /api/demo/inject-fault`

Triggers a fault through the **real Watchdog path**. Two body shapes:

- **Scenario mode** — replays the seeded signal timeline
  (`data/scenarios/run_<name>_signals.jsonl`), fully reproducible from seeds:
  ```json
  { "scenario": "confirm" }   // or "pivot"
  ```
- **Alarm-code mode** — synthesizes a minimal breach timeline (two signals
  `debounce_s` apart in event time) for any family in the alarm dictionary:
  ```json
  { "alarm_code": "PWR-DC-UV", "site_id": "PAR-021-NORD", "equipment_id": "busbar" }
  ```
  `site_id` defaults to `PAR-021-NORD`; `equipment_id` is optional.

**Responses:** `200 {status:"injected", scenario, signals_replayed, incident_id,
state}` · `409` if an incident is already active (reset first) · `422` if neither
a known scenario nor a known `alarm_code` is provided.

## `POST /api/demo/reset`

Returns the system to idle in under 5 s (immediate). Resets the orchestrator
(cancels any in-flight task), the Watchdog episodes and fired-signatures
(re-arms the demo), the event history, the idempotency cache, the push anti-spam
counters, and releases crew bookings made by the dispatch tool. `200 {status:"idle"}`.

---

## `POST /api/validation`

The mobile veracity check. **Two request shapes are accepted**, both converging on
the frozen contract (`contracts/validation_event.schema.json`):

**1. Full (frozen) body** — the complete validation event:

```json
{
  "incident_id": "INC-LIVE-001",
  "client_event_id": "ios-8c1f",
  "submitted_at": "2026-07-05T09:41:00Z",
  "technician": {"id": "tech-07", "name": "on-call field tech"},
  "validations": [
    {"failure_id": "F1", "verdict": "real", "note": "module LED dark"},
    {"failure_id": "F2", "verdict": "false"}
  ],
  "measurements": [{"metric": "dc_voltage_v", "point": "busbar", "value": -53.9, "unit": "V"}]
}
```

**2. Pitch (iOS card) shape** — additive, expanded server-side into a schema-valid
full body:

```json
{ "incident_id": "INC-LIVE-001", "status": "confirmed" }
```
```json
{ "incident_id": "INC-LIVE-001", "status": "rejected",
  "measurement": {"value": -53.9, "unit": "V"} }
```

On `confirmed`, every failure is marked `verdict=real`. On `rejected`, the
load-bearing failure (chosen by the measurement's physical **unit**) is marked
`verdict=false` and the counter-measurement is attached — this drives the pivot
re-diagnosis. `rejected` requires `measurement {value, unit}`.

**Semantics:**
- Body validated against the frozen schema → `422 {detail:[…]}` on violation.
- **Idempotent on `client_event_id`:** a resend returns the original `200`, no
  second state change.
- `409` when no incident is awaiting field validation, or the `incident_id` does
  not match the active incident.
- Success: `200 {status:"accepted", incident_id, result:"confirmed"|"pivot"}`.

---

## `POST /api/devices`

Registers an APNs device token so a diagnostic push reaches the matched
technician's real iPhone.

```json
{ "device_token": "<hex token>", "platform": "ios", "operator_id": "EMP-001" }
```

`204` on success; `422` when `device_token` is missing. Tokens are stored
in-memory and mirrored to a `.runtime` JSON file (`device_store_path`) so a
registered device survives a backend reload during rehearsals. No token is ever
logged.

---

## `GET /api/citations/{doc_id}?claim=<str>`

Opens a cited source. Resolves `doc_id` against `data/corpus_manifest.json`
(title/path) and the `data/corpus/` files, and returns a best-effort
(section, snippet) around the `claim`:

```
GET /api/citations/V4?claim=rectifier-lost%20alarm%20signature
200 {
  "doc_id": "V4",
  "title": "Vertiv NetSure 2100 -48VDC manual",
  "section": "Plant architecture and N+1 redundancy",
  "snippet": "…the bus stays at float and the batteries are not called upon…",
  "source_path": "corpus/vendor/v4_netsure2100.pdf"
}
```

Content resolution order: an inline manifest `text` field first (e.g. O5, the
link-only spare listing → `source_path:"(inline)"`), then the on-disk source (the
`.pdf` paths are plain-text markdown, served as text). Resolvable `doc_id`s:
`V4, S1, V6, FIST-3-6, TM-5-693, UFC-3-540-07, O1, O5, S2, V2`. A clean `404` when
the `doc_id` is unknown or its source is not materialised. Only `citation`
objects (on causes, steps, the report) are guaranteed resolvable — a
`retrieval_performed.results[].doc_id` is a raw search hit. See
[CORPUS.md](CORPUS.md).

---

## Push pipeline

The `PushService` (`backend/app/push_service.py`) emits the contract push payload
when Phase 1 is ready for the human loop. Every payload is validated against
`contracts/push_payload.schema.json` **before** delivery (an invalid push raises —
a contract break is caught in dev).

### Delivery modes (`ARC_PUSH_MODE`)

- **`file`** (default, works everywhere) — writes the payload JSON to
  `push_out_dir`. The file *is* the simctl input: on the demo Mac,
  `xcrun simctl push booted <file>` is the whole delivery step.
- **`simctl`** — file + shells out to `xcrun simctl push booted <file>` (macOS
  only; falls back to file with a warning elsewhere).
- **`apns`** — real token-based APNs to the **matched operator's** registered
  device(s); still writes the file so the simctl/file path remains a fallback. A
  missing/invalid Apple key degrades to file delivery (a warning, never a crash).

### Real APNs (`backend/app/apns_client.py`)

Token-based **ES256** provider auth over **HTTP/2** to Apple's **sandbox** gateway
(`api.sandbox.push.apple.com`; `api.push.apple.com` when `APNS_USE_SANDBOX=false`).
A short-lived JWT (`{iss: team_id, iat}`, header `{alg: ES256, kid: key_id}`) is
signed with the team key and reused for `token_ttl_s` (3000 s). Headers:
`apns-topic` = bundle id, `apns-push-type: alert`, `apns-priority: 10`, and
`apns-collapse-id` = `incident_id`. Imports (PyJWT, httpx[http2]) are lazy, so a
`file`/`simctl` backend needs no Apple dependencies. No token, key, or JWT is ever
logged. The `Simulator Target Bundle` helper key is stripped from the real APNs
body.

### Payload (built by `build_payload`)

```json
{
  "Simulator Target Bundle": "com.arc.operator",
  "aps": {"alert": {"title": "Arc — PAR-021-NORD: energy fault",
                    "body": "2 detected failure(s) await field validation"},
          "sound": "default", "category": "ARC_VALIDATION"},
  "incident_id": "INC-LIVE-001",
  "site": {"id": "PAR-021-NORD", "name": "Paris Nord macro site",
           "lat": 48.8969, "lon": 2.3383, "address": "Rue de la Chapelle, 75018 Paris"},
  "family": "energy",
  "failures": [{"id": "F1", "code": "alarmMajorRectifier", "severity": "major", "equipment": "EQ-PAR-021N-RECT-2"},
               {"id": "F2", "code": "DC_UNDERVOLTAGE", "severity": "critical", "equipment": "busbar"}],
  "reading": {"value": -44.8, "unit": "V", "point": "busbar", "metric": "dc_voltage_v"}
}
```

The optional **`reading`** carries the load-bearing telemetry for the iPhone card
(`_reading`): it is drawn from the failure with a *continuous* measurable quantity
(busbar `dc_voltage_v`, current, temperature, …), **never a boolean status
signal**, and carries **no confidence**. `_METRIC_UNITS` maps each metric to its
display unit.

### Routing + anti-spam

`_deliver` sends real APNs first, to `_target_tokens(operator_id)` — the matched
operator's device tokens, falling back to every registered device. The
anti-spam cap (`push_max_per_incident`, `push_min_interval_s`) is applied in
`send()`; a suppressed push returns `None` and emits no `push_sent`. A successful
send emits `push_sent {method, payload}` (`method ∈ {apns, simctl}` per the frozen
enum — `file` mode reports `simctl`, since the written file is the simctl input).

---

## Configuration

All settings are environment variables (`backend/app/settings.py`), each with a
default so the backend boots with no setup. Secrets never live in the repo — they
come from the local `.env` (gitignored). Values are never logged.

| Env var | Default | Role |
|---|---|---|
| `ARC_HOST` | `0.0.0.0` | Bind host |
| `ARC_PORT` | `8000` | Bind port |
| `ARC_DATA_DIR` | `<repo>/data` | Seed data dir; missing files fall back to `backend/seed_defaults` |
| `ARC_PUSH_MODE` | `file` | `file` \| `simctl` \| `apns` |
| `ARC_PUSH_BUNDLE_ID` | `com.arc.operator` | Bundle id for the simctl payload key |
| `ARC_PUSH_OUT_DIR` | `<tmp>/arc-push-out` | Where push payload JSON files are written |
| `ARC_HEARTBEAT_S` | `15` | SSE heartbeat interval (seconds) |
| `ARC_AGENT_TIMEOUT_S` | `120` | Per-agent timeout → graceful `agent_completed status=timeout` |
| `ARC_PUSH_MAX_PER_INCIDENT` | `2` | Anti-spam: max pushes per incident (initial + pivot) |
| `ARC_PUSH_MIN_INTERVAL_S` | `10` | Anti-spam: min seconds between any two pushes |
| `APPLE_TEAM_ID` / `APNS_TEAM_ID` | `""` | APNs team id (ES256 auth) |
| `APPLE_KEY_ID` / `APNS_KEY_ID` | `""` | APNs signing key id |
| `APPLE_BUNDLE_ID` / `APNS_BUNDLE_ID` | `ARC_PUSH_BUNDLE_ID` | APNs `apns-topic` |
| `APPLE_PRIVATE_KEY_PEM` / `APNS_AUTH_KEY` | `""` | APNs private key (PEM; multi-line or bare base64 accepted) |
| `APNS_USE_SANDBOX` | `true` | Sandbox vs. production APNs gateway |
| `ARC_DEVICE_STORE` | `<tmp>/arc-push-out/devices.runtime.json` | Device-token registry file |

`apns_configured` is `True` only when team id, key id, and private key are all
present; with `ARC_PUSH_MODE=apns` and all three set, `send()` posts a real
notification. The Vultr-related variables (`VULTR_INFERENCE_API_KEY`,
`VULTR_MODEL`, `VULTR_MAX_CONCURRENCY`, `VULTR_TIMEOUT`,
`VULTR_INFERENCE_BASE_URL`, `ARC_CORPUS_COLLECTION`) are read by the agent layer,
not `settings.py` — see [VULTR.md](VULTR.md). The `.env` is parsed by a minimal
stdlib loader that supports quoted multi-line values (for the PEM key); process
env always wins over the file, and tests blank the sensitive keys before import
so the suite can never make a paid LLM call.
