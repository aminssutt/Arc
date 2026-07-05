"""Demo control endpoints (BE.11 + DEMO.2).

POST /api/demo/inject-fault {"scenario": "confirm"|"pivot"} or
                            {"alarm_code": "...", "site_id": "..."}
    Scenario mode replays the SEEDED signal timeline
    (/data/scenarios/run_<name>_signals.jsonl) through the real Watchdog path —
    both demo runs are reproducible deterministically from seeds (#55).
    Alarm-code mode synthesizes a minimal breach timeline for any family in the
    alarm dictionary (debounce satisfied in event time).
POST /api/demo/reset
    Returns the system to idle (< 5 s): orchestrator, watchdog episodes, event
    history, idempotency cache, crew bookings.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app.seeds import SIGNED_METRICS

router = APIRouter()

DEMO_SITE = "PAR-021-NORD"


def _synthetic_timeline(rule: dict, site_id: str, equipment_id: str | None,
                        raw_trap: str | None) -> list[dict]:
    """Two breach signals debounce_s apart in EVENT time (wall time: instant)."""
    t0 = datetime.now(timezone.utc)
    t1 = t0 + timedelta(seconds=rule["debounce_s"] + 1)
    magnitude = {
        "lt": rule["threshold_value"] - 1, "lte": rule["threshold_value"],
        "gt": rule["threshold_value"] + 1, "gte": rule["threshold_value"],
        "eq": rule["threshold_value"], "neq": rule["threshold_value"] + 1,
    }[rule["threshold_op"]]
    value = -magnitude if rule["signal"] in SIGNED_METRICS else magnitude
    iso = lambda t: t.isoformat(timespec="seconds").replace("+00:00", "Z")
    base = {"site_id": site_id, "signal": rule["signal"], "value": value}
    if equipment_id:
        base["equipment_id"] = equipment_id
    if raw_trap:
        base["trap"] = raw_trap
    return [{**base, "ts": iso(t0)}, {**base, "ts": iso(t1)}]


@router.post("/api/demo/inject-fault")
async def inject_fault(request: Request):
    body = await request.json() if int(request.headers.get("content-length") or 0) else {}
    seeds = request.app.state.seeds
    orch = request.app.state.orchestrator

    if orch.state != "idle":
        return JSONResponse(status_code=409, content={
            "detail": f"an incident is already active (state: {orch.state}); reset first"})

    scenario = body.get("scenario")
    if scenario in seeds.scenarios:
        signals = seeds.scenarios[scenario]          # DEMO.2: deterministic from seeds
    elif body.get("alarm_code"):
        rule = seeds.alarm_dictionary.get(body["alarm_code"])
        if rule is None:
            return JSONResponse(status_code=422, content={"detail": f"unknown alarm_code '{body['alarm_code']}'"})
        signals = _synthetic_timeline(rule, body.get("site_id", DEMO_SITE),
                                      body.get("equipment_id"),
                                      seeds.raw_trap_for(rule["alarm_code"]))
    else:
        return JSONResponse(status_code=422, content={
            "detail": f"pass {{\"scenario\": one of {sorted(seeds.scenarios)}}} or {{\"alarm_code\": ...}}"})

    await request.app.state.watchdog.ingest_batch(signals)
    incident_id = orch.incident["id"] if orch.incident else None
    return {"status": "injected", "scenario": scenario or body.get("alarm_code"),
            "signals_replayed": len(signals), "incident_id": incident_id, "state": orch.state}


@router.post("/api/demo/reset")
async def reset(request: Request):
    request.app.state.orchestrator.reset()
    request.app.state.watchdog.reset()
    request.app.state.bus.reset()
    request.app.state.push_service.reset()
    request.app.state.idempotency.clear()
    request.app.state.dispatch_tool.release_all()
    return {"status": "idle"}
