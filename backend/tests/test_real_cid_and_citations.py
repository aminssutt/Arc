"""AUDIT P0-1 (#76) citation transform + the real CID agent (AGA.3) in the registry.

1. Agents produce contracts.Citation {doc_id, section, snippet?}; the frozen
   event schema requires {doc_id, claim}. The orchestrator now transforms at
   every emission point — proven with a root_cause stand-in that emits
   agent-interface-shaped citations (what the REAL Root-Cause produces).
2. aminssutt's CostInventoryDispatchAgent replaces the backend stand-in and
   drives the real tools; the assembled report carries its numbers verbatim.
"""
from contracts import AgentInput, AgentOutput

from agents.cost_inventory import CostInventoryDispatchAgent

from backend.app import orchestrator as st
from backend.app.dummy_agents import DummyRootCauseAgent, default_registry
from backend.app.orchestrator import Orchestrator
from backend.app.push_service import PushService
from backend.app.settings import Settings
from backend.app.validation_adapter import ValidationAgentAdapter

from backend.tests.conftest import assert_contract

FAULT_FAILURES = [{"code": "DC_UNDERVOLTAGE", "alarm_code": "PWR-DC-UV", "severity": "critical",
                   "equipment": "busbar", "metric": "dc_voltage_v",
                   "value": -44.0, "first_seen": "2026-07-05T09:00:00Z"}]
TRIGGER = {"rule": "PWR-DC-UV", "debounce_s": 60, "triggered_at": "2026-07-05T09:01:01Z"}


class SectionCitingRootCause(DummyRootCauseAgent):
    """Emits citations in the agent-interface shape — like the real Root-Cause."""

    async def run(self, data: AgentInput) -> AgentOutput:
        out = await super().run(data)
        raw = [{"doc_id": "S1", "section": "-48V DC input envelope",
                "snippet": "normal range -40.5 to -57.0 VDC"}]
        for cause in out.payload["diagnostic"]["causes"]:
            cause["citations"] = list(raw)
        if out.payload["diagnostic"].get("urgency", {}).get("citations"):
            out.payload["diagnostic"]["urgency"]["citations"] = list(raw)
        return out


def _orch(bus, seeds, tools, tmp_path):
    registry = default_registry(*tools)
    registry["validation"] = ValidationAgentAdapter(seeds)
    registry["cost_inventory_dispatch"] = CostInventoryDispatchAgent(*tools)
    registry["root_cause"] = SectionCitingRootCause()
    push = PushService(bus, Settings(push_out_dir=tmp_path / "push"))
    return Orchestrator(bus, seeds, registry, push, agent_timeout_s=5.0)


def _confirm_body(orch):
    return {"incident_id": orch.incident["id"], "client_event_id": "cid-1",
            "submitted_at": "2026-07-05T09:33:00Z",
            "validations": [{"failure_id": f["id"], "verdict": "real"}
                            for f in orch.incident["failures"]],
            "measurements": [{"metric": "dc_voltage_v", "point": "busbar",
                              "value": -43.9, "unit": "V"}]}


async def test_section_shaped_citations_become_event_legal(bus, seeds, tools, tmp_path, event_validator):
    orch = _orch(bus, seeds, tools, tmp_path)
    await orch.handle_fault("PAR-021-NORD", "energy", FAULT_FAILURES, TRIGGER)
    await orch.join()
    await orch.handle_validation(_confirm_body(orch))
    await orch.join()

    diag = [e for e in bus.history if e["type"] == "diagnostic_ready"][0]
    cite = diag["data"]["causes"][0]["citations"][0]
    assert cite["claim"] == "-48V DC input envelope"      # section -> claim
    assert cite["doc_id"] == "S1"
    report = [e for e in bus.history if e["type"] == "action_report_ready"][0]["data"]["report"]
    assert report["diagnosis"]["citations"][0]["claim"] == "-48V DC input envelope"
    assert_contract(bus.history, event_validator)          # would fail without the transform


async def test_real_cid_agent_numbers_flow_into_report(bus, seeds, tools, tmp_path, event_validator):
    orch = _orch(bus, seeds, tools, tmp_path)
    await orch.handle_fault("PAR-021-NORD", "energy", FAULT_FAILURES, TRIGGER)
    await orch.join()
    await orch.handle_validation(_confirm_body(orch))
    await orch.join()
    assert orch.state == st.IDLE

    done = [e for e in bus.history if e["type"] == "agent_completed"
            and e["data"]["agent"] == "cost_inventory_dispatch"][0]
    assert done["data"]["status"] == "ok"
    assert "3 tool calls" in done["data"]["summary"]

    report = [e for e in bus.history if e["type"] == "action_report_ready"][0]["data"]["report"]
    assert report["cost"]["intervention"] == 1165.50        # Cost Engine, verbatim
    assert report["cost"]["avoided"] == 6800.00
    assert report["inventory"]["part_no"] == "APR48-3G"
    assert report["inventory"]["in_stock"] is True
    assert report["dispatch"]["crew"] == "PWR-2"      # Crew Dispatch, real booking
    assert_contract(bus.history, event_validator)
