"""INT.1 (#47) — the REAL phase-1 chain (Correlation -> Root-Cause) wired into
the orchestrator, replacing the dummies. Verifies an injected fault produces a
`diagnostic_ready` event carrying real causes + citations, with no dummy agent
in the phase-1 path.

Correlation runs its real offline (deterministic) localization; Root-Cause runs
its real confidence-gated retrieval loop against injected FAKE Vultr + retriever
(the prod path uses the shared VultrClient/VultronRetriever + a Vultr key). The
fakes stand in for the network only — the AGENTS in the path are the real ones.
"""
from contracts import RetrievedRef

from backend.app.correlation_adapter import CorrelationAgentAdapter
from backend.app.dummy_agents import DummyCorrelationAgent, DummyRootCauseAgent, default_registry
from backend.app.orchestrator import Orchestrator
from backend.app.push_service import PushService
from backend.app.root_cause_adapter import RootCauseAgentAdapter
from backend.app.settings import Settings

from backend.tests.conftest import assert_contract

FAULT_FAILURES = [{"code": "PWR-DC-UV", "severity": "critical",
                   "equipment": "EQ-PAR-014-RECT-1", "metric": "dc_plant_voltage_v",
                   "value": 44.0, "first_seen": "2026-07-05T09:00:00Z"}]
TRIGGER = {"rule": "PWR-DC-UV", "debounce_s": 60, "triggered_at": "2026-07-05T09:01:01Z"}


class FakeRetriever:
    """Stands in for VultronRetriever's network — returns a real corpus ref."""

    async def query(self, text, top_k=5):
        return [RetrievedRef(
            doc_id="eltek-flatpack2-om-manual", section="3.2 DC Undervoltage Alarm",
            snippet="Replace any rectifier module that stays in 'fail' after an input reset.",
            score=0.86,
        )]

    async def aclose(self):
        pass


class FakeVultr:
    """Stands in for the Vultr inference call — grounded, gate-clearing ranking."""

    async def structured_json(self, prompt, *, schema=None, max_tokens=512, temperature=0.0):
        return {
            "ranked_causes": [{
                "cause": "rectifier module failure",
                "confidence": 0.86,
                "citation_refs": [0],
                "expected_measurement": "dc_plant_voltage_v",
            }],
            "followup_query": "",
            "missing_doc": None,
        }

    async def aclose(self):
        pass


def _orch(bus, seeds, tools, tmp_path):
    registry = default_registry(*tools)
    # INT.1 swap: real correlation (offline) + real root_cause (fake network).
    registry["correlation"] = CorrelationAgentAdapter()
    registry["root_cause"] = RootCauseAgentAdapter(FakeVultr(), FakeRetriever())
    push = PushService(bus, Settings(push_out_dir=tmp_path / "push"))
    return Orchestrator(bus, seeds, registry, push, agent_timeout_s=5.0)


async def test_inject_fault_yields_diagnostic_ready_with_citations(bus, seeds, tools, tmp_path, event_validator):
    orch = _orch(bus, seeds, tools, tmp_path)
    await orch.handle_fault("SITE-PAR-014", "energy", FAULT_FAILURES, TRIGGER)
    await orch.join()

    dr = [e for e in bus.history if e["type"] == "diagnostic_ready"]
    assert dr, "no diagnostic_ready emitted"
    data = dr[0]["data"]

    # Correlation localized the real site/equipment.
    assert data["correlation"]["site_id"] == "SITE-PAR-014"
    assert data["correlation"]["equipment"]

    # Root-Cause produced a ranked cause WITH a resolving citation.
    assert data["causes"], "no causes in diagnostic_ready"
    top = data["causes"][0]
    assert top["cause"]
    assert top["citations"], "top cause carries no citation trail"
    assert top["citations"][0]["doc_id"] == "eltek-flatpack2-om-manual"

    # A verification request was derived for the human loop.
    assert data["verification_requests"]

    # Every emitted event satisfies the FROZEN event contract.
    assert_contract(bus.history, event_validator)


async def test_no_dummy_agent_in_phase1_path(bus, seeds, tools, tmp_path):
    orch = _orch(bus, seeds, tools, tmp_path)
    assert not isinstance(orch.agents["correlation"], DummyCorrelationAgent)
    assert not isinstance(orch.agents["root_cause"], DummyRootCauseAgent)
    assert type(orch.agents["correlation"]).__name__ == "CorrelationAgentAdapter"
    assert type(orch.agents["root_cause"]).__name__ == "RootCauseAgentAdapter"


async def test_retrieval_performed_event_emitted(bus, seeds, tools, tmp_path):
    orch = _orch(bus, seeds, tools, tmp_path)
    await orch.handle_fault("SITE-PAR-014", "energy", FAULT_FAILURES, TRIGGER)
    await orch.join()
    retr = [e for e in bus.history if e["type"] == "retrieval_performed"]
    assert retr, "root_cause retrieval not surfaced as an event"
    assert retr[0]["data"]["results"][0]["doc_id"] == "eltek-flatpack2-om-manual"


async def test_adapters_satisfy_frozen_protocol():
    from contracts import Agent
    assert isinstance(CorrelationAgentAdapter(), Agent)
    assert isinstance(RootCauseAgentAdapter(FakeVultr(), FakeRetriever()), Agent)
