"""Tests for the Remediation agent (AGA.2 #29).

Acceptance criteria:
- Ordered, actionable procedure on the demo scenario.
- >= 2 CITED safety steps (grounded in retrieved corpus docs).

Vultr + retriever are injected fakes -> fully offline, no API key.
"""

import asyncio
import json

import pytest

from contracts.agent_interface import Agent, AgentInput, AgentOutput, RetrievedRef
from agents.remediation import MIN_SAFETY_STEPS, RemediationAgent, RemediationError

PROC_REF = RetrievedRef(
    doc_id="eltek-flatpack2-om-manual", section="3.2 DC Undervoltage Alarm",
    snippet="Replace any rectifier module that stays in 'fail' after an input reset.",
    score=None,
)
SAFETY_REF = RetrievedRef(
    doc_id="site-safety-dc-power-plant", section="2 Lockout/Tagout and PPE",
    snippet="Open and lock the battery disconnect; verify zero energy before touching any busbar.",
    score=None,
)


class FakeRetriever:
    def __init__(self, safety=(SAFETY_REF,), proc=(PROC_REF,)):
        self._safety = list(safety)
        self._proc = list(proc)
        self.queries: list[str] = []

    async def query(self, text: str, top_k: int = 5) -> list[RetrievedRef]:
        self.queries.append(text)
        return self._safety if "safety" in text.lower() else self._proc


class FakeVultr:
    def __init__(self, result):
        self._result = result
        self.calls = 0

    async def structured_json(self, prompt, *, schema=None, max_tokens=512, temperature=0.0):
        self.calls += 1
        return self._result


_GOOD_RESULT = {
    "procedure": [
        "Read the plant controller; confirm bus voltage and which modules report 'fail'.",
        "If AC mains present, reset any tripped rectifier input breaker.",
        "Replace the rectifier module that stays in 'fail' after reset.",
    ],
    "safety_steps": [
        {"step": "Apply lockout/tagout on the battery disconnect and load breaker.",
         "doc_id": "site-safety-dc-power-plant", "section": "2"},
        {"step": "Verify zero energy with a meter before touching the busbar; wear arc-rated PPE.",
         "doc_id": "site-safety-dc-power-plant", "section": "2"},
    ],
    "parts_needed": ["Eltek Flatpack2 HE 48V/2000W rectifier module"],
    "crew_skill": "power",
}


def _input():
    return AgentInput(
        incident_id="INC-DEMO-001",
        site_id="PAR-021-NORD",
        failure_family="energy",
        context={"findings": {"root_cause": {"top_cause": {
            "failure_id": "F2", "label": "rectifier module failure (DC undervoltage)",
        }}}},
    )


def _run(agent):
    return asyncio.run(agent.run(_input()))


def test_satisfies_agent_protocol():
    assert isinstance(RemediationAgent(FakeVultr(_GOOD_RESULT), FakeRetriever()), Agent)


def test_ordered_procedure_and_two_cited_safety_steps():
    agent = RemediationAgent(FakeVultr(_GOOD_RESULT), FakeRetriever())
    out = _run(agent)
    assert isinstance(out, AgentOutput)
    assert out.payload["procedure"] == _GOOD_RESULT["procedure"]  # order preserved
    assert len(out.payload["safety_steps"]) >= MIN_SAFETY_STEPS
    # Every safety step carries a citation that resolves to a retrieved doc.
    retrieved_ids = {r.doc_id for r in out.retrieved_refs}
    for s in out.payload["safety_steps"]:
        assert s["doc_id"] in retrieved_ids
    assert out.citations and all(c.doc_id in retrieved_ids for c in out.citations)
    assert out.payload["parts_needed"]
    json.loads(out.model_dump_json())


def test_hallucinated_citation_is_dropped_and_fails_closed():
    bad = {**_GOOD_RESULT, "safety_steps": [
        {"step": "real cited step", "doc_id": "site-safety-dc-power-plant", "section": "2"},
        {"step": "invented step", "doc_id": "no-such-doc", "section": "9"},
    ]}
    agent = RemediationAgent(FakeVultr(bad), FakeRetriever())
    with pytest.raises(RemediationError):
        _run(agent)  # only 1 grounded safety step < MIN_SAFETY_STEPS


def test_missing_confirmed_cause_raises():
    agent = RemediationAgent(FakeVultr(_GOOD_RESULT), FakeRetriever())
    bad = AgentInput(incident_id="X", site_id="S", failure_family="energy", context={})
    with pytest.raises(RemediationError):
        asyncio.run(agent.run(bad))


def test_no_safety_docs_refuses():
    agent = RemediationAgent(FakeVultr(_GOOD_RESULT), FakeRetriever(safety=()))
    with pytest.raises(RemediationError):
        _run(agent)
