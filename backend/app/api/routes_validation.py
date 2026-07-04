"""POST /api/validation (BE.6) — the mobile veracity check intake.

- Body validated against contracts/validation_event.schema.json -> 422 with the
  schema errors on violation (the contract is enforced, not assumed).
- Idempotent on client_event_id: a resend returns the ORIGINAL 200 response and
  causes no second state change (acceptance).
- 409 when the incident is not awaiting field validation.
"""
import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from jsonschema import Draft202012Validator

from backend.app import orchestrator as st

router = APIRouter()
_validator: Draft202012Validator | None = None


def _get_validator(request: Request) -> Draft202012Validator:
    global _validator
    if _validator is None:
        schema_path = request.app.state.settings.contracts_dir / "validation_event.schema.json"
        _validator = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))
    return _validator


@router.post("/api/validation")
async def receive_validation(request: Request):
    body = await request.json()
    errors = [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
              for e in _get_validator(request).iter_errors(body)]
    if errors:
        return JSONResponse(status_code=422, content={"detail": errors})

    idempotency: dict = request.app.state.idempotency
    cid = body["client_event_id"]
    if cid in idempotency:  # double submit -> same answer, no state change
        return JSONResponse(status_code=200, content=idempotency[cid])

    orch = request.app.state.orchestrator
    if orch.state != st.AWAITING or orch.incident is None:
        return JSONResponse(status_code=409, content={
            "detail": f"no incident awaiting field validation (state: {orch.state})"})
    if body["incident_id"] != orch.incident["id"]:
        return JSONResponse(status_code=409, content={
            "detail": f"incident_id mismatch: active incident is {orch.incident['id']}"})

    response = await orch.handle_validation(body)
    idempotency[cid] = response
    return JSONResponse(status_code=200, content=response)
