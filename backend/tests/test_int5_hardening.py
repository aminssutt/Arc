"""INT.5 (#51) — backend E2E hardening, demo-day resilience. Acceptance:

1. Web client kill/restart MID-RUN => stream resumes (Last-Event-ID, real HTTP)
2. Agent timeout => graceful error event, no crash — and the incident always
   TERMINATES (phase-1 degraded terminal added here; phase-2 covered by #97)
3. Incident reset < 5 s for retakes, including mid-run
"""
import asyncio
import json
import time

import pytest
from httpx import AsyncClient

from backend.app import orchestrator as st
from backend.app.dummy_agents import default_registry
from backend.app.main import create_app
from backend.app.orchestrator import Orchestrator
from backend.app.push_service import PushService
from backend.app.settings import Settings

from backend.tests.conftest import assert_contract

FAULT_FAILURES = [{"code": "DC_UNDERVOLTAGE", "alarm_code": "PWR-DC-UV", "severity": "critical",
                   "equipment": "busbar", "metric": "dc_voltage_v",
                   "value": -44.0, "first_seen": "2026-07-05T09:00:00Z"}]
TRIGGER = {"rule": "PWR-DC-UV", "debounce_s": 60, "triggered_at": "2026-07-05T09:01:01Z"}


# --------------------------------------------------------------------------- #
# 1. kill/restart mid-run => stream resumes (real uvicorn, real reconnect)
# --------------------------------------------------------------------------- #
async def test_stream_resumes_after_midrun_kill():
    import uvicorn

    app = create_app()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8733, log_level="warning"))
    serve_task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.05)
    try:
        async with AsyncClient(base_url="http://127.0.0.1:8733") as http:
            r = await http.post("/api/demo/inject-fault", json={"scenario": "confirm"})
            assert r.status_code == 200, r.text
            orch = app.state.orchestrator

            # client reads a few events MID-RUN, then dies (connection dropped)
            got: list[dict] = []
            async with http.stream("GET", "/api/stream") as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        got.append(json.loads(line[6:]))
                        if len(got) >= 3:
                            break                      # <- kill mid-run
            await orch.join()                          # run continues without the client

            body = {"incident_id": orch.incident["id"], "client_event_id": "int5-1",
                    "submitted_at": "2026-07-05T09:33:00Z",
                    "validations": [{"failure_id": f["id"], "verdict": "real"}
                                    for f in orch.incident["failures"]],
                    "measurements": [{"metric": "dc_voltage_v", "point": "busbar",
                                      "value": -43.9, "unit": "V"}]}
            assert (await http.post("/api/validation", json=body)).status_code == 200
            await orch.join()

            # restart: reconnect with Last-Event-ID, expect the remainder
            resumed: list[dict] = []
            async with http.stream("GET", "/api/stream",
                                   headers={"Last-Event-ID": got[-1]["id"]}) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        resumed.append(json.loads(line[6:]))
                        if resumed[-1]["type"] == "incident_resolved":
                            break
            seqs = [e["seq"] for e in got + resumed]
            assert seqs == list(range(1, len(seqs) + 1))        # gapless across the kill
            assert resumed[0]["seq"] == got[-1]["seq"] + 1      # resumed exactly after
            assert resumed[-1]["type"] == "incident_resolved"   # run completed on stream
    finally:
        server.should_exit = True
        await serve_task


# --------------------------------------------------------------------------- #
# 2. phase-1 agent timeout => graceful events AND the incident terminates
# --------------------------------------------------------------------------- #
class SlowAgent:
    name = "correlation"

    async def run(self, data):
        await asyncio.sleep(1.0)


class ExplodingRootCause:
    name = "root_cause"

    async def run(self, data):
        raise RuntimeError("LLM meltdown")


@pytest.mark.parametrize("agent_key,broken,expected_status", [
    ("correlation", SlowAgent(), "timeout"),
    ("root_cause", ExplodingRootCause(), "error"),
])
async def test_phase1_failure_terminates_degraded(bus, seeds, tools, tmp_path,
                                                  event_validator, agent_key, broken, expected_status):
    registry = default_registry(*tools)
    registry[agent_key] = broken
    push = PushService(bus, Settings(push_out_dir=tmp_path / "p"))
    orch = Orchestrator(bus, seeds, registry, push, agent_timeout_s=0.05)

    await orch.handle_fault("PAR-021-NORD", "energy", FAULT_FAILURES, TRIGGER)
    await orch.join()                                       # no crash

    done = [e for e in bus.history if e["type"] == "agent_completed"
            and e["data"]["agent"] == agent_key][-1]
    assert done["data"]["status"] == expected_status        # graceful error event
    resolved = [e for e in bus.history if e["type"] == "incident_resolved"]
    assert len(resolved) == 1                               # incident TERMINATED
    assert resolved[0]["data"]["outcome"] == "downgraded"
    assert agent_key in resolved[0]["data"]["summary"]
    assert orch.state == st.IDLE                            # next fault accepted immediately
    assert_contract(bus.history, event_validator)


# --------------------------------------------------------------------------- #
# 3. mid-run reset < 5 s, system immediately retake-ready
# --------------------------------------------------------------------------- #
async def test_midrun_reset_under_5s(bus, watchdog, orchestrator):
    await orchestrator.handle_fault("PAR-021-NORD", "energy", FAULT_FAILURES, TRIGGER)
    await orchestrator.join()
    assert orchestrator.state == st.AWAITING                # mid-run: human loop pending

    t0 = time.monotonic()
    orchestrator.reset()
    watchdog.reset()
    bus.reset()
    elapsed = time.monotonic() - t0
    assert elapsed < 5.0                                    # INT.5 acceptance
    assert orchestrator.state == st.IDLE and bus.history == []

    # retake works immediately
    await orchestrator.handle_fault("PAR-021-NORD", "energy", FAULT_FAILURES, TRIGGER)
    await orchestrator.join()
    assert orchestrator.state == st.AWAITING
