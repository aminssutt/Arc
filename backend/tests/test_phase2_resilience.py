"""Issue #97 (stage-C P0): phase-2 resilience — the demo must ALWAYS terminate.

Locks the three fixes:
1. RemediationAgentAdapter degrades (not crashes) on RemediationError, VultrError
   and asyncio.TimeoutError, and never emits empty procedure steps.
2. A phase-2 agent that fails/returns nothing still closes the incident with a
   DEGRADED action report + incident_resolved (no stuck phase2_running).
3. The emitted remediation_ready never carries procedure.steps=[] (frozen
   events.schema minItems>=1), and every degraded run stays schema-valid.
"""
import asyncio

import pytest

from contracts import AgentInput, AgentOutput

from agents.common.vultr import VultrError
from agents.remediation import RemediationError
from backend.app import orchestrator as st
from backend.app.remediation_adapter import RemediationAgentAdapter
from backend.tests.conftest import assert_contract

FAULT_FAILURES = [{"code": "PWR-DC-UV", "severity": "critical",
                   "equipment": "EQ-PAR-014-RECT-1", "metric": "dc_plant_voltage_v",
                   "value": 44.0, "first_seen": "2026-07-05T09:00:00Z"}]
TRIGGER = {"rule": "PWR-DC-UV", "debounce_s": 60, "triggered_at": "2026-07-05T09:01:01Z"}


def _validation_body(orch, verdicts):
    return {
        "incident_id": orch.incident["id"],
        "client_event_id": "t-1",
        "submitted_at": "2026-07-05T09:33:00Z",
        "technician": {"id": "tech-07"},
        "validations": [{"failure_id": f["id"], "verdict": v}
                        for f, v in zip(orch.incident["failures"], verdicts)],
        "measurements": [{"metric": "dc_plant_voltage_v", "point": "busbar", "value": 43.9, "unit": "V"}],
    }


class _RaisingInner:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def run(self, data: AgentInput) -> AgentOutput:
        raise self._exc


class _FailingAgent:
    """Phase-2 agent whose run raises -> orchestrator sees None (error event)."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def run(self, data: AgentInput) -> AgentOutput:
        raise RuntimeError(f"{self.name} boom")


class _EmptyStepsRemediation:
    name = "remediation"

    async def run(self, data: AgentInput) -> AgentOutput:
        return AgentOutput(
            incident_id=data.incident_id, agent=self.name,
            summary="procedure with no steps (should be guarded)",
            payload={"procedure": {"title": "t", "steps": [], "safety": []},
                     "parts": [], "action_hints": []},
            retrieved_refs=[], citations=[], confidence=0.5,
        )


# -- Fix 1: adapter degrades on the broadened exception set --------------------
@pytest.mark.parametrize("exc", [
    RemediationError("corpus lacks a safe cited procedure"),
    VultrError("LLM token overflow"),
    asyncio.TimeoutError(),
])
async def test_adapter_degrades_instead_of_raising(exc):
    adapter = RemediationAgentAdapter(vultr=None, retriever=None)
    adapter._inner = _RaisingInner(exc)  # bypass the real inner agent

    out = await adapter.run(AgentInput(
        incident_id="INC-LIVE-001", site_id="SITE-PAR-014", failure_family="energy",
        context={"diagnostic": {"causes": [{"cause": "rectifier failure"}]}}))

    assert out is not None
    steps = out.payload["procedure"]["steps"]
    assert len(steps) >= 1                                   # NEVER empty (Fix 3)
    assert all(s["text"] and "citations" in s for s in steps)
    assert out.confidence <= 0.5                             # flagged as degraded


# -- Fix 2: phase-2 remediation failure still terminates the incident ----------
async def test_phase2_remediation_failure_degrades_and_resolves(orchestrator, bus, event_validator):
    await orchestrator.handle_fault("SITE-PAR-014", "energy", FAULT_FAILURES, TRIGGER)
    await orchestrator.join()
    assert orchestrator.state == st.AWAITING

    orchestrator.agents["remediation"] = _FailingAgent("remediation")
    await orchestrator.handle_validation(_validation_body(orchestrator, ["real"]))
    await orchestrator.join()

    assert orchestrator.state == st.IDLE                     # NOT stuck in phase2_running
    types = [e["type"] for e in bus.history]
    assert "action_report_ready" in types                   # degraded report emitted
    assert "incident_resolved" in types                     # demo terminated
    resolved = [e for e in bus.history if e["type"] == "incident_resolved"][-1]["data"]
    assert resolved["outcome"] == "downgraded"
    assert "DEGRADED" in resolved["summary"]
    err = [e for e in bus.history if e["type"] == "agent_completed"
           and e["data"]["status"] == "error"]
    assert err and err[0]["data"]["agent"] == "remediation"
    report = [e for e in bus.history if e["type"] == "action_report_ready"][-1]["data"]["report"]
    assert len(report["diagnosis"]["citations"]) >= 1       # minItems>=1 honoured
    assert report["honesty_notes"]
    assert_contract(bus.history, event_validator)            # every event schema-valid


# -- Fix 2: phase-2 cost/inventory/dispatch failure also terminates ------------
async def test_phase2_cid_failure_degrades_and_resolves(orchestrator, bus, event_validator):
    await orchestrator.handle_fault("SITE-PAR-014", "energy", FAULT_FAILURES, TRIGGER)
    await orchestrator.join()

    orchestrator.agents["cost_inventory_dispatch"] = _FailingAgent("cost_inventory_dispatch")
    await orchestrator.handle_validation(_validation_body(orchestrator, ["real"]))
    await orchestrator.join()

    assert orchestrator.state == st.IDLE
    types = [e["type"] for e in bus.history]
    assert "remediation_ready" in types                     # remediation succeeded first
    resolved = [e for e in bus.history if e["type"] == "incident_resolved"][-1]["data"]
    assert resolved["outcome"] == "downgraded"
    assert_contract(bus.history, event_validator)


# -- Fix 3: an agent returning empty steps is guarded before emission ----------
async def test_empty_steps_remediation_is_guarded(orchestrator, bus, event_validator):
    await orchestrator.handle_fault("SITE-PAR-014", "energy", FAULT_FAILURES, TRIGGER)
    await orchestrator.join()

    orchestrator.agents["remediation"] = _EmptyStepsRemediation()
    await orchestrator.handle_validation(_validation_body(orchestrator, ["real"]))
    await orchestrator.join()

    assert orchestrator.state == st.IDLE
    rr = [e for e in bus.history if e["type"] == "remediation_ready"][-1]["data"]
    assert len(rr["procedure"]["steps"]) >= 1               # guarded, not empty
    assert_contract(bus.history, event_validator)
