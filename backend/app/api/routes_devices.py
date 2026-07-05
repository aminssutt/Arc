"""POST /api/devices (INT.7) — register an APNs device token.

Body ``{"device_token": str, "platform": "ios", "operator_id": str|null}`` -> 204.
The token is stored (in-memory + .runtime file) so a diagnostic_ready push reaches
the matched technician's real iPhone. Additive endpoint; no contract change.
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

router = APIRouter()


@router.post("/api/devices")
async def register_device(request: Request):
    body = await request.json() if int(request.headers.get("content-length") or 0) else {}
    token = (body.get("device_token") or "").strip()
    if not token:
        return JSONResponse(status_code=422, content={"detail": "device_token is required"})
    request.app.state.device_store.register(
        token,
        platform=body.get("platform") or "ios",
        operator_id=body.get("operator_id"),
    )
    return Response(status_code=204)
