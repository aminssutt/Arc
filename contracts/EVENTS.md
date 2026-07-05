# Arc event contract v1 — events, push payload, validation event

> **Status: DRAFT → FROZEN on merge of this PR** (P0.6, #6). After freeze, any change
> = PR + immediate Discord ping + producer AND all consumers approve (see CONTRIBUTING).
> Producer: simerugby. Consumers: frontend (SSE), iOS (push + validation POST),
> agents/orchestrator (event emission). Machine-readable schemas live next to this file:
> `events.schema.json`, `push_payload.schema.json`, `validation_event.schema.json`.

## Transport

- **SSE** — `GET /api/stream` (`text/event-stream`). Each event is written as:

  ```
  id: <envelope.id>
  event: <envelope.type>
  data: <the full envelope as one-line JSON>
  ```

  The `data:` field carries the **entire envelope**, so clients may ignore SSE framing
  and parse `data` alone. Heartbeat = comment line `: hb` every 15 s. Reconnect resume
  via standard `Last-Event-ID` header (server replays events after that id).
- **POST /api/validation** — the iOS app posts the validation event (schema below).
  Idempotent on `client_event_id`: a resend returns `200` with the original result.
- **Push** — APNs-shaped payload (schema below). Demo path is `xcrun simctl push`
  with the exact same JSON; real APNs is flag-gated (INT.7).

## Envelope (every SSE event)

```json
{"seq": 7, "id": "INC-DEMO-001-0007", "ts": "2026-07-05T09:24:10Z",
 "incident_id": "INC-DEMO-001", "type": "diagnostic_ready", "data": { }}
```

- `seq` — monotonically increasing per incident, no gaps in a replay.
- `id` — globally unique, used as the SSE `id:` for resume.
- `type` — one of the 15 event types below. `data` shape depends on `type`.

## Shared objects

- **citation** `{"doc_id": "V4", "title": "NetSure control manual", "page": 12, "claim": "rectifier-lost alarm signature"}` —
  `doc_id` keys into `validation/DATA_MANIFEST.md` source IDs. Every load-bearing claim
  in agent output carries ≥1 citation that resolves.
- **failure** `{"id": "F1", "code": "alarmMajorRectifier", "severity": "major", "equipment": "rectifier-2", "metric": "module_status", "value": "fail", "first_seen": "..."}` —
  `severity` per X.733: `critical|major|minor|warning|indeterminate|cleared`.
  `failure.id` is the key the technician's per-failure verdict references.
- **site** `{"id": "PAR-021-NORD", "name": "Paris Nord macro site", "lat": 48.8969, "lon": 2.3383, "address": "..."}`
- **family** — `energy | environment | rf | transport`.
- **agent** — `correlation | root_cause | validation | remediation | cost_inventory_dispatch`.

## Event catalog (15 types)

| # | type | Emitted by | When |
|---|---|---|---|
| 1 | `fault_detected` | Watchdog | debounced trigger fires |
| 2 | `phase_started` | Orchestrator | phase 1 or 2 begins (`cause: initial\|pivot`) |
| 3 | `agent_started` | Orchestrator | an agent begins |
| 4 | `agent_completed` | Orchestrator | an agent returns (`status: ok\|error\|timeout`) |
| 5 | `retrieval_performed` | any retrieving agent | each retrieval pass (`pass` number + citations) |
| 6 | `diagnostic_ready` | Orchestrator (after Phase 1) | ranked causes + urgency + verification requests |
| 7 | `push_sent` | Push service | notification dispatched (`method: simctl\|apns`) |
| 8 | `awaiting_field_validation` | Orchestrator | waiting on the technician |
| 9 | `validation_received` | Validation intake | technician's POST accepted (echo) |
| 10 | `validation_result` | Validation agent | `result: confirmed\|pivot` + contradictions |
| 11 | `remediation_ready` | Remediation agent | cited procedure + safety steps + parts |
| 12 | `action_report_ready` | Orchestrator (after Phase 2) | the prioritized action report |
| 13 | `doc_requested` | any agent | needed doc missing from corpus |
| 14 | `incident_resolved` | Orchestrator | terminal state |
| 15 | `responder_matched` | Orchestrator | matchmaking narrowed the roster to one technician (after diagnostic_ready, initial phase 1) |

### 1. fault_detected
```json
{"site": {"id": "PAR-021-NORD", "name": "Paris Nord macro site", "lat": 48.8969, "lon": 2.3383},
 "family": "energy",
 "failures": [{"id": "F1", "code": "alarmMajorRectifier", "severity": "major", "equipment": "rectifier-2", "metric": "module_status", "value": "fail", "first_seen": "2026-07-05T09:00:00Z"},
              {"id": "F2", "code": "DC_UNDERVOLTAGE", "severity": "major", "equipment": "busbar", "metric": "dc_voltage_v", "value": -45.0, "first_seen": "2026-07-05T09:12:00Z"}],
 "trigger": {"rule": "undervoltage_major", "debounce_s": 120, "triggered_at": "2026-07-05T09:20:00Z"}}
```
Failures may be **added during Phase 1** (e.g. a thermal signal that corroborates mid-run):
the authoritative failures list for the human loop is the one in the **push payload /
`awaiting_field_validation`**, not `fault_detected`.

### 2. phase_started
```json
{"phase": 1, "cause": "initial"}
```
`cause: "pivot"` when the validation agent contradicted Phase-1 output and the
orchestrator loops back.

### 3. agent_started / 4. agent_completed
```json
{"agent": "root_cause", "phase": 1}
{"agent": "root_cause", "phase": 1, "status": "ok", "duration_ms": 41200, "summary": "top cause: rectifier module failure (0.87)"}
```

### 5. retrieval_performed
```json
{"agent": "root_cause", "pass": 2, "query": "VRLA discharge time to LVD -48V string",
 "results": [{"doc_id": "FIST-3-6", "title": "FIST 3-6 Battery Maintenance", "page": 14, "score": 0.81}]}
```
`pass ≥ 2` on the same incident is the multi-retrieve compliance proof — emit one event
per pass, never batch.

### 6. diagnostic_ready
```json
{"correlation": {"site_id": "PAR-021-NORD", "equipment": ["rectifier-2", "busbar"], "blast_radius": "all 3 sectors on battery reserve"},
 "causes": [{"rank": 1, "cause": "rectifier module failure (rectifier-2)", "confidence": 0.87,
             "citations": [{"doc_id": "V4", "page": 12, "claim": "rectifier-lost signature"}]},
            {"rank": 2, "cause": "grid loss", "confidence": 0.06, "rejected_because": "alarmACmains never fired; no area outage",
             "citations": [{"doc_id": "V6", "page": 3, "claim": "mains alarm definition"}]}],
 "urgency": {"kind": "time_to_lvd", "estimate_min": 210, "basis": "synthesis from NASA capacity curves scaled per FIST 3-6 Table 1 (labeled synth)",
             "citations": [{"doc_id": "FIST-3-6", "page": 14, "claim": "float/discharge criteria"}]},
 "failures": [],
 "verification_requests": [{"failure_id": "F2", "action": "measure busbar DC voltage with a DMM", "point": "busbar", "metric": "dc_voltage_v"}]}
```
`failures` (optional) lists failures added since `fault_detected` (full failure objects).
`rank` orders causes by operational probability: `rank: 1` is the most probable, and `confidence` is strictly decreasing with rank (rank *i* always outranks *i+1*).

### 7. push_sent
```json
{"method": "simctl", "payload": { "<push payload, schema below>": "..." }}
```

### 8. awaiting_field_validation
```json
{"failure_ids": ["F1", "F2", "F3"],
 "requested_measurements": [{"metric": "dc_voltage_v", "point": "busbar", "unit": "V"}]}
```

### 9. validation_received
Echo of the accepted POST (same shape as the validation event's `data` minus transport
fields):
```json
{"validations": [{"failure_id": "F1", "verdict": "real", "note": "module LED dark"},
                 {"failure_id": "F2", "verdict": "false"}],
 "measurements": [{"metric": "dc_voltage_v", "point": "busbar", "value": -53.9, "unit": "V"}],
 "technician": {"id": "tech-07"}, "client_event_id": "ios-8c1f"}
```

### 10. validation_result
```json
{"result": "pivot", "rationale": "field measurement -53.9 V contradicts telemetry -45.0 V; plant is healthy",
 "contradictions": [{"failure_id": "F2", "telemetry": -45.0, "measured": -53.9, "unit": "V"}]}
```
On `pivot`, the orchestrator re-enters Phase 1 (`phase_started {phase:1, cause:"pivot"}`)
with the field measurement as ground truth. If existing field data suffices, the
re-diagnosis MAY proceed to Phase 2 without a second push loop.

> **Decision wording:** the frozen wire value is `pivot` (the `result` enum). A validation
> agent may reason in other terms internally (e.g. "contradicted"); its adapter maps that
> to `pivot` before emit — the enum is never changed.

### 11. remediation_ready
```json
{"procedure": {"title": "Replace failed rectifier module",
   "steps": [{"n": 1, "text": "Verify plant on N-1 redundancy before extraction",
              "citations": [{"doc_id": "V4", "page": 18, "claim": "hot-swap procedure"}]}],
   "safety": [{"text": "DC plant lockout per site SOP; insulated tools only",
               "citations": [{"doc_id": "UFC-3-540-07", "page": 33, "claim": "DC plant safety"}]}]},
 "parts": [{"part_no": "APR48-3G", "description": "Eaton 48V rectifier module", "qty": 1}]}
```

### 12. action_report_ready
```json
{"report": {
  "diagnosis": {"cause": "rectifier module failure (rectifier-2)", "confidence": 0.91,
                "citations": [{"doc_id": "V4", "page": 12, "claim": "alarm signature match"}]},
  "actions": [{"priority": "P1", "action": "Replace rectifier-2 with APR48-3G from Paris-Est stock", "owner": "crew PWR-2", "eta": "2026-07-05T11:30:00Z"},
              {"priority": "P2", "action": "Load-test battery string A after plant restore", "owner": "crew PWR-2", "eta": "2026-07-05T13:00:00Z"}],
  "cost": {"currency": "USD", "intervention": 1165.50, "avoided": 6800.0,
           "notes": "part 769.04 + 2h labor @35.73 + truck roll 325.00 = 1165.50; avoided = downtime 5.00/min x 240 min (gold restore target) x 1.5 weight + SLA breach penalty 5000.00 = 6800.00",
           "sla": {"clock": "Lumen Critical: notify 15 min, TTR High < 4 h", "citations": [{"doc_id": "O1", "page": 2, "claim": "TTR clock"}]}},
  "inventory": {"part_no": "APR48-3G", "qty_available": 3, "location": "Paris-Est depot", "unit_price": 769.04},
  "dispatch": {"booking_id": "BK-2107", "crew": "PWR-2", "skill": "dc_power", "eta": "2026-07-05T11:30:00Z"},
  "honesty_notes": [], 
  "citations": [{"doc_id": "V4", "page": 12, "claim": "rectifier alarm signature match"},
                {"doc_id": "UFC-3-540-07", "page": 33, "claim": "DC plant lockout safety step"}]}}
```
`citations` aggregates every citation in the report. `honesty_notes` states unresolved
contradictions or synth-labeled values out loud (never hidden).

### 13. doc_requested
```json
{"agent": "root_cause", "description": "vendor thermal derating curve for AirScale radio", "query": "radio auto-shutdown threshold", "status": "missing"}
```

### 14. incident_resolved
```json
{"summary": "rectifier-2 replaced; plant back on float -54.4 V", "total_duration_s": 8460, "outcome": "resolved"}
```

### 15. responder_matched
```json
{"fault": {"family": "energy", "equipment_class": "rectifier", "code": "PWR-DC-UV", "region": "IDF-North"},
 "difficulty": "medium",
 "chosen": {"employee_id": "EMP-001", "name": "Nadia Cherif", "tier": "senior", "region": "IDF-North",
            "matched_skills": ["power", "rectifier"], "score": 0.8991,
            "reason": "medium task -> senior profile; competence 1.00 (power,rectifier); zone IDF-North",
            "out_of_zone": false},
 "candidates": [{"employee_id": "EMP-001", "name": "Nadia Cherif", "tier": "senior", "region": "IDF-North", "matched_skills": ["power", "rectifier"], "score": 0.8991, "out_of_zone": false},
                {"employee_id": "EMP-006", "name": "Karim Haddad", "tier": "confirmé", "region": "IDF-East", "matched_skills": ["power", "rectifier"], "score": 0.9738},
                {"employee_id": "EMP-004", "name": "Thomas Berger", "tier": "junior", "region": "IDF-North", "matched_skills": ["power", "rectifier"], "score": 0.8102}]}
```
Emitted by the Orchestrator right after `diagnostic_ready` on the **initial** phase 1
(before `push_sent`). The deterministic matchmaking (skill + zone, difficulty-routed)
narrows the roster to ONE technician: `candidates` is the roster considered — render
it as the roster tightening — and `chosen` is the retained technician with the
skill+zone `reason`. Candidates may sit out of zone with a higher raw `score`; the
`chosen` is the best **in-zone** qualified person (`out_of_zone` flags the fallback
when nobody in-zone is available). NOT emitted on a pivot re-diagnosis. The push then
routes to `chosen` (their registered device — see Push payload).

## Push payload (APNs-shaped; simctl demo path)

```json
{"Simulator Target Bundle": "com.arc.operator",
 "aps": {"alert": {"title": "Arc — PAR-021-NORD: energy fault",
                   "body": "3 detected failures await field validation"},
         "sound": "default", "category": "ARC_VALIDATION"},
 "incident_id": "INC-DEMO-001",
 "site": {"id": "PAR-021-NORD", "name": "Paris Nord macro site", "lat": 48.8969, "lon": 2.3383, "address": "Rue de la Chapelle, 75018 Paris"},
 "family": "energy",
 "failures": [{"id": "F1", "code": "alarmMajorRectifier", "severity": "major", "equipment": "rectifier-2"},
              {"id": "F2", "code": "DC_UNDERVOLTAGE", "severity": "major", "equipment": "busbar"},
              {"id": "F3", "code": "HIGH_TEMP", "severity": "warning", "equipment": "cabinet"}]}
```

- `"Simulator Target Bundle"` is **simctl-only** (lets `xcrun simctl push booted <file>`
  work without passing a bundle id); real APNs ignores/omits it.
- Bundle id `com.arc.operator` = standardized value — real-device signed & APNs-sandbox verified (daniwavy5032, 2026-07-04).

## Validation event — `POST /api/validation`

```json
{"incident_id": "INC-DEMO-001",
 "client_event_id": "ios-8c1f",
 "submitted_at": "2026-07-05T09:41:00Z",
 "technician": {"id": "tech-07", "name": "on-call field tech"},
 "validations": [{"failure_id": "F1", "verdict": "real", "note": "module LED dark"},
                 {"failure_id": "F2", "verdict": "real"},
                 {"failure_id": "F3", "verdict": "real"}],
 "measurements": [{"metric": "dc_voltage_v", "point": "busbar", "value": -44.8, "unit": "V"}]}
```

- `verdict` ∈ `real | false` per failure — mixed verdicts are expected and legal.
- `client_event_id` is the idempotency key: same key ⇒ same 200 response, no state change.
- Responses: `200` accepted (body `{"status":"accepted","incident_id":...}`),
  `409` incident not awaiting validation, `422` schema violation.

## Fixtures

`mock_stream/run_confirm.ndjson` and `mock_stream/run_pivot.ndjson` are full envelope
sequences for the two demo runs (values pinned to `validation/GROUND_TRUTH_SCENARIOS.md`);
`mock_stream/replay.py` serves them over real SSE at `/api/stream` (see its header for
usage). `push_fixtures/` holds the exact push payloads + the documented simctl command.
Frontend and iOS build against these with zero backend; swapping to real = base-URL flip.

## Frontend integration (additive endpoints — NOT frozen, backend-owned)

The frozen event/push/validation contracts above are the source of truth. These
extra HTTP endpoints are additive helpers the web control-room and the iOS app
use; they never change the frozen shapes.

### Live + replay stream
- `GET /api/stream` (SSE) — live events; full history replayed on connect,
  `Last-Event-ID` resume. Offline: `python contracts/mock_stream/replay.py
  run_confirm.ndjson` serves the same wire at `/api/stream` (base-URL flip only).
- Trigger: `POST /api/demo/inject-fault` `{"scenario":"confirm"|"pivot"}` (or
  `{"alarm_code":"...","site_id":"..."}`). Reset: `POST /api/demo/reset`.

### Clickable citations — `GET /api/citations/{doc_id}?claim=<str>`
Every load-bearing `citation` in the stream is `{"doc_id","claim"}` (plus optional
`title`,`page`). To open a source chip, call this endpoint with that exact
`doc_id` and `claim`:

```
GET /api/citations/V4?claim=rectifier-lost%20alarm%20signature
200 {
  "doc_id": "V4",
  "title": "Vertiv NetSure 2100 -48VDC manual",
  "section": "Plant architecture and N+1 redundancy",
  "snippet": "…the bus stays at float and the batteries are not called upon while N modules still carry the load. This is why a lone rectifier-lost alarm…",
  "source_path": "corpus/vendor/v4_netsure2100.pdf"
}
```
- Resolvable `doc_id`s: `V4, S1, V6, FIST-3-6, TM-5-693, UFC-3-540-07, O1, O5, S2, V2`
  (the pivot's rank-1 cites **S2** "measurement point failure" + **V2** "supervision module").
  O5 is served from an inline `text` field (`source_path: "(inline)"`); the `.pdf`
  paths are plain-text markdown, served as text.
- `404` (clean) when the `doc_id` is unknown or its source is not materialised.
  `retrieval_performed.results[].doc_id` are search hits — only `citation` objects
  (on causes, steps, report) are guaranteed resolvable.

### Matchmaking panel — the `responder_matched` event
Render event #15 (`responder_matched`, above) as the roster tightening: `candidates`
is the pool considered, `chosen` is the retained technician with the skill+zone
`reason`. It arrives between `diagnostic_ready` and `push_sent` on the initial
phase 1 (never on a pivot).

### iOS device registration — `POST /api/devices`
`{"device_token": str, "platform": "ios", "operator_id": str|null}` → `204`. Lets
`diagnostic_ready` route a real APNs push to the matched operator's iPhone.

### Field validation from the phone — `POST /api/validation`
Accepts the frozen full body (above) AND the iOS card shape:
`{"incident_id","status":"confirmed"}` or
`{"incident_id","status":"rejected","measurement":{"value","unit"}}` → `200`
`{"status":"accepted","incident_id","result":"confirmed"|"pivot"}`. A `rejected`
counter-measurement drives the pivot re-diagnosis.
