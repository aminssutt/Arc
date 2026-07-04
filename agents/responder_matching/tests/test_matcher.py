"""Unit tests for the deterministic responder matcher + the agent."""

import asyncio
import json
import pathlib

from contracts.agent_interface import Agent, AgentInput, AgentOutput
from agents.responder_matching import ResponderMatchingAgent, match_responders, score_employee
from agents.responder_matching.matcher import REFERENCE_DATE

ROOT = pathlib.Path(__file__).resolve().parents[3]
ROSTER = json.loads((ROOT / "data" / "employees.json").read_text(encoding="utf-8"))
BY_ID = {e["employee_id"]: e for e in ROSTER}

AS_OF = "2026-07-04"
DC_UV = {"family": "energy", "equipment_class": "rectifier", "code": "PWR-DC-UV"}


# --------------------------------------------------------------------------- #
# Matcher
# --------------------------------------------------------------------------- #
def test_top_match_is_the_right_specialist():
    out = match_responders(ROSTER, DC_UV, as_of=AS_OF)
    assert out[0]["employee_id"] == "EMP-001"        # 3 prior PWR-DC-UV fixes
    assert 2 <= len(out) <= 3
    assert out[0]["score"] > out[-1]["score"]


def test_only_available_are_returned():
    out = match_responders(ROSTER, DC_UV, as_of=AS_OF)
    assert all(r["status"] == "available" for r in out)
    assert "EMP-005" not in {r["employee_id"] for r in out}   # on_job specialist excluded


def test_reason_is_explainable():
    out = match_responders(ROSTER, DC_UV, as_of=AS_OF)
    reason = out[0]["reason"]
    assert "famille energy" in reason and "fix(es) similaire" in reason
    assert out[0]["matched_skills"]


def test_off_domain_senior_scores_below_floor():
    # EMP-024: 16y multi-domain lead, but no rf skill -> must not clear the floor for rf.
    score, _ = score_employee(BY_ID["EMP-024"],
                              {"family": "rf", "equipment_class": "feeder", "code": "RF-VSWR-HIGH"},
                              as_of=AS_OF)
    assert score < 0.25


def test_no_confident_responder_returns_empty():
    # A family nobody available specializes in -> empty (escalate), not a wrong page.
    out = match_responders(ROSTER, {"family": "satellite", "equipment_class": "vsat", "code": "SAT-DOWN"}, as_of=AS_OF)
    assert out == []


def test_seniority_is_deterministic_via_as_of():
    a = match_responders(ROSTER, DC_UV, as_of="2026-07-04")
    b = match_responders(ROSTER, DC_UV, as_of="2026-07-04")
    assert a == b


# --------------------------------------------------------------------------- #
# Agent
# --------------------------------------------------------------------------- #
def _run(agent, ctx):
    inp = AgentInput(incident_id="INC-1", site_id="SITE-PAR-014", failure_family=ctx.get("fault", {}).get("family", "energy"), context=ctx)
    return asyncio.run(agent.run(inp))


def test_agent_satisfies_protocol():
    assert isinstance(ResponderMatchingAgent(roster=ROSTER, as_of=AS_OF), Agent)


def test_agent_emits_notify_list_and_responders():
    agent = ResponderMatchingAgent(roster=ROSTER, as_of=AS_OF)
    out = _run(agent, {"fault": DC_UV})
    assert isinstance(out, AgentOutput)
    assert out.payload["notify"][0] == "EMP-001"
    assert 2 <= len(out.payload["notify"]) <= 3
    assert out.payload["escalate"] is False
    json.loads(out.model_dump_json())


def test_agent_derives_fault_from_findings():
    # No explicit fault -> derive from correlation equipment_class + failure code.
    agent = ResponderMatchingAgent(roster=ROSTER, as_of=AS_OF)
    out = _run(agent, {
        "findings": {"correlation": {"equipment_class": "rectifier"}},
        "failures": [{"id": "F1", "code": "PWR-DC-UV"}],
    })
    assert out.payload["notify"][0] == "EMP-001"


def test_agent_escalates_when_no_match():
    agent = ResponderMatchingAgent(roster=ROSTER, as_of=AS_OF)
    out = _run(agent, {"fault": {"family": "satellite", "equipment_class": "vsat", "code": "SAT-DOWN"}})
    assert out.payload["escalate"] is True
    assert out.payload["notify"] == []
    assert out.confidence == 0.0


def test_optional_semantic_rerank_blends():
    async def scorer(fault_text, employee_texts):
        # Boost whoever is listed last, to prove the blend reorders.
        return [0.0] * (len(employee_texts) - 1) + [1.0]

    base = ResponderMatchingAgent(roster=ROSTER, as_of=AS_OF)
    base_out = _run(base, {"fault": DC_UV})
    reranked = ResponderMatchingAgent(roster=ROSTER, as_of=AS_OF, semantic_scorer=scorer, semantic_weight=0.9)
    rr_out = _run(reranked, {"fault": DC_UV})
    assert rr_out.payload["notify"] != base_out.payload["notify"]     # rerank changed the order
    assert "semantic_score" in rr_out.payload["responders"][0]
