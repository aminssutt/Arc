"""Unit tests for the difficulty-routed, zone-preferred single-responder matcher."""

import asyncio
import json
import pathlib

from contracts.agent_interface import Agent, AgentInput, AgentOutput
from agents.responder_matching import (
    ResponderMatchingAgent, employee_level, fault_difficulty, match_responder,
)

ROOT = pathlib.Path(__file__).resolve().parents[3]
ROSTER = json.loads((ROOT / "data" / "employees.json").read_text(encoding="utf-8"))
BY_ID = {e["employee_id"]: e for e in ROSTER}
AS_OF = "2026-07-04"


def _m(fault):
    return match_responder(ROSTER, fault, as_of=AS_OF)


# --------------------------------------------------------------------------- #
# Difficulty routing
# --------------------------------------------------------------------------- #
def test_simple_task_goes_to_a_junior_in_zone():
    r = _m({"family": "energy", "equipment_class": "rectifier", "code": "PWR-FUSE-BLOWN", "region": "IDF-North"})
    assert r["employee_id"] == "EMP-004" and r["tier"] == "junior"


def test_complex_task_goes_to_a_senior_in_zone():
    r = _m({"family": "energy", "equipment_class": "rectifier", "code": "PWR-GRID-LOSS", "region": "IDF-North"})
    assert r["employee_id"] == "EMP-003" and r["tier"] == "senior"


def test_medium_task_goes_to_mid_level_not_the_senior():
    r = _m({"family": "energy", "equipment_class": "rectifier", "code": "PWR-DC-UV", "region": "IDF-East"})
    assert r["employee_id"] == "EMP-006" and r["tier"] == "confirmé"


def test_explicit_difficulty_override_reroutes():
    base = {"family": "energy", "equipment_class": "rectifier", "code": "PWR-DC-UV", "region": "IDF-North"}
    simple = _m({**base, "difficulty": "simple"})
    complex_ = _m({**base, "difficulty": "complex"})
    assert simple["level"] < complex_["level"]      # simple → less experienced than complex


# --------------------------------------------------------------------------- #
# Zone workflow (preferred, with incompatibility fallback)
# --------------------------------------------------------------------------- #
def test_in_zone_is_preferred():
    r = _m({"family": "transport", "equipment_class": "router", "code": "TRN-BACKHAUL-DOWN", "region": "IDF-North"})
    assert r["region"] == "IDF-North" and r["out_of_zone"] is False


def test_out_of_zone_fallback_when_none_available_in_zone():
    # IDF-South has only EMP-005 (energy, on_job) -> must fall back out of zone.
    r = _m({"family": "energy", "equipment_class": "rectifier", "code": "PWR-GRID-LOSS", "region": "IDF-South"})
    assert r["out_of_zone"] is True
    assert r["region"] != "IDF-South" and r["tier"] == "senior"


def test_region_agnostic_when_no_region_given():
    r = _m({"family": "rf", "equipment_class": "feeder", "code": "RF-VSWR-HIGH"})
    assert r is not None and r["out_of_zone"] is False


# --------------------------------------------------------------------------- #
# Competence gate / negative controls
# --------------------------------------------------------------------------- #
def test_off_domain_lead_never_picked():
    r = _m({"family": "rf", "equipment_class": "feeder", "code": "RF-VSWR-HIGH", "region": "IDF-East"})
    assert r["employee_id"] != "EMP-024"            # multi-domain lead has no rf skill


def test_unavailable_never_picked():
    r = _m({"family": "energy", "equipment_class": "rectifier", "code": "PWR-DC-UV", "region": "IDF-South"})
    assert r["employee_id"] != "EMP-005"            # on_job specialist excluded


def test_no_eligible_returns_none():
    assert _m({"family": "satellite", "equipment_class": "vsat", "code": "SAT-DOWN", "region": "IDF-North"}) is None


def test_level_rises_with_seniority_and_tasks():
    assert employee_level(BY_ID["EMP-004"], as_of=AS_OF) < employee_level(BY_ID["EMP-003"], as_of=AS_OF)


def test_difficulty_lookup():
    assert fault_difficulty({"code": "PWR-GRID-LOSS"}) == "complex"
    assert fault_difficulty({"code": "PWR-FUSE-BLOWN"}) == "simple"
    assert fault_difficulty({"code": "PWR-DC-UV"}) == "medium"
    assert fault_difficulty({"code": "UNKNOWN"}) == "medium"


# --------------------------------------------------------------------------- #
# Agent
# --------------------------------------------------------------------------- #
def _run(agent, ctx, family="energy"):
    return asyncio.run(agent.run(AgentInput(incident_id="INC-1", site_id="SITE", failure_family=family, context=ctx)))


def test_agent_satisfies_protocol():
    assert isinstance(ResponderMatchingAgent(roster=ROSTER, as_of=AS_OF), Agent)


def test_agent_notifies_exactly_one():
    agent = ResponderMatchingAgent(roster=ROSTER, as_of=AS_OF)
    out = _run(agent, {"fault": {"family": "energy", "equipment_class": "rectifier", "code": "PWR-GRID-LOSS", "region": "IDF-North"}})
    assert isinstance(out, AgentOutput)
    assert out.payload["notify"] == ["EMP-003"]
    assert out.payload["escalate"] is False
    assert out.payload["difficulty"] == "complex"
    json.loads(out.model_dump_json())


def test_agent_flags_out_of_zone():
    agent = ResponderMatchingAgent(roster=ROSTER, as_of=AS_OF)
    out = _run(agent, {"fault": {"family": "energy", "equipment_class": "rectifier", "code": "PWR-GRID-LOSS", "region": "IDF-South"}})
    assert out.payload["out_of_zone"] is True
    assert len(out.payload["notify"]) == 1


def test_agent_escalates_when_no_match():
    agent = ResponderMatchingAgent(roster=ROSTER, as_of=AS_OF)
    out = _run(agent, {"fault": {"family": "satellite", "equipment_class": "vsat", "code": "SAT-DOWN", "region": "IDF-North"}}, family="satellite")
    assert out.payload["escalate"] is True and out.payload["notify"] == []


def test_agent_derives_fault_from_findings():
    agent = ResponderMatchingAgent(roster=ROSTER, as_of=AS_OF)
    out = _run(agent, {
        "findings": {"correlation": {"equipment_class": "rectifier"}},
        "failures": [{"id": "F1", "code": "PWR-GRID-LOSS"}],
        "site": {"region": "IDF-North"},
    })
    assert out.payload["notify"] == ["EMP-003"]
