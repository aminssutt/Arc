"""GET /api/stream (BE.4) — SSE broadcast of orchestrator events.

Same wire semantics as contracts/mock_stream/replay.py (heartbeat comments,
`data:` = full envelope, Last-Event-ID resume via header or ?lastEventId=),
so the frontend swaps mock -> real by changing the base URL only.
"""
import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.app.bus import EventBus

router = APIRouter()


@router.get("/api/stream")
async def stream(request: Request):
    bus: EventBus = request.app.state.bus
    heartbeat_s: float = request.app.state.settings.heartbeat_s
    last_event_id = request.headers.get("last-event-id") or request.query_params.get("lastEventId")

    async def gen():
        queue = bus.subscribe()
        try:
            for envelope in bus.replay_after(last_event_id):  # resume (INT.5)
                yield EventBus.sse_format(envelope)
            while True:
                try:
                    envelope = await asyncio.wait_for(queue.get(), timeout=heartbeat_s)
                    yield EventBus.sse_format(envelope)
                except asyncio.TimeoutError:
                    yield ": hb\n\n"
                if await request.is_disconnected():
                    return
        finally:
            bus.unsubscribe(queue)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
