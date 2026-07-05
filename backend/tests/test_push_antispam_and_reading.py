"""INT.7 anti-spam belts + the iPhone-card reading (task #56 / P0 push spam).

- Watchdog one-shot: a consumed fault never re-fires after termination (only a
  reset re-arms) — kills the observed periodic push spam.
- Push cap per incident + global min interval: a hard belt even if a bug ever
  re-triggered an incident.
- The push payload carries a `reading` (value/unit/point/metric) and NEVER a
  confidence.
"""
import json

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.push_service import PushService
from backend.app.settings import Settings
from backend.app.watchdog import Watchdog


def _sig(ts, value=-44.0):
    return {"ts": ts, "site_id": "PAR-021-NORD", "signal": "dc_voltage_v",
            "value": value, "equipment_id": "busbar", "trap": "DC_UNDERVOLTAGE"}


def _incident(incident_id="INC-R", failures=None):
    return {"id": incident_id, "family": "energy",
            "failures": failures or [
                {"id": "F1", "code": "alarmMajorRectifier", "severity": "major",
                 "equipment": "rectifier-2", "metric": "module_status", "value": 0},
                {"id": "F2", "code": "DC_UNDERVOLTAGE", "severity": "major",
                 "equipment": "busbar", "metric": "dc_voltage_v", "value": -44.8}],
            "site": {"site_id": "PAR-021-NORD", "name": "Paris Nord", "lat": 48.9, "lon": 2.3, "address": "a"}}


# -- BELT 1: watchdog one-shot --------------------------------------------------
async def test_watchdog_one_shot_no_refire_after_termination(seeds):
    faults: list[str] = []

    async def on_fault(site, family, failures, trigger):
        faults.append(site)

    wd = Watchdog(seeds, on_fault)
    sigs = [_sig("2026-07-05T09:00:00Z"), _sig("2026-07-05T09:01:01Z")]  # debounce satisfied
    await wd.ingest_batch(sigs)
    assert len(faults) == 1                                    # one inject -> one incident
    wd.incident_closed("PAR-021-NORD")                         # incident resolves
    await wd.ingest_batch(sigs)                                # re-tick with the SAME signals
    assert len(faults) == 1                                    # NO re-fire (one-shot; no spam)
    wd.reset()                                                 # explicit reset re-arms
    await wd.ingest_batch(sigs)
    assert len(faults) == 2


# -- BELT 2: push cap + min interval --------------------------------------------
async def test_push_cap_per_incident(bus, seeds, tmp_path):
    push = PushService(bus, Settings(push_out_dir=tmp_path / "p", push_min_interval_s=0))
    inc = _incident("INC-CAP")
    assert await push.send(inc) is not None
    assert await push.send(inc) is not None
    assert await push.send(inc) is None                        # 3rd suppressed (cap = 2)
    assert len([e for e in bus.history if e["type"] == "push_sent"]) == 2


async def test_push_min_interval_suppresses_rapid(bus, seeds, tmp_path):
    push = PushService(bus, Settings(push_out_dir=tmp_path / "p", push_min_interval_s=60))
    assert await push.send(_incident("INC-A")) is not None
    assert await push.send(_incident("INC-B")) is None         # within 60 s of the last push
    push.reset()                                               # reset clears the interval clock
    assert await push.send(_incident("INC-C")) is not None


# -- reading on the card, never a confidence ------------------------------------
def test_push_reading_present_and_no_confidence(bus, seeds, tmp_path):
    push = PushService(bus, Settings(push_out_dir=tmp_path / "p"))
    payload = push.build_payload(_incident("INC-R"))
    assert payload["reading"] == {"value": -44.8, "unit": "V",
                                  "point": "busbar", "metric": "dc_voltage_v"}
    assert "confidence" not in json.dumps(payload)             # reading, but never the score


def test_push_reading_skips_boolean_only_failures(bus, seeds, tmp_path):
    push = PushService(bus, Settings(push_out_dir=tmp_path / "p"))
    # only a boolean status failure -> no numeric reading (never a bogus 0)
    payload = push.build_payload(_incident("INC-B", failures=[
        {"id": "F1", "code": "alarmMajorRectifier", "severity": "major",
         "equipment": "rectifier-2", "metric": "module_status", "value": 0}]))
    assert "reading" not in payload


# -- E2E: one inject = one incident = one push, no re-fire after termination -----
@pytest.fixture()
async def app_client():
    from backend.app.main import create_app
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.app = app
            yield c


async def test_e2e_one_inject_one_push_no_refire(app_client):
    orch = app_client.app.state.orchestrator
    bus = app_client.app.state.bus
    await app_client.post("/api/demo/inject-fault", json={"scenario": "confirm"})
    await orch.join()
    await app_client.post("/api/validation", json={"incident_id": orch.incident["id"], "status": "confirmed"})
    await orch.join()

    incidents = {e["incident_id"] for e in bus.history}
    pushes = [e for e in bus.history if e["type"] == "push_sent"]
    assert len(incidents) == 1 and len(pushes) == 1            # exactly one incident, one push
    assert "reading" in pushes[0]["data"]["payload"]

    # simulate the watchdog re-ticking the consumed signals after termination
    await app_client.app.state.watchdog.ingest_batch(app_client.app.state.seeds.scenarios["confirm"])
    await orch.join()
    assert {e["incident_id"] for e in bus.history} == incidents          # no new incident
    assert len([e for e in bus.history if e["type"] == "push_sent"]) == 1  # no new push
    assert orch.state == "idle"
