"""Demo-alignment acceptance: the matchmaking narrowing event is emitted and
schema-valid, the push payload carries NO confidence score and routes to the
matched operator, and POST /api/validation accepts the iOS pitch card shape
(confirmed / rejected+measurement) on top of the frozen full body.
"""
import json

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.device_store import DeviceStore
from backend.app.main import create_app
from backend.app.push_service import PushService
from backend.app.settings import Settings


@pytest.fixture()
async def client():
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.app = app
            yield c


async def _to_awaiting(client, scenario="confirm"):
    r = await client.post("/api/demo/inject-fault", json={"scenario": scenario})
    assert r.status_code == 200, r.text
    orch = client.app.state.orchestrator
    await orch.join()
    assert orch.state == "awaiting_field_validation"
    return orch


# -- matchmaking narrowing event ------------------------------------------------
async def test_responder_matched_emitted_and_schema_valid(client, event_validator):
    await _to_awaiting(client)
    history = client.app.state.bus.history
    rm = [e for e in history if e["type"] == "responder_matched"]
    assert len(rm) == 1, "exactly one responder_matched on the initial phase 1"
    data = rm[0]["data"]
    assert data["chosen"]["employee_id"] and data["chosen"]["name"]
    assert data["chosen"].get("reason")                          # skill+zone rationale
    assert len(data["candidates"]) >= 1                          # roster considered (narrowing)
    for c in data["candidates"]:                                 # each renders name/skill/zone
        assert c["name"] and "region" in c and "matched_skills" in c
    assert not list(event_validator.iter_errors(rm[0]))          # frozen contract satisfied

    # ordering: responder_matched sits after diagnostic_ready, before push_sent
    types = [e["type"] for e in history]
    assert types.index("diagnostic_ready") < types.index("responder_matched") < types.index("push_sent")


async def test_push_payload_has_no_confidence_and_carries_site(client):
    orch = await _to_awaiting(client)
    push = [e for e in client.app.state.bus.history if e["type"] == "push_sent"][0]
    payload = push["data"]["payload"]
    assert "confidence" not in json.dumps(payload)              # never leaks the score
    assert payload["site"]["id"] == "PAR-021-NORD"
    assert payload["family"] == "energy" and payload["failures"]
    assert payload["aps"]["category"] == "ARC_VALIDATION"


# -- push routed to the matched operator's device ------------------------------
async def test_push_routes_to_matched_operator_token(tmp_path, bus, seeds):
    store = DeviceStore(tmp_path / "dev.json")
    store.register("tok-emp1", operator_id="EMP-001")
    push = PushService(bus, Settings(push_out_dir=tmp_path / "push"), store)

    calls = []

    class _FakeApns:
        async def send(self, token, payload, collapse_id=None):
            calls.append((token, collapse_id))
            return (True, 200, "ok")

    push._apns = _FakeApns()
    incident = {"id": "INC-X-001", "family": "energy",
                "failures": [{"id": "F1", "code": "PWR", "severity": "major", "equipment": "rectifier-2"}],
                "site": {"site_id": "PAR-021-NORD", "name": "Paris Nord", "lat": 48.9, "lon": 2.3, "address": "a"}}
    payload = await push.send(incident, operator_id="EMP-001")

    assert calls == [("tok-emp1", "INC-X-001")]                 # routed to the matched tech only
    method = [e for e in bus.history if e["type"] == "push_sent"][0]["data"]["method"]
    assert method == "apns"
    assert "confidence" not in json.dumps(payload)


async def test_push_falls_back_to_all_devices_when_operator_unmatched(tmp_path, bus, seeds):
    store = DeviceStore(tmp_path / "dev.json")
    store.register("tok-global", operator_id=None)
    push = PushService(bus, Settings(push_out_dir=tmp_path / "push"), store)
    seen = []

    class _FakeApns:
        async def send(self, token, payload, collapse_id=None):
            seen.append(token)
            return (True, 200, "ok")

    push._apns = _FakeApns()
    incident = {"id": "INC-Y-001", "family": "energy",
                "failures": [{"id": "F1", "code": "PWR", "severity": "major", "equipment": "busbar"}],
                "site": {"site_id": "PAR-021-NORD", "name": "Paris Nord", "lat": 48.9, "lon": 2.3, "address": "a"}}
    await push.send(incident, operator_id="EMP-404")           # no token for this operator
    assert seen == ["tok-global"]                              # falls back to every registered device


# -- POST /api/validation accepts the pitch card shape -------------------------
async def test_pitch_validation_confirmed(client):
    orch = await _to_awaiting(client)
    r = await client.post("/api/validation",
                          json={"incident_id": orch.incident["id"], "status": "confirmed"})
    assert r.status_code == 200, r.text
    assert r.json()["result"] == "confirmed"
    await orch.join()
    types = [e["type"] for e in client.app.state.bus.history]
    assert "action_report_ready" in types and "incident_resolved" in types


async def test_pitch_validation_rejected_pivots(client):
    orch = await _to_awaiting(client)
    r = await client.post("/api/validation", json={
        "incident_id": orch.incident["id"], "status": "rejected",
        "measurement": {"value": -53.9, "unit": "V"}})
    assert r.status_code == 200, r.text
    assert r.json()["result"] == "pivot"                       # counter-measurement drives the pivot
    await orch.join()
    history = client.app.state.bus.history
    vr = [e for e in history if e["type"] == "validation_result"][0]
    assert vr["data"]["result"] == "pivot"
    assert any(e["type"] == "phase_started" and e["data"]["cause"] == "pivot" for e in history)


async def test_pitch_validation_idempotent(client):
    orch = await _to_awaiting(client)
    body = {"incident_id": orch.incident["id"], "status": "confirmed"}
    first = await client.post("/api/validation", json=body)
    second = await client.post("/api/validation", json=body)   # double tap
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    await orch.join()
    received = [e for e in client.app.state.bus.history if e["type"] == "validation_received"]
    assert len(received) == 1                                   # no second state change


async def test_full_frozen_validation_body_still_accepted(client):
    orch = await _to_awaiting(client)
    body = {
        "incident_id": orch.incident["id"], "client_event_id": "full-1",
        "submitted_at": "2026-07-05T09:33:00Z",
        "validations": [{"failure_id": f["id"], "verdict": "real"} for f in orch.incident["failures"]],
        "measurements": [{"metric": "dc_voltage_v", "point": "busbar", "value": -44.8, "unit": "V"}],
    }
    r = await client.post("/api/validation", json=body)
    assert r.status_code == 200 and r.json()["result"] == "confirmed"
