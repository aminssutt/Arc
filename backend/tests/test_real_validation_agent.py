"""The REAL Validation agent (aminssutt's AGA.1) wired into the orchestrator
registry via ValidationAgentAdapter — the first dummy->real swap (INT.3 slice).

Signature source of truth: PWR-DC-UV in alarm_dictionary.csv (lt 45.0 V) — the
same rule that fires the Watchdog. Measurement 43.9 V => abnormal => CONFIRMED;
53.9 V => normal => CONTRADICTED => pivot, regardless of the verdict.
"""
from backend.app import orchestrator as st
from backend.app.dummy_agents import default_registry
from backend.app.orchestrator import Orchestrator
from backend.app.push_service import PushService
from backend.app.settings import Settings
from backend.app.validation_adapter import ValidationAgentAdapter

from backend.tests.conftest import assert_contract

FAULT_FAILURES = [{"code": "DC_UNDERVOLTAGE", "alarm_code": "PWR-DC-UV", "severity": "critical",
                   "equipment": "busbar", "metric": "dc_voltage_v",
                   "value": -44.0, "first_seen": "2026-07-05T09:00:00Z"}]
TRIGGER = {"rule": "PWR-DC-UV", "debounce_s": 60, "triggered_at": "2026-07-05T09:01:01Z"}


def _orch(bus, seeds, tools, tmp_path):
    registry = default_registry(*tools)
    registry["validation"] = ValidationAgentAdapter(seeds)   # the real one
    push = PushService(bus, Settings(push_out_dir=tmp_path / "push"))
    return Orchestrator(bus, seeds, registry, push, agent_timeout_s=5.0)


def _body(orch, verdicts, value):
    return {
        "incident_id": orch.incident["id"], "client_event_id": "rv-1",
        "submitted_at": "2026-07-05T09:33:00Z",
        "validations": [{"failure_id": f["id"], "verdict": v}
                        for f, v in zip(orch.incident["failures"], verdicts)],
        "measurements": [{"metric": "dc_voltage_v", "point": "busbar",
                          "value": value, "unit": "V"}],
    }


async def test_real_agent_confirms_on_abnormal_measurement(bus, seeds, tools, tmp_path, event_validator):
    orch = _orch(bus, seeds, tools, tmp_path)
    await orch.handle_fault("PAR-021-NORD", "energy", FAULT_FAILURES, TRIGGER)
    await orch.join()

    await orch.handle_validation(_body(orch, ["real"], value=-43.9))  # |v| < 45.0 => fault real
    await orch.join()

    vr = [e for e in bus.history if e["type"] == "validation_result"][0]
    assert vr["data"]["result"] == "confirmed"
    assert "CONFIRMS" in vr["data"]["rationale"]          # the real agent's prose
    assert orch.state == st.IDLE
    assert_contract(bus.history, event_validator)


async def test_real_agent_pivots_on_normal_measurement(bus, seeds, tools, tmp_path, event_validator):
    orch = _orch(bus, seeds, tools, tmp_path)
    await orch.handle_fault("PAR-021-NORD", "energy", FAULT_FAILURES, TRIGGER)
    await orch.join()

    # Technician says "real" but MEASURES a healthy plant: the real agent trusts
    # the measurement (the dummy would have confirmed) — the telemetry-lied beat.
    await orch.handle_validation(_body(orch, ["real"], value=-53.9))
    await orch.join()

    vr = [e for e in bus.history if e["type"] == "validation_result"][0]
    assert vr["data"]["result"] == "pivot"
    assert vr["data"]["contradictions"] == [
        {"failure_id": "F1", "telemetry": -44.0, "measured": -53.9, "unit": "V"}]
    pivot_restarts = [e for e in bus.history
                      if e["type"] == "phase_started" and e["data"]["cause"] == "pivot"]
    assert len(pivot_restarts) == 1
    resolved = [e for e in bus.history if e["type"] == "incident_resolved"][0]
    assert resolved["data"]["outcome"] == "downgraded"
    assert_contract(bus.history, event_validator)


async def test_adapter_satisfies_frozen_protocol(seeds):
    from contracts import Agent
    assert isinstance(ValidationAgentAdapter(seeds), Agent)
