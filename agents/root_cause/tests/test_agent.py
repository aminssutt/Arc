"""Unit tests for the Root-Cause agent (issue #27) -- no network.

``vultr`` and ``retriever`` are constructor-injected and duck-typed, so pure
Python fakes drive the confidence gate deterministically: the fake retriever
returns canned evidence and records queries; the fake LLM returns a scripted
ranking per pass and records the messages it was sent.

Coverage map (issue #27 acceptance criteria):
* Satisfies the frozen ``Agent`` protocol; ``run`` -> JSON-round-trippable output.
* Gate: confidence >= threshold -> 1 pass, doc_request null; below -> pass 2 with a
  REFORMULATED query (!= pass-1 query); still below -> non-null doc_request.
* Invariants: >= 1 citation per cause (structural fallback when the LLM gives
  none); sum(refs_count) == len(retrieved_refs); causes sorted desc; output
  confidence == top cause.
* ``system_prompt`` override (empty string respected -- the `is not None` branch).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import agents.root_cause.agent as rc_mod
from agents.root_cause.agent import GateConfig, RootCauseAgent
from contracts.agent_interface import Agent, AgentInput, AgentOutput, RetrievedRef

_PROMPT_MD = Path(rc_mod.__file__).resolve().parent / "prompt.md"


# --------------------------------------------------------------------------- #
# Pure-Python fakes (duck-typed)
# --------------------------------------------------------------------------- #
class FakeRetriever:
    """Returns a scripted ref list per call; records queries in order."""

    def __init__(self, refs_per_call: list[list[RetrievedRef]]) -> None:
        self._refs_per_call = refs_per_call
        self.queries: list[str] = []
        self._i = 0

    async def query(self, text: str, top_k: int = 5) -> list[RetrievedRef]:
        self.queries.append(text)
        refs = self._refs_per_call[self._i] if self._i < len(self._refs_per_call) else []
        self._i += 1
        return list(refs)


class FakeVultr:
    """Returns a scripted ranking dict per call; records the messages sent."""

    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses
        self.calls: list = []
        self._i = 0

    async def structured_json(self, messages, *, max_tokens=600, temperature=0.0):
        self.calls.append(messages)
        resp = self._responses[self._i] if self._i < len(self._responses) else {}
        self._i += 1
        return dict(resp)


def _ref(doc: str, section: str = "sec", snippet: str = "evidence chunk") -> RetrievedRef:
    return RetrievedRef(doc_id=doc, section=section, snippet=snippet)


def _cause(cause: str, confidence: float, *, measurement="dc_plant_voltage_v", refs=(0,)) -> dict:
    return {
        "cause": cause,
        "confidence": confidence,
        "expected_measurement": measurement,
        "citation_refs": list(refs),
    }


def _input() -> AgentInput:
    return AgentInput(
        incident_id="INC-RC-001",
        site_id="SITE-PAR-014",
        failure_family="energy",
        context={"fault": {"failures": [{"code": "PWR-DC-UV", "equipment": "EQ-PAR-014-RECT-1"}]}},
    )


# --------------------------------------------------------------------------- #
# Protocol + JSON round-trip
# --------------------------------------------------------------------------- #
class TestProtocolAndRoundTrip:
    def test_satisfies_agent_protocol(self) -> None:
        agent = RootCauseAgent(FakeVultr([]), FakeRetriever([[]]))
        assert isinstance(agent, Agent)
        assert agent.name == "root_cause"

    def test_requires_injected_dependencies(self) -> None:
        with pytest.raises(ValueError):
            RootCauseAgent(None, FakeRetriever([[]]))
        with pytest.raises(ValueError):
            RootCauseAgent(FakeVultr([]), None)

    @pytest.mark.asyncio
    async def test_run_returns_json_round_trippable_output(self) -> None:
        vultr = FakeVultr([{"ranked_causes": [_cause("rectifier module failed", 0.9)],
                            "followup_query": "", "missing_doc": None}])
        retriever = FakeRetriever([[_ref("doc-a")]])
        out = await RootCauseAgent(vultr, retriever).run(_input())

        assert isinstance(out, AgentOutput)
        assert out.agent == "root_cause"
        dumped = out.model_dump(mode="json")
        restored = AgentOutput.model_validate(json.loads(json.dumps(dumped)))
        assert restored == out


# --------------------------------------------------------------------------- #
# Confidence gate
# --------------------------------------------------------------------------- #
class TestConfidenceGate:
    @pytest.mark.asyncio
    async def test_high_confidence_stops_after_one_pass(self) -> None:
        vultr = FakeVultr([{"ranked_causes": [_cause("rectifier module failed", 0.9)],
                            "followup_query": "", "missing_doc": None}])
        retriever = FakeRetriever([[_ref("doc-a")], [_ref("doc-b")]])
        out = await RootCauseAgent(vultr, retriever).run(_input())

        assert len(retriever.queries) == 1                     # single retrieval pass
        assert len(out.payload["retrieval_passes"]) == 1
        assert out.payload["doc_request"] is None
        assert out.confidence == 0.9

    @pytest.mark.asyncio
    async def test_low_confidence_reretrieves_with_reformulated_query(self) -> None:
        followup = "SITE-PAR-014 rectifier discharge-curve vendor alarm-signature table"
        vultr = FakeVultr([
            {"ranked_causes": [_cause("rectifier module failed", 0.4)],
             "followup_query": followup, "missing_doc": None},
            {"ranked_causes": [_cause("rectifier module failed", 0.9)],
             "followup_query": "", "missing_doc": None},
        ])
        retriever = FakeRetriever([[_ref("doc-a")], [_ref("doc-b")]])
        out = await RootCauseAgent(vultr, retriever).run(_input())

        assert len(retriever.queries) == 2                     # gate triggered a 2nd pass
        assert retriever.queries[1] == followup                # used the LLM reformulation
        assert retriever.queries[1] != retriever.queries[0]    # genuinely different query
        assert out.payload["doc_request"] is None              # 2nd pass cleared the gate
        assert out.confidence == 0.9

    @pytest.mark.asyncio
    async def test_persistently_low_confidence_emits_doc_request(self) -> None:
        vultr = FakeVultr([
            {"ranked_causes": [_cause("ambiguous", 0.3)], "followup_query": "angle two", "missing_doc": None},
            {"ranked_causes": [_cause("ambiguous", 0.3)], "followup_query": "", "missing_doc": None},
        ])
        retriever = FakeRetriever([[_ref("doc-a")], [_ref("doc-b")]])
        out = await RootCauseAgent(vultr, retriever).run(_input())

        assert len(out.payload["retrieval_passes"]) == 2       # exhausted the pass budget
        dr = out.payload["doc_request"]
        assert dr is not None
        assert dr["agent"] == "root_cause"
        assert dr["status"] == "missing"
        assert dr["description"] and dr["query"]
        assert out.confidence == 0.3

    @pytest.mark.asyncio
    async def test_reformulation_falls_back_when_llm_omits_followup(self) -> None:
        # Low confidence but no followup_query -> a widened seed fallback is used,
        # still different from pass 1.
        vultr = FakeVultr([
            {"ranked_causes": [_cause("x", 0.2)], "followup_query": "", "missing_doc": None},
            {"ranked_causes": [_cause("x", 0.2)], "followup_query": "", "missing_doc": None},
        ])
        retriever = FakeRetriever([[_ref("doc-a")], [_ref("doc-b")]])
        await RootCauseAgent(vultr, retriever).run(_input())
        assert len(retriever.queries) == 2
        assert retriever.queries[1] != retriever.queries[0]


# --------------------------------------------------------------------------- #
# Output invariants
# --------------------------------------------------------------------------- #
class TestInvariants:
    @pytest.mark.asyncio
    async def test_every_cause_has_at_least_one_citation_via_fallback(self) -> None:
        # The LLM supplies NO citation index; the agent must still attach one.
        cause_no_cites = {"cause": "rectifier module failed", "confidence": 0.9,
                          "expected_measurement": "rectifier_output_a", "citation_refs": []}
        vultr = FakeVultr([{"ranked_causes": [cause_no_cites], "followup_query": "", "missing_doc": None}])
        retriever = FakeRetriever([[_ref("doc-a", "3.2 UV alarm")]])
        out = await RootCauseAgent(vultr, retriever).run(_input())

        causes = out.payload["ranked_causes"]
        assert causes and all(len(c["citations"]) >= 1 for c in causes)
        assert causes[0]["citations"][0]["doc_id"] == "doc-a"

    @pytest.mark.asyncio
    async def test_invalid_citation_indices_fall_back_to_top_ref(self) -> None:
        # Out-of-range + boolean indices are junk -> structural fallback to [0].
        cause = {"cause": "c", "confidence": 0.9, "expected_measurement": "vswr_ratio",
                 "citation_refs": [99, True, -1]}
        vultr = FakeVultr([{"ranked_causes": [cause], "followup_query": "", "missing_doc": None}])
        retriever = FakeRetriever([[_ref("doc-a")]])
        out = await RootCauseAgent(vultr, retriever).run(_input())
        assert len(out.payload["ranked_causes"][0]["citations"]) == 1

    @pytest.mark.asyncio
    async def test_sum_of_pass_refs_counts_equals_evidence_pool(self) -> None:
        # Force two passes with different ref counts (2 then 3).
        vultr = FakeVultr([
            {"ranked_causes": [_cause("x", 0.3)], "followup_query": "next", "missing_doc": None},
            {"ranked_causes": [_cause("x", 0.3)], "followup_query": "", "missing_doc": None},
        ])
        retriever = FakeRetriever([
            [_ref("a"), _ref("b")],
            [_ref("c"), _ref("d"), _ref("e")],
        ])
        out = await RootCauseAgent(vultr, retriever).run(_input())

        passes = out.payload["retrieval_passes"]
        assert [p["refs_count"] for p in passes] == [2, 3]
        assert sum(p["refs_count"] for p in passes) == len(out.retrieved_refs) == 5

    @pytest.mark.asyncio
    async def test_causes_sorted_desc_and_confidence_equals_top(self) -> None:
        vultr = FakeVultr([{
            "ranked_causes": [
                _cause("A weak", 0.3),
                _cause("B strong", 0.9),
                _cause("C middle", 0.6),
            ],
            "followup_query": "", "missing_doc": None,
        }])
        retriever = FakeRetriever([[_ref("doc-a")]])
        out = await RootCauseAgent(vultr, retriever).run(_input())

        confidences = [c["confidence"] for c in out.payload["ranked_causes"]]
        assert confidences == sorted(confidences, reverse=True) == [0.9, 0.6, 0.3]
        assert out.confidence == out.payload["ranked_causes"][0]["confidence"] == 0.9


# --------------------------------------------------------------------------- #
# system_prompt override (empty string respected)
# --------------------------------------------------------------------------- #
class TestSystemPrompt:
    @pytest.mark.asyncio
    async def test_override_replaces_prompt_md(self) -> None:
        vultr = FakeVultr([{"ranked_causes": [_cause("x", 0.9)], "followup_query": "", "missing_doc": None}])
        agent = RootCauseAgent(vultr, FakeRetriever([[_ref("a")]]), system_prompt="RC-PERSONA")
        await agent.run(_input())
        assert agent._system_prompt == "RC-PERSONA"
        assert vultr.calls[0][0]["content"] == "RC-PERSONA"

    @pytest.mark.asyncio
    async def test_empty_string_prompt_is_respected_not_replaced_by_file(self) -> None:
        # "" is not None -> it must be kept, NOT replaced by prompt.md.
        vultr = FakeVultr([{"ranked_causes": [_cause("x", 0.9)], "followup_query": "", "missing_doc": None}])
        agent = RootCauseAgent(vultr, FakeRetriever([[_ref("a")]]), system_prompt="")
        await agent.run(_input())
        assert agent._system_prompt == ""
        assert vultr.calls[0][0]["content"] == ""

    def test_none_falls_back_to_prompt_md(self) -> None:
        agent = RootCauseAgent(FakeVultr([]), FakeRetriever([[]]), system_prompt=None)
        assert agent._system_prompt == _PROMPT_MD.read_text(encoding="utf-8")
        assert agent._system_prompt.strip() != ""


# --------------------------------------------------------------------------- #
# Empty-evidence gate fix: ungrounded causes are flagged uncited, confidence
# floored to 0.0, doc_request mandatory; grounded happy path stays 4 strict keys.
# --------------------------------------------------------------------------- #
class TestEmptyEvidencePool:
    @pytest.mark.asyncio
    async def test_pool_empty_flags_uncited_floors_confidence_and_requests_doc(self) -> None:
        # Retriever returns nothing on every pass; the LLM still asserts a cause.
        vultr = FakeVultr([
            {"ranked_causes": [_cause("ungrounded rectifier guess", 0.9)],
             "followup_query": "", "missing_doc": None},
            {"ranked_causes": [_cause("ungrounded rectifier guess", 0.9)],
             "followup_query": "", "missing_doc": None},
        ])
        retriever = FakeRetriever([[], []])  # zero evidence, both passes
        out = await RootCauseAgent(vultr, retriever).run(_input())

        assert out.retrieved_refs == []                       # empty evidence pool
        causes = out.payload["ranked_causes"]
        assert len(causes) == 1
        cause = causes[0]
        # The invariant relaxes to: >= 1 citation UNLESS explicitly uncited.
        assert cause["uncited"] is True
        assert cause["citations"] == []
        assert cause["confidence"] == 0.0                     # floored, never a confident fact
        assert out.confidence == 0.0                          # max grounded == 0.0
        dr = out.payload["doc_request"]                        # mandatory when ungrounded
        assert dr is not None
        assert dr["status"] == "missing"

    @pytest.mark.asyncio
    async def test_happy_path_grounded_cause_has_exactly_four_keys_no_uncited(self) -> None:
        # Evidence present + cited -> grounded: entry must NOT carry the uncited key.
        vultr = FakeVultr([{"ranked_causes": [_cause("rectifier module failed", 0.9)],
                            "followup_query": "", "missing_doc": None}])
        retriever = FakeRetriever([[_ref("doc-a")]])
        out = await RootCauseAgent(vultr, retriever).run(_input())

        cause = out.payload["ranked_causes"][0]
        assert set(cause.keys()) == {"cause", "confidence", "citations", "expected_measurement"}
        assert "uncited" not in cause
        assert cause["confidence"] == 0.9
        assert out.payload["doc_request"] is None
