"""Employee-matching wired into the orchestrator: the diagnosed fault routes to
ONE responder whose notification decision rides the `awaiting_field_validation`
event (schema is open — no frozen-contract change). Difficulty + zone are honored
end to end, and every emitted event still satisfies the frozen contract.
"""
from backend.app.dummy_agents import default_registry
from backend.app.orchestrator import Orchestrator
from backend.app.push_service import PushService
from backend.app.settings import Settings
from agents.responder_matching import ResponderMatchingAgent

from backend.tests.conftest import assert_contract

TRIGGER = {"rule": "PWR", "debounce_s": 60, "triggered_at": "2026-07-05T09:01:01Z"}


def _failures(code, alarm_code):
    return [{"code": code, "alarm_code": alarm_code, "severity": "critical",
             "equipment": "EQ-RECT-1", "metric": "dc_plant_voltage_v",
             "value": 44.0, "first_seen": "2026-07-05T09:00:00Z"}]


def _orch(bus, seeds, tools, tmp_path):
    registry = default_registry(*tools)
    registry["responder_matching"] = ResponderMatchingAgent(as_of="2026-07-04")
    push = PushService(bus, Settings(push_out_dir=tmp_path / "push"))
    return Orchestrator(bus, seeds, registry, push, agent_timeout_s=5.0)


def _awaiting(bus):
    ev = [e for e in bus.history if e["type"] == "awaiting_field_validation"]
    assert ev, "no awaiting_field_validation emitted"
    return ev[0]["data"]


async def test_complex_energy_routes_to_in_zone_senior(bus, seeds, tools, tmp_path, event_validator):
    orch = _orch(bus, seeds, tools, tmp_path)
    # PAR-021-NORD is IDF-North; PWR-GRID-LOSS is a COMPLEX energy fault.
    await orch.handle_fault("PAR-021-NORD", "energy", _failures("alarmACmains", "PWR-GRID-LOSS"), TRIGGER)
    await orch.join()

    data = _awaiting(bus)
    responders = data.get("responders")
    assert responders, "notification carries no responder"
    r = responders[0]
    assert r["employee_id"] == "EMP-003"        # in-zone energy senior
    assert r["tier"] == "senior" and r["out_of_zone"] is False
    assert r["difficulty"] == "complex"
    assert_contract(bus.history, event_validator)  # frozen contract still satisfied


async def test_simple_energy_routes_to_a_junior(bus, seeds, tools, tmp_path, event_validator):
    orch = _orch(bus, seeds, tools, tmp_path)
    # PWR-FUSE-BLOWN is a SIMPLE energy fault at IDF-North -> junior gains experience.
    await orch.handle_fault("PAR-021-NORD", "energy", _failures("alarmDistributionBreakerOpen", "PWR-FUSE-BLOWN"), TRIGGER)
    await orch.join()

    r = _awaiting(bus)["responders"][0]
    assert r["employee_id"] == "EMP-004" and r["tier"] == "junior"
    assert_contract(bus.history, event_validator)


async def test_notification_absent_when_agent_not_registered(bus, seeds, tools, tmp_path, event_validator):
    # Without the responder agent, the flow is unchanged (backwards compatible).
    registry = default_registry(*tools)
    push = PushService(bus, Settings(push_out_dir=tmp_path / "push"))
    orch = Orchestrator(bus, seeds, registry, push, agent_timeout_s=5.0)
    await orch.handle_fault("PAR-021-NORD", "energy", _failures("alarmACmains", "PWR-GRID-LOSS"), TRIGGER)
    await orch.join()
    assert "responders" not in _awaiting(bus)
    assert_contract(bus.history, event_validator)
