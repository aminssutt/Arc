"""Tests for the orchestration glue (AGA.4 #31).

Acceptance criteria:
- Phase-1 chain (correlation -> root-cause) runs end-to-end offline via harness.
- Per-agent prompt/persona files exist for every agent in the plan (vgtray review).
"""

import asyncio
import json

import pytest

from contracts.agent_interface import Agent, AgentInput, AgentOutput
from agents.orchestration import (
    ALL_AGENTS,
    AgentRegistry,
    Phase,
    available_personas,
    load_persona,
    run_phase,
    run_plan,
)
from agents.validation import ValidationAgent


# --------------------------------------------------------------------------- #
# Stub agent (placeholder for the real correlation/root_cause, vgtray's lane)
# --------------------------------------------------------------------------- #
class StubAgent:
    def __init__(self, name, payload=None, confidence=0.8):
        self.name = name
        self._payload = payload or {}
        self._confidence = confidence

    async def run(self, data: AgentInput) -> AgentOutput:
        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=f"[stub] {self.name}",
            payload={**self._payload, "saw_findings": sorted(data.context.get("findings", {}))},
            retrieved_refs=[],
            citations=[],
            confidence=self._confidence,
        )


def _seed(incident="INC-DEMO-001"):
    return AgentInput(incident_id=incident, site_id="PAR-021-NORD", failure_family="energy")


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
def test_registry_registers_and_gets():
    reg = AgentRegistry()
    reg.register(StubAgent("correlation"))
    assert "correlation" in reg
    assert isinstance(reg.get("correlation"), Agent)


def test_registry_rejects_non_agent():
    reg = AgentRegistry()
    with pytest.raises(TypeError):
        reg.register(object())


def test_registry_rejects_duplicate():
    reg = AgentRegistry()
    reg.register(StubAgent("root_cause"))
    with pytest.raises(ValueError):
        reg.register(StubAgent("root_cause"))


def test_registry_get_missing_raises():
    with pytest.raises(KeyError):
        AgentRegistry().get("nope")


# --------------------------------------------------------------------------- #
# Phase-1 chain end-to-end offline (the headline acceptance criterion)
# --------------------------------------------------------------------------- #
def test_phase1_chain_runs_end_to_end_offline():
    reg = AgentRegistry()
    reg.register(StubAgent("correlation", {"site": "PAR-021-NORD", "equipment": ["rectifier-2"]}))
    reg.register(StubAgent("root_cause", {"top_cause": "rectifier module failure"}, 0.82))

    result = asyncio.run(run_phase(reg, Phase.PHASE1, _seed()))

    # Both agents ran, in order.
    assert [o.agent for o in result.outputs] == ["correlation", "root_cause"]
    # Findings accumulated for both.
    assert set(result.findings) == {"correlation", "root_cause"}
    # Context threaded forward: root_cause saw correlation's finding.
    assert result.findings["root_cause"]["saw_findings"] == ["correlation"]


def test_run_plan_threads_findings_across_phases():
    reg = AgentRegistry()
    reg.register(StubAgent("correlation"))
    reg.register(StubAgent("root_cause"))
    reg.register(StubAgent("remediation"))
    reg.register(StubAgent("cost_inventory_dispatch"))

    result = asyncio.run(run_plan(reg, [Phase.PHASE1, Phase.PHASE2], _seed()))
    assert [o.agent for o in result.outputs] == [
        "correlation", "root_cause", "remediation", "cost_inventory_dispatch",
    ]
    # Phase-2's first agent saw all of phase-1's findings.
    assert set(result.findings["remediation"]["saw_findings"]) == {"correlation", "root_cause"}


def test_harness_runs_the_real_validation_agent():
    # The human-loop step wires the shipped ValidationAgent unchanged.
    reg = AgentRegistry()
    reg.register(ValidationAgent())
    seed = AgentInput(
        incident_id="INC-DEMO-002",
        site_id="PAR-021-NORD",
        failure_family="energy",
        context={
            "top_cause": {
                "failure_id": "F2",
                "label": "DC undervoltage",
                "signature": {"metric": "dc_voltage_v", "point": "busbar",
                              "abnormal_when": "gte", "threshold": -47.0},
            },
            "validation_event": {
                "validations": [{"failure_id": "F2", "verdict": "false"}],
                "measurements": [{"metric": "dc_voltage_v", "point": "busbar",
                                  "value": -53.9, "unit": "V"}],
            },
        },
    )
    result = asyncio.run(run_phase(reg, Phase.HUMAN_LOOP, seed))
    assert result.findings["validation"]["decision"] == "contradicted"


# --------------------------------------------------------------------------- #
# Personas
# --------------------------------------------------------------------------- #
def test_every_planned_agent_has_a_persona():
    have = set(available_personas())
    for name in ALL_AGENTS:
        assert name in have, f"missing persona file for {name!r}"


def test_persona_loads_nonempty():
    for name in ALL_AGENTS:
        assert load_persona(name).strip(), f"empty persona for {name!r}"


def test_persona_missing_raises():
    with pytest.raises(FileNotFoundError):
        load_persona("does_not_exist")


# --------------------------------------------------------------------------- #
# Output stays contract-serializable
# --------------------------------------------------------------------------- #
def test_chain_outputs_json_serializable():
    reg = AgentRegistry()
    reg.register(StubAgent("correlation"))
    reg.register(StubAgent("root_cause"))
    result = asyncio.run(run_phase(reg, Phase.PHASE1, _seed()))
    for out in result.outputs:
        json.loads(out.model_dump_json())
