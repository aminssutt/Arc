"""Unit tests for the Correlation agent (issue #26) -- no network.

``vultr`` and ``retriever`` are constructor-injected and duck-typed, so pure
Python fakes replace them (no MockTransport, no API key). The topology comes from
the bundled fixture, so the deterministic walk is asserted against known ids.

Coverage map (issue #26 acceptance criteria):
* Satisfies the frozen ``Agent`` protocol; ``run`` -> valid, JSON-round-trippable
  ``AgentOutput``.
* Deterministic walk: PWR-DC-UV @ SITE-PAR-014 -> EQ-PAR-014-RECT-1;
  RF-VSWR-HIGH -> EQ-PAR-014-FEED-1 (generalization).
* Anti-hallucination: an LLM plan naming a class absent from the site is
  overridden by the taxonomy -- the structured walk decides, not the model.
* ``system_prompt`` override replaces prompt.md; ``None`` falls back to prompt.md;
  >= 1 Citation when the retriever was consulted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import agents.correlation.agent as corr_mod
from agents.correlation.agent import CorrelationAgent
from contracts.agent_interface import Agent, AgentInput, AgentOutput, Citation, RetrievedRef

_FIXTURES = Path(corr_mod.__file__).resolve().parent / "fixtures"
_PROMPT_MD = Path(corr_mod.__file__).resolve().parent / "prompt.md"


# --------------------------------------------------------------------------- #
# Pure-Python fakes (duck-typed)
# --------------------------------------------------------------------------- #
class FakeVultr:
    """Captures the messages it is sent and returns a canned plan dict."""

    def __init__(self, plan: dict) -> None:
        self._plan = plan
        self.calls: list = []

    async def structured_json(self, messages, *, schema=None, max_tokens=350, temperature=0.0):
        self.calls.append(messages)
        return dict(self._plan)


class FakeRetriever:
    """Returns a fixed ref list; records the queries it received."""

    def __init__(self, refs: list[RetrievedRef]) -> None:
        self._refs = refs
        self.queries: list[str] = []

    async def query(self, text: str, top_k: int = 4) -> list[RetrievedRef]:
        self.queries.append(text)
        return list(self._refs)[:top_k]


def _load_input(name: str) -> AgentInput:
    return AgentInput.model_validate(json.loads((_FIXTURES / name).read_text(encoding="utf-8")))


def _rf_vswr_input() -> AgentInput:
    return AgentInput(
        incident_id="INC-RF-001",
        site_id="SITE-PAR-014",
        failure_family="rf",
        context={"fault_event": {"failures": [{"code": "RF-VSWR-HIGH", "severity": "major"}]}},
    )


# --------------------------------------------------------------------------- #
# Protocol + JSON round-trip
# --------------------------------------------------------------------------- #
class TestProtocolAndRoundTrip:
    def test_satisfies_agent_protocol(self) -> None:
        agent = CorrelationAgent()
        assert isinstance(agent, Agent)
        assert agent.name == "correlation"

    @pytest.mark.asyncio
    async def test_run_returns_json_round_trippable_output(self) -> None:
        agent = CorrelationAgent(vultr=None, retriever=None)  # fully offline
        out = await agent.run(_load_input("fault_pwr_dc_uv.json"))

        assert isinstance(out, AgentOutput)
        assert out.agent == "correlation"
        assert out.incident_id == "INC-DEMO-CORR-001"
        dumped = out.model_dump(mode="json")
        restored = AgentOutput.model_validate(json.loads(json.dumps(dumped)))
        assert restored == out


# --------------------------------------------------------------------------- #
# Deterministic walk
# --------------------------------------------------------------------------- #
class TestDeterministicWalk:
    @pytest.mark.asyncio
    async def test_pwr_dc_uv_localizes_to_rectifier_module(self) -> None:
        agent = CorrelationAgent(vultr=None, retriever=None)
        out = await agent.run(_load_input("fault_pwr_dc_uv.json"))
        p = out.payload
        assert p["located_equipment_id"] == "EQ-PAR-014-RECT-1"
        assert p["equipment_class"] == "rectifier"
        assert p["located_site_id"] == "SITE-PAR-014"

    @pytest.mark.asyncio
    async def test_rf_vswr_generalizes_to_feeder(self) -> None:
        agent = CorrelationAgent(vultr=None, retriever=None)
        out = await agent.run(_rf_vswr_input())
        p = out.payload
        assert p["located_equipment_id"] == "EQ-PAR-014-FEED-1"
        assert p["equipment_class"] == "feeder"

    @pytest.mark.asyncio
    async def test_walk_is_stable_across_repeated_runs(self) -> None:
        agent = CorrelationAgent(vultr=None, retriever=None)
        inp = _load_input("fault_pwr_dc_uv.json")
        first = await agent.run(inp)
        second = await agent.run(inp)
        assert (
            first.payload["located_equipment_id"]
            == second.payload["located_equipment_id"]
            == "EQ-PAR-014-RECT-1"
        )


# --------------------------------------------------------------------------- #
# Anti-hallucination: the walk overrides an out-of-inventory LLM class
# --------------------------------------------------------------------------- #
class TestAntiHallucination:
    @pytest.mark.asyncio
    async def test_llm_class_absent_from_site_is_overridden_by_taxonomy(self) -> None:
        # The planner hallucinates a class that does not exist at the site.
        fake_vultr = FakeVultr(
            {
                "target_equipment_class": "transformer",  # not in the topology
                "walk_strategy": "made up",
                "retrieval_query": "transformer fault",
                "needs_retrieval": False,
                "rationale": "hallucinated",
            }
        )
        agent = CorrelationAgent(vultr=fake_vultr, retriever=None)
        out = await agent.run(_load_input("fault_pwr_dc_uv.json"))

        # The structured walk still lands on the taxonomy-correct equipment...
        assert out.payload["located_equipment_id"] == "EQ-PAR-014-RECT-1"
        # ...and the plan records that the LLM class was overridden.
        plan = out.payload["plan"]
        assert plan["source"] == "deterministic-fallback"
        assert plan["overridden_from"] == "transformer"
        assert plan["target_equipment_class"] == "rectifier"


# --------------------------------------------------------------------------- #
# system_prompt override + citations
# --------------------------------------------------------------------------- #
class TestSystemPromptAndCitations:
    @pytest.mark.asyncio
    async def test_system_prompt_override_replaces_prompt_md(self) -> None:
        fake_vultr = FakeVultr(
            {
                "target_equipment_class": "rectifier",
                "walk_strategy": "s",
                "retrieval_query": "q",
                "needs_retrieval": False,
                "rationale": "r",
            }
        )
        agent = CorrelationAgent(vultr=fake_vultr, retriever=None, system_prompt="PERSONA-OVERRIDE")
        await agent.run(_load_input("fault_pwr_dc_uv.json"))

        system_message = fake_vultr.calls[0][0]
        assert system_message["role"] == "system"
        assert system_message["content"] == "PERSONA-OVERRIDE"

    @pytest.mark.asyncio
    async def test_system_prompt_none_falls_back_to_prompt_md(self) -> None:
        fake_vultr = FakeVultr(
            {
                "target_equipment_class": "rectifier",
                "walk_strategy": "s",
                "retrieval_query": "q",
                "needs_retrieval": False,
                "rationale": "r",
            }
        )
        agent = CorrelationAgent(vultr=fake_vultr, retriever=None, system_prompt=None)
        await agent.run(_load_input("fault_pwr_dc_uv.json"))

        system_message = fake_vultr.calls[0][0]
        assert system_message["content"] == _PROMPT_MD.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_at_least_one_citation_when_retriever_consulted(self) -> None:
        ref = RetrievedRef(
            doc_id="eltek-flatpack2-om-manual",
            section="3.2 DC Undervoltage Alarm",
            snippet="A -48V DC plant undervoltage points at the rectifier module.",
        )
        retriever = FakeRetriever([ref])
        agent = CorrelationAgent(vultr=None, retriever=retriever)  # deterministic plan needs_retrieval=True
        out = await agent.run(_load_input("fault_pwr_dc_uv.json"))

        assert retriever.queries, "the retriever should have been consulted"
        assert len(out.citations) >= 1
        assert all(isinstance(c, Citation) for c in out.citations)
        assert out.payload["retrieval_passes"] == 1


# --------------------------------------------------------------------------- #
# Taxonomy deviation flag (fix: plan.taxonomy_class + plan.deviation, computed
# on the FINAL target_class after any anti-absent-class fallback)
# --------------------------------------------------------------------------- #
class TestTaxonomyDeviation:
    @pytest.mark.asyncio
    async def test_deviation_true_when_llm_class_present_but_taxonomically_wrong(self) -> None:
        # battery_string EXISTS at SITE-PAR-014, so it is not overridden; but the
        # taxonomy for PWR-DC-UV is rectifier -> the deviation must be flagged.
        fake_vultr = FakeVultr(
            {
                "target_equipment_class": "battery_string",
                "walk_strategy": "s",
                "retrieval_query": "q",
                "needs_retrieval": False,
                "rationale": "r",
            }
        )
        agent = CorrelationAgent(vultr=fake_vultr, retriever=None)
        out = await agent.run(_load_input("fault_pwr_dc_uv.json"))

        plan = out.payload["plan"]
        assert plan["deviation"] is True
        assert plan["taxonomy_class"] == "rectifier"
        assert plan["target_equipment_class"] == "battery_string"
        assert plan["source"] == "llm"  # present class -> LLM keeps its latitude
        # The walk followed the (flagged) LLM class, landing on the battery string.
        assert out.payload["located_equipment_id"] == "EQ-PAR-014-BATT-1"

    @pytest.mark.asyncio
    async def test_deviation_false_after_absent_class_fallback(self) -> None:
        # transformer is ABSENT -> corrected back to the taxonomy class; the final
        # target_class then equals the taxonomy, so deviation must be False.
        fake_vultr = FakeVultr(
            {
                "target_equipment_class": "transformer",
                "walk_strategy": "made up",
                "retrieval_query": "q",
                "needs_retrieval": False,
                "rationale": "hallucinated",
            }
        )
        agent = CorrelationAgent(vultr=fake_vultr, retriever=None)
        out = await agent.run(_load_input("fault_pwr_dc_uv.json"))

        plan = out.payload["plan"]
        assert plan["deviation"] is False
        assert plan["taxonomy_class"] == "rectifier"
        assert plan["target_equipment_class"] == "rectifier"
        assert plan["source"] == "deterministic-fallback"
        assert plan["overridden_from"] == "transformer"
        assert out.payload["located_equipment_id"] == "EQ-PAR-014-RECT-1"
