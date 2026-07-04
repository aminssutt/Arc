"""BE.3 acceptance: all transitions unit-tested incl. the pivot loop; runs
end-to-end with dummy agents via the registry; agent timeout -> graceful event
(INT.5). Every envelope emitted by the LIVE runtime is validated against the
FROZEN event contract — the backend cannot drift from what frontend/iOS build
against.
"""
import asyncio

import pytest

from backend.app import orchestrator as st
from backend.app.orchestrator import IllegalTransition, Orchestrator

from backend.tests.conftest import assert_contract

FAULT_FAILURES = [{"code": "PWR-DC-UV", "severity": "critical",
                   "equipment": "EQ-PAR-014-RECT-1", "metric": "dc_plant_voltage_v",
                   "value": 44.0, "first_seen": "2026-07-05T09:00:00Z"}]
TRIGGER = {"rule": "PWR-DC-UV", "debounce_s": 60, "triggered_at": "2026-07-05T09:01:01Z"}


def _validation_body(orch, verdicts):
    return {
        "incident_id": orch.incident["id"],
        "client_event_id": "t-1",
        "submitted_at": "2026-07-05T09:33:00Z",
        "technician": {"id": "tech-07"},
        "validations": [{"failure_id": f["id"], "verdict": v}
                        for f, v in zip(orch.incident["failures"], verdicts)],
        "measurements": [{"metric": "dc_plant_voltage_v", "point": "busbar", "value": 43.9, "unit": "V"}],
    }


async def test_confirm_run_end_to_end(orchestrator, bus, event_validator):
    incident_id = await orchestrator.handle_fault("SITE-PAR-014", "energy", FAULT_FAILURES, TRIGGER)
    assert incident_id is not None
    await orchestrator.join()
    assert orchestrator.state == st.AWAITING

    await orchestrator.handle_validation(_validation_body(orchestrator, ["real"]))
    await orchestrator.join()
    assert orchestrator.state == st.IDLE  # resolved -> idle, ready for the next fault

    types = [e["type"] for e in bus.history]
    assert types[0] == "fault_detected"
    assert {"phase_started", "agent_started", "agent_completed", "retrieval_performed",
            "diagnostic_ready", "push_sent", "awaiting_field_validation",
            "validation_received", "validation_result", "remediation_ready",
            "action_report_ready", "incident_resolved"} <= set(types)
    # multi-retrieve compliance: root_cause performed >= 2 passes
    passes = [e["data"]["pass"] for e in bus.history
              if e["type"] == "retrieval_performed" and e["data"]["agent"] == "root_cause"]
    assert len(passes) >= 2
    resolved = [e for e in bus.history if e["type"] == "incident_resolved"][0]
    assert resolved["data"]["outcome"] == "resolved"
    assert_contract(bus.history, event_validator)  # frozen contract, every event


async def test_pivot_loop_end_to_end(orchestrator, bus, event_validator):
    await orchestrator.handle_fault("SITE-PAR-014", "energy", FAULT_FAILURES, TRIGGER)
    await orchestrator.join()

    await orchestrator.handle_validation(_validation_body(orchestrator, ["false"]))
    await orchestrator.join()
    assert orchestrator.state == st.IDLE

    types = [e["type"] for e in bus.history]
    vr = [e for e in bus.history if e["type"] == "validation_result"][0]
    assert vr["data"]["result"] == "pivot"
    pivot_restart = [e for e in bus.history
                     if e["type"] == "phase_started" and e["data"] == {"phase": 1, "cause": "pivot"}]
    assert len(pivot_restart) == 1                      # the pivot loop re-entered phase 1
    assert types.count("diagnostic_ready") == 2         # re-diagnosis happened
    assert types.count("push_sent") == 1                # no second push loop after pivot
    resolved = [e for e in bus.history if e["type"] == "incident_resolved"][0]
    assert resolved["data"]["outcome"] == "downgraded"
    assert_contract(bus.history, event_validator)


async def test_second_fault_while_busy_is_ignored(orchestrator):
    await orchestrator.handle_fault("SITE-PAR-014", "energy", FAULT_FAILURES, TRIGGER)
    assert await orchestrator.handle_fault("SITE-PAR-021", "rf", FAULT_FAILURES, TRIGGER) is None
    await orchestrator.join()


async def test_illegal_transitions_raise(orchestrator):
    with pytest.raises(IllegalTransition):
        orchestrator._transition(st.PHASE2)            # idle -> phase2 is illegal
    orchestrator._transition(st.FAULT_TRIGGERED)
    with pytest.raises(IllegalTransition):
        orchestrator._transition(st.AWAITING)          # fault_triggered -> awaiting is illegal


async def test_agent_timeout_is_graceful(bus, seeds, tools, tmp_path, event_validator):
    from backend.app.dummy_agents import default_registry
    from backend.app.push_service import PushService
    from backend.app.settings import Settings

    class SlowAgent:
        name = "correlation"

        async def run(self, data):
            await asyncio.sleep(1.0)

    registry = default_registry(*tools)
    registry["correlation"] = SlowAgent()
    push = PushService(bus, Settings(push_out_dir=tmp_path / "p"))
    orch = Orchestrator(bus, seeds, registry, push, agent_timeout_s=0.05)

    await orch.handle_fault("SITE-PAR-014", "energy", FAULT_FAILURES, TRIGGER)
    await orch.join()                                   # no crash (INT.5)
    done = [e for e in bus.history if e["type"] == "agent_completed"][-1]
    assert done["data"]["status"] == "timeout"
    assert_contract(bus.history, event_validator)
    orch.reset()                                        # recoverable
    assert orch.state == st.IDLE
