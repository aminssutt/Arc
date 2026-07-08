"""Auto-reset TTL (idle-return): N seconds after an incident reaches a TERMINAL
state the backend auto-returns to a clean idle -- the SAME reset as POST
/api/demo/reset -- so a visitor arriving long after a run sees a fresh state, not
the replayed final report (SSE history purged). Guards: a new incident / active
run is never reset; ARC_AUTO_RESET_S=0 disables it. Offline, deterministic.
"""
import asyncio
import itertools

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app import orchestrator as st
from backend.app.dummy_agents import default_registry
from backend.app.main import create_app
from backend.app.orchestrator import Orchestrator
from backend.app.push_service import PushService
from backend.app.settings import Settings

FAULT_FAILURES = [{"code": "DC_UNDERVOLTAGE", "alarm_code": "PWR-DC-UV", "severity": "critical",
                   "equipment": "busbar", "metric": "dc_voltage_v",
                   "value": -44.0, "first_seen": "2026-07-05T09:00:00Z"}]
TRIGGER = {"rule": "PWR-DC-UV", "debounce_s": 60, "triggered_at": "2026-07-05T09:01:01Z"}


@pytest.fixture()
async def client():
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.app = app
            yield c


def _body(orch, verdicts, cid="ttl-1"):
    return {
        "incident_id": orch.incident["id"],
        "client_event_id": cid,
        "submitted_at": "2026-07-05T09:33:00Z",
        "validations": [{"failure_id": f["id"], "verdict": v}
                        for f, v in zip(orch.incident["failures"], itertools.cycle(verdicts))],
        "measurements": [{"metric": "dc_voltage_v", "point": "busbar", "value": -43.9, "unit": "V"}],
    }


async def _run_confirm_to_terminal(client, orch, cid):
    r = await client.post("/api/demo/inject-fault", json={"scenario": "confirm"})
    assert r.status_code == 200, r.text
    await orch.join()
    assert orch.state == "awaiting_field_validation"
    r = await client.post("/api/validation", json=_body(orch, ["real"], cid=cid))
    assert r.status_code == 200
    await orch.join()
    assert orch.state == "idle"                              # terminal reached (resolved -> idle)


# --------------------------------------------------------------------------- #
# 1. terminal + short TTL => clean idle; a fresh inject restarts cleanly
# --------------------------------------------------------------------------- #
async def test_terminal_incident_auto_resets_after_ttl(client):
    orch = client.app.state.orchestrator
    orch.auto_reset_s = 0.1                                  # opt in (conftest default is 0)

    await _run_confirm_to_terminal(client, orch, cid="ttl-run1")
    assert client.app.state.bus.history                      # final report still on the bus

    await asyncio.sleep(0.3)                                 # let the TTL fire
    assert client.app.state.bus.history == []                # events purged: SSE won't replay the run
    assert orch.incident is None and orch.state == "idle"    # back to a clean idle

    # a fresh run starts clean: exactly one incident detected, one push sent
    r = await client.post("/api/demo/inject-fault", json={"scenario": "confirm"})
    assert r.status_code == 200, r.text
    await orch.join()
    faults = [e for e in client.app.state.bus.history if e["type"] == "fault_detected"]
    pushes = [e for e in client.app.state.bus.history if e["type"] == "push_sent"]
    assert len(faults) == 1 and len(pushes) == 1


# --------------------------------------------------------------------------- #
# 2. a NEW run started before the TTL fires => the active run is NEVER reset
# --------------------------------------------------------------------------- #
async def test_new_run_before_ttl_is_not_reset(bus, seeds, tools, tmp_path):
    push = PushService(bus, Settings(push_out_dir=tmp_path / "p"))
    reset_calls: list = []
    orch = Orchestrator(bus, seeds, default_registry(*tools), push,
                        agent_timeout_s=5.0, auto_reset_s=0.2)
    orch.reset_hook = lambda: reset_calls.append(orch.state)  # detect any reset (would mean a bug)

    # incident A runs through the human loop to a terminal state -> TTL armed (gen=1)
    await orch.handle_fault("PAR-021-NORD", "energy", FAULT_FAILURES, TRIGGER)
    await orch.join()
    await orch.handle_validation(_body(orch, ["real"], cid="a-1"))
    await orch.join()
    assert orch.state == st.IDLE

    # incident B starts BEFORE A's TTL elapses -> it cancels A's pending timer
    await orch.handle_fault("LYO-002-SUD", "energy", FAULT_FAILURES, TRIGGER)
    await orch.join()
    assert orch.state == st.AWAITING                         # B is mid human loop (active)
    incident_b = orch.incident["id"]

    await asyncio.sleep(0.35)                                # well past A's original 0.2s TTL
    assert reset_calls == []                                 # the active run B was never reset
    assert orch.state == st.AWAITING and orch.incident["id"] == incident_b


# --------------------------------------------------------------------------- #
# 3. ARC_AUTO_RESET_S=0 (conftest default) => the terminal state persists
# --------------------------------------------------------------------------- #
async def test_auto_reset_disabled_persists_terminal_state(client):
    orch = client.app.state.orchestrator
    assert orch.auto_reset_s == 0                            # conftest default: auto-reset disabled

    await _run_confirm_to_terminal(client, orch, cid="off-1")
    history_len = len(client.app.state.bus.history)
    assert history_len > 0

    await asyncio.sleep(0.3)                                 # no TTL should ever fire
    assert len(client.app.state.bus.history) == history_len  # final report still replayed to new clients
    assert orch.incident is not None                        # the terminated incident is still held
