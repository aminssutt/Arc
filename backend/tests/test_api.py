"""API acceptance: BE.1 (/health), BE.4 (SSE conforms + heartbeat + resume),
BE.6 (validated, idempotent, state-checked intake), BE.11 (inject-fault E2E,
reset < 5 s). Runs the real app through its lifespan (real seeds, real tools).
"""
import asyncio
import json
import time

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app


@pytest.fixture()
async def client():
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.app = app
            yield c


async def _run_confirm_to_awaiting(client):
    r = await client.post("/api/demo/inject-fault", json={"scenario": "confirm"})
    assert r.status_code == 200, r.text
    orch = client.app.state.orchestrator
    await orch.join()
    assert orch.state == "awaiting_field_validation"
    return orch


def _body(orch, verdicts, cid="api-1"):
    import itertools
    return {
        "incident_id": orch.incident["id"],
        "client_event_id": cid,
        "submitted_at": "2026-07-05T09:33:00Z",
        # every detected failure gets a verdict (cycle a short list over all)
        "validations": [{"failure_id": f["id"], "verdict": v}
                        for f, v in zip(orch.incident["failures"], itertools.cycle(verdicts))],
        "measurements": [{"metric": "dc_voltage_v", "point": "busbar", "value": -43.9, "unit": "V"}],
    }


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_inject_validate_report_reset(client):
    orch = await _run_confirm_to_awaiting(client)

    r = await client.post("/api/validation", json=_body(orch, ["real"]))
    assert r.status_code == 200
    assert r.json()["result"] == "confirmed"
    await orch.join()

    types = [e["type"] for e in client.app.state.bus.history]
    assert "action_report_ready" in types and "incident_resolved" in types

    t0 = time.monotonic()
    r = await client.post("/api/demo/reset")
    assert r.status_code == 200 and r.json() == {"status": "idle"}
    assert time.monotonic() - t0 < 5.0                       # BE.11: reset < 5 s
    assert client.app.state.bus.history == []
    # system usable again immediately
    await _run_confirm_to_awaiting(client)


async def test_intake_idempotent_on_double_submit(client):
    orch = await _run_confirm_to_awaiting(client)
    body = _body(orch, ["real"], cid="dup-1")
    first = await client.post("/api/validation", json=body)
    assert first.status_code == 200
    events_after_first = len(client.app.state.bus.history)
    second = await client.post("/api/validation", json=body)  # double submit
    assert second.status_code == 200
    assert second.json() == first.json()                      # same answer
    await orch.join()
    dupes = [e for e in client.app.state.bus.history if e["type"] == "validation_received"]
    assert len(dupes) == 1                                    # no second state change


async def test_intake_rejects_wrong_state_and_bad_payload(client):
    r = await client.post("/api/validation", json={
        "incident_id": "INC-NONE", "client_event_id": "x",
        "submitted_at": "2026-07-05T09:00:00Z",
        "validations": [{"failure_id": "F1", "verdict": "real"}]})
    assert r.status_code == 409                               # nothing awaiting

    orch = await _run_confirm_to_awaiting(client)
    r = await client.post("/api/validation", json={"incident_id": orch.incident["id"]})
    assert r.status_code == 422                               # schema violation, explicit errors
    assert "validations" in json.dumps(r.json())


async def test_sse_stream_replays_conforms_and_resumes(event_validator):
    # Real uvicorn server: httpx's ASGITransport buffers full responses, so an
    # infinite SSE stream needs actual HTTP — which is also the honest BE.4 check.
    import uvicorn

    app = create_app()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8731, log_level="warning"))
    serve_task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.05)
    try:
        async with AsyncClient(base_url="http://127.0.0.1:8731") as http:
            r = await http.post("/api/demo/inject-fault", json={"scenario": "confirm"})
            assert r.status_code == 200, r.text
            orch = app.state.orchestrator
            await orch.join()

            async def read_events(path, count, headers=None):
                events = []
                async with http.stream("GET", path, headers=headers) as resp:
                    assert resp.headers["content-type"].startswith("text/event-stream")
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            events.append(json.loads(line[6:]))
                            if len(events) >= count:
                                break
                return events

            # two CONCURRENT clients receive the same replayed history (BE.4)
            n = len(app.state.bus.history)
            first, second = await asyncio.wait_for(
                asyncio.gather(read_events("/api/stream", n), read_events("/api/stream", n)),
                timeout=15)
            assert [e["id"] for e in first] == [e["id"] for e in second]
            for e in first:                        # schema-conformant on the wire
                assert not list(event_validator.iter_errors(e))

            # Last-Event-ID resume (header form, like a real EventSource reconnect)
            resumed = await asyncio.wait_for(
                read_events("/api/stream", 1, headers={"Last-Event-ID": first[2]["id"]}),
                timeout=15)
            assert resumed[0]["id"] == first[3]["id"]
    finally:
        server.should_exit = True
        await serve_task
