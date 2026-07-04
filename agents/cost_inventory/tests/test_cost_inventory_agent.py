"""Tests for the Cost/Inventory/Dispatch agent (AGA.3 #30).

Acceptance criteria:
- All 3 tool calls visible in events (payload.tool_calls).
- Action report conforms to contract; part matched to a REAL seeded stock line.
- Totals consistent with the Cost Engine.

Unit tests use fake tools (offline); one integration test drives the REAL
backend tools over the committed seeds.
"""

import asyncio
from pathlib import Path

from contracts.agent_interface import (
    Agent, AgentInput, CostReport, DispatchBooking, InventoryLine, InventoryMatch,
)
from agents.cost_inventory import CostInventoryDispatchAgent

ROOT = Path(__file__).resolve().parents[3]


# --------------------------------------------------------------------------- #
# Fakes (satisfy contracts.Tool structurally)
# --------------------------------------------------------------------------- #
class FakeInventory:
    name = "inventory_lookup"

    def __init__(self, line):
        self._line = line

    async def __call__(self, payload):
        return InventoryMatch(incident_id=payload.incident_id, matches=[self._line])


class FakeCost:
    name = "cost_engine"

    async def __call__(self, payload):
        return CostReport(
            incident_id=payload.incident_id, repair_cost=770.0, downtime_cost_avoided=5450.0,
            currency="EUR",
            breakdown={"parts": 420.0, "labor": 170.0, "truck_roll": 180.0,
                       "downtime_avoided": 450.0, "sla_penalty_avoided": 5000.0},
        )


class FakeDispatch:
    name = "crew_dispatch"

    def __init__(self, booked=True):
        self._booked = booked

    async def __call__(self, payload):
        if not self._booked:
            return DispatchBooking(incident_id=payload.incident_id, crew_id="", booked=False)
        return DispatchBooking(incident_id=payload.incident_id, crew_id="CREW-IDF-3",
                               booked=True, eta_hours=0.75, window="today 06:00-18:00")


_IN_STOCK = InventoryLine(part_number="PN-RECT-48-2000", in_stock=True, quantity=6,
                          warehouse_id="WH-PAR-CENTRAL", eta_hours=None)


def _agent(dispatch=None, inv_line=_IN_STOCK):
    return CostInventoryDispatchAgent(FakeCost(), FakeInventory(inv_line), dispatch or FakeDispatch())


def _input(context=None):
    return AgentInput(
        incident_id="INC-DEMO-001", site_id="SITE-PAR-014", failure_family="energy",
        context=context if context is not None else {
            "parts": [{"part_no": "PN-RECT-48-2000", "qty": 1}],
            "remediation_title": "Replace failed rectifier module",
            "top_priority": "P1",
        },
    )


def _run(agent, inp):
    return asyncio.run(agent.run(inp))


# --------------------------------------------------------------------------- #
# Unit
# --------------------------------------------------------------------------- #
def test_satisfies_agent_protocol_and_name():
    assert isinstance(_agent(), Agent)
    assert _agent().name == "cost_inventory_dispatch"


def test_all_three_tool_calls_visible():
    out = _run(_agent(), _input())
    calls = out.payload["tool_calls"]
    assert len(calls) == 3
    assert {c["tool"] for c in calls} == {"inventory_lookup", "cost_engine", "crew_dispatch"}
    # backend _assemble_report keys present
    for k in ("cost", "inventory", "dispatch"):
        assert k in out.payload


def test_action_report_part_matched_and_crew():
    out = _run(_agent(), _input())
    report = out.payload["action_report"]
    assert report["part"]["part_number"] == "PN-RECT-48-2000"
    assert report["part"]["in_stock"] is True
    assert report["actions"][0]["priority"] == "P1"
    assert report["actions"][0]["owner"] == "CREW-IDF-3"
    assert out.confidence == 1.0


def test_totals_consistent_flag():
    out = _run(_agent(), _input())
    assert out.payload["totals_consistent"] is True


def test_part_extraction_from_agents_lane_shape():
    ctx = {"findings": {"remediation": {"parts_needed": ["PN-RECT-48-2000"], "confirmed_cause": "rectifier"}}}
    out = _run(_agent(), _input(ctx))
    assert out.payload["action_report"]["part"]["part_number"] == "PN-RECT-48-2000"


def test_no_crew_flags_honesty_and_lowers_confidence():
    out = _run(_agent(dispatch=FakeDispatch(booked=False)), _input())
    assert any("no crew" in n for n in out.payload["action_report"]["honesty_notes"])
    assert out.confidence < 1.0
    assert "owner" not in out.payload["action_report"]["actions"][0]


def test_out_of_stock_flags_honesty():
    oos = InventoryLine(part_number="PN-ANT-8001", in_stock=False, quantity=0,
                        warehouse_id="WH-PAR-NORTH", eta_hours=120.0)
    out = _run(_agent(inv_line=oos), _input())
    assert any("out of stock" in n for n in out.payload["action_report"]["honesty_notes"])


# --------------------------------------------------------------------------- #
# Integration: REAL tools + seeds (part matched to real stock; totals verified)
# --------------------------------------------------------------------------- #
def test_integration_real_tools_and_seeds():
    from backend.app.seeds import load_seeds
    from backend.app.tools import CostEngineTool, CrewDispatchTool, InventoryLookupTool

    seeds = load_seeds(ROOT / "data", ROOT / "backend" / "seed_defaults")
    agent = CostInventoryDispatchAgent(
        CostEngineTool(seeds), InventoryLookupTool(seeds), CrewDispatchTool(seeds),
    )
    # Canonical confirm scenario (frozen run_confirm): the Paris-Nord gold site and
    # the Eaton rectifier the reconciled seeds carry. The shared _input() still pins
    # the OLD part/site for the fake-tool unit tests, so this REAL-tools path feeds
    # the canonical reference explicitly.
    inp = AgentInput(
        incident_id="INC-DEMO-001", site_id="PAR-021-NORD", failure_family="energy",
        context={
            "parts": [{"part_no": "APR48-3G", "qty": 1}],
            "remediation_title": "Replace failed rectifier module",
            "top_priority": "P1",
        },
    )
    out = _run(agent, inp)

    # part matched to a REAL seeded stock line (data/inventory.csv: APR48-3G)
    part = out.payload["action_report"]["part"]
    assert part["part_number"] == "APR48-3G"
    assert part["in_stock"] is True
    assert part["quantity"] == 3
    assert part["warehouse_id"] == "WH-PAR-EST"

    # Cost derived from the real seeds + CostEngineTool formula:
    #   repair  = part 769.04 + labor 35.73*2h + truck_roll 325.00 = 1165.50
    #             (matches frozen run_confirm intervention 1165.50)
    #   avoided = downtime 5.00/min * 240 (gold restore_target) * 1.5 (gold weight)
    #             + sla_breach_penalty 5000.00 = 6800.00
    #   NB: the frozen fixture avoided is 4180.00 — a hand-authored "SLA credits +
    #   downtime" figure predating the seeded flat-penalty model; the deterministic
    #   tool math is the source of truth for the live path.
    cost = out.payload["cost"]
    assert cost["repair_cost"] == 1165.50
    assert cost["downtime_cost_avoided"] == 6800.00
    assert out.payload["totals_consistent"] is True

    # crew booked from the real schedule: PAR-021-NORD is IDF-North; the only AVAILABLE
    # IDF-North dc_power crew is PWR-2 (PWR-5 is on_job, PWR-7 is IDF-East).
    assert out.payload["dispatch"]["booked"] is True
    assert out.payload["dispatch"]["crew_id"] == "PWR-2"
    assert len(out.payload["tool_calls"]) == 3
