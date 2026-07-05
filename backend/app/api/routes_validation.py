"""POST /api/validation (BE.6) — the mobile veracity check intake.

Two request shapes are accepted, both converging on the frozen contract body:
- FULL (frozen validation_event.schema.json): {incident_id, client_event_id,
  submitted_at, validations[], measurements?, technician?}.
- PITCH (the iOS demo card, additive): {incident_id, status:"confirmed"} or
  {incident_id, status:"rejected", measurement:{value, unit}}. This is expanded
  into a schema-valid full body (all failures verdict=real on confirm; the
  load-bearing failure verdict=false + the counter-measurement on reject, which
  drives the existing pivot re-diagnosis).

- Body validated against contracts/validation_event.schema.json -> 422 on
  violation. - Idempotent on client_event_id (same key => original 200, no second
  state change). - 409 when the incident is not awaiting field validation.
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app import orchestrator as st

router = APIRouter()
_validator = None


def _get_validator(request: Request):
    global _validator
    if _validator is None:
        from jsonschema import Draft202012Validator
        schema_path = request.app.state.settings.contracts_dir / "validation_event.schema.json"
        _validator = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))
    return _validator


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _is_pitch_shape(raw: dict) -> bool:
    """The iOS demo card: a `status` verb and no explicit `validations` list."""
    return isinstance(raw, dict) and "status" in raw and "validations" not in raw


def _expand_pitch(raw: dict, orch) -> tuple[dict | None, str | None]:
    """Expand the pitch card into a frozen-contract validation body."""
    status = raw.get("status")
    if status not in ("confirmed", "rejected"):
        return None, "status must be 'confirmed' or 'rejected'"
    incident_id = raw.get("incident_id")
    if not incident_id:
        return None, "incident_id is required"

    inc = orch.incident or {}
    seeds = getattr(orch, "seeds", None)
    failures = inc.get("failures", []) or []
    vreqs = ((inc.get("diagnostic") or {}).get("verification_requests")) or []
    measurement = raw.get("measurement") or {}
    unit = measurement.get("unit")

    # The failure a counter-measurement refutes is the one physically read in that
    # measurement's UNIT (e.g. a "V" reading refutes the busbar dc_voltage failure,
    # never the rectifier module_status one). This binds by physical dimension, so
    # it is robust to metric-name drift and to which failure the verification_request
    # happened to name. Falls back to a numeric-valued failure, then the verified
    # failure, then the first.
    lb = _failure_for_measurement(failures, seeds, unit, vreqs) if status == "rejected" else None
    if lb is None:
        if vreqs:
            lb = next((f for f in failures if f["id"] == vreqs[0].get("failure_id")), None)
        if lb is None:
            lb = failures[0] if failures else None
    lb_id = lb["id"] if lb else "F1"
    metric = (measurement.get("metric") or (lb.get("metric") if lb else "")
              or (vreqs[0].get("metric") if vreqs else "") or "dc_voltage_v")
    point = (lb.get("equipment") if lb else "") or (vreqs[0].get("point") if vreqs else "") or ""

    if not failures:
        validations = [{"failure_id": lb_id, "verdict": "real" if status == "confirmed" else "false"}]
    elif status == "confirmed":
        validations = [{"failure_id": f["id"], "verdict": "real"} for f in failures]
    else:
        validations = [{"failure_id": f["id"], "verdict": "false" if f["id"] == lb_id else "real"}
                       for f in failures]

    body: dict = {
        "incident_id": incident_id,
        "client_event_id": raw.get("client_event_id") or f"pitch-{incident_id}-{status}",
        "submitted_at": raw.get("submitted_at") or _now_iso(),
        "validations": validations,
        "measurements": [],
    }
    if raw.get("technician"):
        body["technician"] = raw["technician"]

    if status == "rejected":
        if "value" not in measurement or "unit" not in measurement:
            return None, "rejected requires measurement {value, unit}"
        meas = {"metric": metric, "value": measurement["value"], "unit": measurement["unit"]}
        if point:
            meas["point"] = point
        body["measurements"] = [meas]
    return body, None


def _alarm_rule(seeds, failure: dict):
    """The alarm-dictionary rule for a failure (via alarm_code / trap_map / code)."""
    if seeds is None:
        return None
    code = failure.get("code", "")
    alarm_code = (failure.get("alarm_code")
                  or (seeds.trap_map.get(code, {}) or {}).get("alarm_code")
                  or code)
    return seeds.alarm_dictionary.get(alarm_code)


def _failure_for_measurement(failures: list[dict], seeds, unit, vreqs):
    """The failure a field measurement refutes, chosen by physical unit."""
    if unit:
        for f in failures:
            rule = _alarm_rule(seeds, f)
            if rule and str(rule.get("unit", "")).lower() == str(unit).lower():
                return f
    for f in failures:  # a field number refutes a numeric-telemetry failure
        v = f.get("value")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return f
    if vreqs:
        fid = vreqs[0].get("failure_id")
        m = next((f for f in failures if f["id"] == fid), None)
        if m:
            return m
    return failures[0] if failures else None


@router.post("/api/validation")
async def receive_validation(request: Request):
    raw = await request.json()
    orch = request.app.state.orchestrator

    if _is_pitch_shape(raw):
        body, err = _expand_pitch(raw, orch)
        if err:
            return JSONResponse(status_code=422, content={"detail": [err]})
    else:
        body = raw

    errors = [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
              for e in _get_validator(request).iter_errors(body)]
    if errors:
        return JSONResponse(status_code=422, content={"detail": errors})

    idempotency: dict = request.app.state.idempotency
    cid = body["client_event_id"]
    if cid in idempotency:  # double submit -> same answer, no state change
        return JSONResponse(status_code=200, content=idempotency[cid])

    if orch.state != st.AWAITING or orch.incident is None:
        return JSONResponse(status_code=409, content={
            "detail": f"no incident awaiting field validation (state: {orch.state})"})
    if body["incident_id"] != orch.incident["id"]:
        return JSONResponse(status_code=409, content={
            "detail": f"incident_id mismatch: active incident is {orch.incident['id']}"})

    response = await orch.handle_validation(body)
    idempotency[cid] = response
    return JSONResponse(status_code=200, content=response)
