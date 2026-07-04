"""Contract tests for the Validation agent (AGA.1 #28).

Acceptance criteria:
- Confirm fixture  => confirmed + rationale
- Pivot fixture    => contradicted + pivot request to the orchestrator
- Conforms to AgentOutput (and the frozen Agent protocol)
"""

import asyncio
import json
import pathlib

import pytest

from contracts.agent_interface import Agent, AgentInput, AgentOutput
from agents.validation import ValidationAgent, evaluate

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str) -> AgentInput:
    return AgentInput(**json.loads((FIXTURES / name).read_text(encoding="utf-8")))


def _run(inp: AgentInput) -> AgentOutput:
    return asyncio.run(ValidationAgent().run(inp))


# --------------------------------------------------------------------------- #
# Protocol / envelope conformance
# --------------------------------------------------------------------------- #
def test_satisfies_agent_protocol():
    assert isinstance(ValidationAgent(), Agent)


def test_output_conforms_to_agent_output():
    out = _run(_load("confirm_input.json"))
    assert isinstance(out, AgentOutput)
    assert out.agent == "validation"
    assert out.incident_id == "INC-DEMO-001"
    assert 0.0 <= out.confidence <= 1.0
    # JSON-serializable so it can transit the SSE stream.
    json.loads(out.model_dump_json())


# --------------------------------------------------------------------------- #
# Confirm run
# --------------------------------------------------------------------------- #
def test_confirm_fixture_confirms_with_rationale():
    out = _run(_load("confirm_input.json"))
    assert out.payload["decision"] == "confirmed"
    assert out.payload["matched_failure_id"] == "F2"
    assert out.payload["rationale"]  # non-empty rationale
    assert "CONFIRM" in out.summary
    assert "pivot_request" not in out.payload
    assert out.citations  # carries the envelope citation
    assert out.confidence >= 0.8


# --------------------------------------------------------------------------- #
# Pivot run
# --------------------------------------------------------------------------- #
def test_pivot_fixture_contradicts_and_requests_pivot():
    out = _run(_load("pivot_input.json"))
    assert out.payload["decision"] == "contradicted"
    assert "PIVOT" in out.summary
    pivot = out.payload["pivot_request"]
    assert pivot["incident_id"] == "INC-DEMO-002"
    assert pivot["reject_failure_id"] == "F2"
    assert pivot["ground_truth"]["value"] == -53.9
    assert "ground truth" in pivot["instruction"]


# --------------------------------------------------------------------------- #
# Pure decision logic (measurement is ground truth)
# --------------------------------------------------------------------------- #
def _cause():
    return {
        "failure_id": "F2",
        "label": "DC undervoltage",
        "signature": {"metric": "dc_voltage_v", "point": "busbar",
                      "abnormal_when": "gte", "threshold": -47.0},
    }


def test_measurement_overrides_verdict_conflict():
    # Technician says "real" but the busbar reads a healthy float -> measurement wins.
    ev = {
        "validations": [{"failure_id": "F2", "verdict": "real"}],
        "measurements": [{"metric": "dc_voltage_v", "point": "busbar", "value": -53.9, "unit": "V"}],
    }
    d = evaluate(_cause(), ev)
    assert d["decision"] == "contradicted"
    assert d["verdict_measurement_conflict"] is True
    assert d["confidence"] <= 0.72


def test_verdict_only_no_measurement_still_decides():
    ev = {"validations": [{"failure_id": "F2", "verdict": "real"}], "measurements": []}
    d = evaluate(_cause(), ev)
    assert d["decision"] == "confirmed"
    assert d["measurement_supports_fault"] is None


def test_missing_context_raises():
    bad = AgentInput(incident_id="X", site_id="S", failure_family="energy", context={})
    with pytest.raises(ValueError):
        asyncio.run(ValidationAgent().run(bad))
