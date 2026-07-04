"""Root-Cause's mandatory missing-doc path reaches the stream as the
doc_requested event (frozen contract type 13) — previously dropped silently.
"""
from contracts import AgentInput, AgentOutput

from backend.app.dummy_agents import DummyRootCauseAgent
from backend.tests.conftest import assert_contract

FAULT_FAILURES = [{"code": "PWR-DC-UV", "severity": "critical",
                   "equipment": "EQ-PAR-014-RECT-1", "metric": "dc_plant_voltage_v",
                   "value": 44.0, "first_seen": "2026-07-05T09:00:00Z"}]
TRIGGER = {"rule": "PWR-DC-UV", "debounce_s": 60, "triggered_at": "2026-07-05T09:01:01Z"}

DOC_REQUEST = {"agent": "root_cause",
               "description": "vendor derating spec missing from corpus",
               "query": "radio derating threshold", "status": "missing"}


class DocRequestingRootCause(DummyRootCauseAgent):
    """Nests doc_request inside diagnostic — the real adapter's shape (#89)."""

    async def run(self, data: AgentInput) -> AgentOutput:
        out = await super().run(data)
        out.payload["diagnostic"]["doc_request"] = dict(DOC_REQUEST)
        return out


async def test_doc_request_becomes_event(orchestrator, bus, event_validator):
    orchestrator.agents["root_cause"] = DocRequestingRootCause()
    await orchestrator.handle_fault("SITE-PAR-014", "energy", FAULT_FAILURES, TRIGGER)
    await orchestrator.join()

    types = [e["type"] for e in bus.history]
    assert "doc_requested" in types
    dr = [e for e in bus.history if e["type"] == "doc_requested"][0]["data"]
    assert dr == DOC_REQUEST
    # emitted BEFORE the diagnostic it qualifies, and stripped from its data
    assert types.index("doc_requested") < types.index("diagnostic_ready")
    diag = [e for e in bus.history if e["type"] == "diagnostic_ready"][0]["data"]
    assert "doc_request" not in diag
    assert_contract(bus.history, event_validator)
