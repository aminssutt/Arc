"""Demo control endpoints (BE.11).

POST /api/demo/inject-fault {"scenario": "confirm"|"pivot"} or
                            {"alarm_code": "...", "site_id": "..."}
    Feeds a signal timeline into the Watchdog (event-time debounce satisfied),
    driving the REAL detection path end-to-end to a FaultEvent. The confirm and
    pivot scenarios inject the same opening (per the ground-truth runs — the
    difference is the technician's answer); arbitrary alarm codes exercise any
    family in the alarm dictionary.
POST /api/demo/reset
    Returns the system to idle (< 5 s): orchestrator, watchdog episodes, event
    history, idempotency cache, crew bookings.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

DEMO_SITE = "SITE-PAR-014"


def _timeline(rule: dict, site_id: str, equipment_id: str | None) -> list[dict]:
    """Two breach signals debounce_s apart in EVENT time (wall time: instant)."""
    t0 = datetime.now(timezone.utc)
    t1 = t0 + timedelta(seconds=rule["debounce_s"] + 1)
    breach_value = {
        "lt": rule["threshold_value"] - 1, "lte": rule["threshold_value"],
        "gt": rule["threshold_value"] + 1, "gte": rule["threshold_value"],
        "eq": rule["threshold_value"], "neq": rule["threshold_value"] + 1,
    }[rule["threshold_op"]]
    iso = lambda t: t.isoformat(timespec="seconds").replace("+00:00", "Z")
    base = {"site_id": site_id, "signal": rule["signal"], "value": breach_value}
    if equipment_id:
        base["equipment_id"] = equipment_id
    return [{**base, "ts": iso(t0)}, {**base, "ts": iso(t1)}]


@router.post("/api/demo/inject-fault")
async def inject_fault(request: Request):
    body = await request.json() if int(request.headers.get("content-length") or 0) else {}
    seeds = request.app.state.seeds
    orch = request.app.state.orchestrator

    scenario = body.get("scenario")
    if scenario in ("confirm", "pivot"):
        alarm_code, site_id, equipment_id = "PWR-DC-UV", DEMO_SITE, "EQ-PAR-014-RECT-1"
    elif body.get("alarm_code"):
        alarm_code, site_id = body["alarm_code"], body.get("site_id", DEMO_SITE)
        equipment_id = body.get("equipment_id")
    else:
        return JSONResponse(status_code=422, content={
            "detail": "pass {\"scenario\": \"confirm\"|\"pivot\"} or {\"alarm_code\": ...}"})

    rule = seeds.alarm_dictionary.get(alarm_code)
    if rule is None:
        return JSONResponse(status_code=422, content={"detail": f"unknown alarm_code '{alarm_code}'"})
    if orch.state != "idle":
        return JSONResponse(status_code=409, content={
            "detail": f"an incident is already active (state: {orch.state}); reset first"})

    await request.app.state.watchdog.ingest_batch(_timeline(rule, site_id, equipment_id))
    incident_id = orch.incident["id"] if orch.incident else None
    return {"status": "injected", "scenario": scenario or alarm_code,
            "incident_id": incident_id, "state": orch.state}


@router.post("/api/demo/reset")
async def reset(request: Request):
    request.app.state.orchestrator.reset()
    request.app.state.watchdog.reset()
    request.app.state.bus.reset()
    request.app.state.idempotency.clear()
    request.app.state.dispatch_tool.release_all()
    return {"status": "idle"}
