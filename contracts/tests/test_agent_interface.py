"""Contract test locking the FROZEN Agent/Tool interface (issue #7 / P0.7).

Test-only: this module asserts the frozen contract in
``contracts.agent_interface`` behaves as promised and that the reference
``EchoAgent`` satisfies it. No production code is imported for mutation and none
is touched here -- if any assertion below fails, the freeze was broken, not the
test.

Coverage map (issue #7 acceptance criteria):
1. ``EchoAgent`` structurally satisfies the ``@runtime_checkable`` ``Agent``
   protocol (no inheritance) and its async ``run`` returns a valid
   ``AgentOutput``.
2. ``AgentOutput`` survives a JSON round-trip
   (``model_dump(mode="json")`` -> ``model_validate``) with no loss.
3. ``confidence`` bounds ``[0, 1]`` are enforced.
4. ``extra="forbid"`` rejects unknown fields on ``AgentInput`` / ``AgentOutput``
   (and the nested evidence models that ride inside ``AgentOutput``).
5. The three tool model pairs (Cost / Inventory / Dispatch) expose a derivable
   JSON schema.
"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, ValidationError

from contracts.agent_interface import (
    Agent,
    AgentInput,
    AgentOutput,
    Citation,
    CostQuery,
    CostReport,
    DispatchBooking,
    DispatchRequest,
    InventoryLine,
    InventoryMatch,
    InventoryQuery,
    RetrievedRef,
)
from contracts.echo_agent import EchoAgent


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def sample_input() -> AgentInput:
    """A realistic incident envelope handed to an agent by the orchestrator."""
    return AgentInput(
        incident_id="INC-001",
        site_id="SITE-42",
        failure_family="energy/power",
        context={"alarm": "rectifier_failure", "dc_plant_v": -47.1},
    )


@pytest.fixture
def rich_output() -> AgentOutput:
    """An AgentOutput exercising every field, incl. nested refs and citations."""
    return AgentOutput(
        incident_id="INC-001",
        agent="root_cause",
        summary="Rectifier module A failed; DC plant running on battery reserve.",
        payload={"ranked_causes": [{"cause": "rectifier_a", "p": 0.7}]},
        retrieved_refs=[
            RetrievedRef(
                doc_id="RUNBOOK-DC",
                section="4.2 Rectifier faults",
                snippet="A single rectifier failure keeps the plant on reserve.",
                score=0.91,
            )
        ],
        citations=[
            Citation(
                doc_id="RUNBOOK-DC",
                section="4.2 Rectifier faults",
                snippet="keeps the plant on reserve",
            )
        ],
        confidence=0.7,
    )


# --------------------------------------------------------------------------- #
# 1. EchoAgent satisfies the Agent protocol; run() returns a valid AgentOutput
# --------------------------------------------------------------------------- #
class TestAgentProtocol:
    def test_echo_agent_satisfies_runtime_checkable_protocol_without_inheritance(
        self,
    ) -> None:
        # Arrange
        agent = EchoAgent()
        # Act / Assert -- structural conformance, and it is NOT a subclass
        assert isinstance(agent, Agent)
        assert Agent not in type(agent).__mro__
        assert agent.name == "echo"

    def test_object_missing_async_run_is_not_an_agent(self) -> None:
        # Arrange -- a look-alike that only provides `name`, not `run`
        class NotAnAgent:
            name = "nope"

        # Act / Assert -- the protocol requires the async `run` too
        assert not isinstance(NotAnAgent(), Agent)

    @pytest.mark.asyncio
    async def test_run_returns_a_valid_agent_output(
        self, sample_input: AgentInput
    ) -> None:
        # Arrange
        agent = EchoAgent()
        # Act
        result = await agent.run(sample_input)
        # Assert -- typed, correlated, in-range, and re-validatable
        assert isinstance(result, AgentOutput)
        assert result.incident_id == sample_input.incident_id
        assert result.agent == "echo"
        assert 0.0 <= result.confidence <= 1.0
        assert result.payload["echoed_context"] == sample_input.context
        # An AgentOutput is valid iff pydantic can re-validate its own dump.
        assert AgentOutput.model_validate(result.model_dump()) == result


# --------------------------------------------------------------------------- #
# 2. AgentOutput JSON round-trip with no loss
# --------------------------------------------------------------------------- #
class TestAgentOutputJsonRoundTrip:
    def test_model_dump_json_mode_is_pure_json_and_round_trips(
        self, rich_output: AgentOutput
    ) -> None:
        # Arrange
        as_json = rich_output.model_dump(mode="json")
        # Act -- prove it is genuine JSON (survives a real dumps/loads cycle)
        reloaded = json.loads(json.dumps(as_json))
        restored = AgentOutput.model_validate(reloaded)
        # Assert -- byte-for-byte structural equality, no field lost
        assert restored == rich_output
        assert restored.model_dump(mode="json") == as_json

    def test_model_dump_json_string_round_trips(
        self, rich_output: AgentOutput
    ) -> None:
        # Arrange / Act
        payload = rich_output.model_dump_json()
        restored = AgentOutput.model_validate_json(payload)
        # Assert -- nested refs and citations survive intact
        assert restored == rich_output
        assert restored.retrieved_refs == rich_output.retrieved_refs
        assert restored.citations == rich_output.citations


# --------------------------------------------------------------------------- #
# 3. confidence bounds [0, 1]
# --------------------------------------------------------------------------- #
class TestConfidenceBounds:
    @pytest.mark.parametrize("bad", [-0.01, 1.01, -1.0, 2.0, float("nan")])
    def test_confidence_out_of_range_is_rejected(self, bad: float) -> None:
        with pytest.raises(ValidationError):
            AgentOutput(incident_id="i", agent="a", summary="s", confidence=bad)

    @pytest.mark.parametrize("ok", [0.0, 0.5, 1.0])
    def test_confidence_on_and_within_bounds_is_accepted(self, ok: float) -> None:
        out = AgentOutput(incident_id="i", agent="a", summary="s", confidence=ok)
        assert out.confidence == ok


# --------------------------------------------------------------------------- #
# 4. extra="forbid" rejects unknown fields
# --------------------------------------------------------------------------- #
class TestExtraForbid:
    @pytest.mark.parametrize(
        "model, valid_kwargs",
        [
            (AgentInput, {"incident_id": "i", "site_id": "s", "failure_family": "f"}),
            (
                AgentOutput,
                {"incident_id": "i", "agent": "a", "summary": "s", "confidence": 0.5},
            ),
            (RetrievedRef, {"doc_id": "d", "section": "s", "snippet": "x"}),
            (Citation, {"doc_id": "d", "section": "s"}),
        ],
    )
    def test_unknown_field_is_rejected(
        self, model: type[BaseModel], valid_kwargs: dict
    ) -> None:
        # Sanity: the valid kwargs alone must construct fine...
        model(**valid_kwargs)
        # ...but one extra unexpected field must be refused.
        with pytest.raises(ValidationError):
            model(**valid_kwargs, unexpected_field="boom")


# --------------------------------------------------------------------------- #
# 5. The three tool model pairs expose a derivable JSON schema
# --------------------------------------------------------------------------- #
TOOL_PAIRS = [
    ("cost", CostQuery, CostReport),
    ("inventory", InventoryQuery, InventoryMatch),
    ("dispatch", DispatchRequest, DispatchBooking),
]
TOOL_MODELS = [m for _, q, r in TOOL_PAIRS for m in (q, r)]


class TestToolSchemas:
    @pytest.mark.parametrize(
        "model", TOOL_MODELS, ids=[m.__name__ for m in TOOL_MODELS]
    )
    def test_tool_model_yields_derivable_json_schema(
        self, model: type[BaseModel]
    ) -> None:
        # Act -- this is exactly what Tool.input_schema is built from.
        schema = model.model_json_schema()
        # Assert -- a well-formed, JSON-serializable object schema.
        assert isinstance(schema, dict)
        assert schema["type"] == "object"
        assert schema["title"] == model.__name__
        assert schema["properties"], "expected at least one property"
        json.dumps(schema)  # must be pure JSON (raises otherwise)

    @pytest.mark.parametrize("name, query, report", TOOL_PAIRS, ids=[p[0] for p in TOOL_PAIRS])
    def test_each_pair_query_and_report_are_both_derivable(
        self, name: str, query: type[BaseModel], report: type[BaseModel]
    ) -> None:
        # Both ends of a tool contract must produce a schema (input + output).
        assert query.model_json_schema()["properties"]
        assert report.model_json_schema()["properties"]

    def test_nested_model_is_included_in_schema_defs(self) -> None:
        # InventoryMatch nests InventoryLine -- a derivable schema must inline it.
        schema = InventoryMatch.model_json_schema()
        assert "InventoryLine" in schema.get("$defs", {})
        assert InventoryLine.model_json_schema()["title"] == "InventoryLine"
