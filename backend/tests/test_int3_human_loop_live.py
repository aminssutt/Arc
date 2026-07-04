"""INT.3 (#49) — the human loop + phase-2 chain live, end to end, with EVERY
agent real (correlation offline, root_cause + remediation on injected fakes for
the Vultr network only, validation + CID fully real over the seeds).

- Confirm run: inject-fault -> field CONFIRMS -> completes through
  action_report_ready, and the report carries a citation trail.
- Pivot run: field CONTRADICTS -> phase 1 visibly re-runs (phase_started cause=pivot).

The backend human loop is driven directly via handle_validation (the iOS
push/round-trip is INT.2 #48); this proves the orchestration + citation trail.
"""
from contracts import RetrievedRef

from backend.app import orchestrator as st
from backend.app.correlation_adapter import CorrelationAgentAdapter
from backend.app.dummy_agents import default_registry
from backend.app.orchestrator import Orchestrator
from backend.app.push_service import PushService
from backend.app.remediation_adapter import RemediationAgentAdapter
from backend.app.root_cause_adapter import RootCauseAgentAdapter
from backend.app.settings import Settings
from backend.app.validation_adapter import ValidationAgentAdapter

from backend.tests.conftest import assert_contract

FAULT_FAILURES = [{"code": "PWR-DC-UV", "severity": "critical",
                   "equipment": "EQ-PAR-014-RECT-1", "metric": "dc_plant_voltage_v",
                   "value": 44.0, "first_seen": "2026-07-05T09:00:00Z"}]
TRIGGER = {"rule": "PWR-DC-UV", "debounce_s": 60, "triggered_at": "2026-07-05T09:01:01Z"}

RECT_REF = RetrievedRef(doc_id="eltek-flatpack2-om-manual", section="3.2 DC Undervoltage Alarm",
                        snippet="Replace any rectifier module that stays in 'fail'.", score=0.86)
SAFETY_REF = RetrievedRef(doc_id="site-safety-dc-power-plant", section="2 Lockout/Tagout and PPE",
                          snippet="Open and lock the battery disconnect; verify zero energy.", score=0.8)


class FakeRootCauseVultr:
    async def structured_json(self, prompt, *, schema=None, max_tokens=512, temperature=0.0):
        return {"ranked_causes": [{"cause": "rectifier module failure", "confidence": 0.86,
                                   "citation_refs": [0], "expected_measurement": "dc_plant_voltage_v"}],
                "followup_query": "", "missing_doc": None}
    async def aclose(self): pass


class RCRetriever:
    async def query(self, text, top_k=5): return [RECT_REF]
    async def aclose(self): pass


class FakeRemediationVultr:
    async def structured_json(self, prompt, *, schema=None, max_tokens=512, temperature=0.0):
        return {
            "procedure": ["Read the plant controller; confirm which modules report 'fail'.",
                          "Replace the rectifier module that stays in 'fail' after reset."],
            "safety_steps": [
                {"step": "Apply lockout/tagout on the battery disconnect.",
                 "doc_id": "site-safety-dc-power-plant", "section": "2"},
                {"step": "Verify zero energy with a meter before touching the busbar.",
                 "doc_id": "site-safety-dc-power-plant", "section": "2"}],
            "parts_needed": ["PN-RECT-48-2000"],
            "crew_skill": "power",
        }
    async def aclose(self): pass


class RemRetriever:
    async def query(self, text, top_k=5):
        return [SAFETY_REF] if "safety" in text.lower() else [RECT_REF]
    async def aclose(self): pass


def _orch(bus, seeds, tools, tmp_path):
    registry = default_registry(*tools)                                    # CID + tools already real
    registry["correlation"] = CorrelationAgentAdapter()                    # real, offline
    registry["root_cause"] = RootCauseAgentAdapter(FakeRootCauseVultr(), RCRetriever())
    registry["validation"] = ValidationAgentAdapter(seeds)                 # real
    registry["remediation"] = RemediationAgentAdapter(FakeRemediationVultr(), RemRetriever())
    push = PushService(bus, Settings(push_out_dir=tmp_path / "push"))
    return Orchestrator(bus, seeds, registry, push, agent_timeout_s=5.0)


def _validation_body(orch, value):
    return {
        "incident_id": orch.incident["id"], "client_event_id": "int3-1",
        "submitted_at": "2026-07-05T09:33:00Z",
        "validations": [{"failure_id": f["id"], "verdict": "real"} for f in orch.incident["failures"]],
        "measurements": [{"metric": "dc_plant_voltage_v", "point": "busbar", "value": value, "unit": "V"}],
    }


async def test_confirm_run_completes_through_action_report_with_citations(
        bus, seeds, tools, tmp_path, event_validator):
    orch = _orch(bus, seeds, tools, tmp_path)
    await orch.handle_fault("SITE-PAR-014", "energy", FAULT_FAILURES, TRIGGER)
    await orch.join()

    await orch.handle_validation(_validation_body(orch, value=43.9))       # < 45 => confirmed
    await orch.join()

    reports = [e for e in bus.history if e["type"] == "action_report_ready"]
    assert reports, "confirm run did not reach action_report_ready"
    report = reports[0]["data"]["report"]

    # full citation trail (root-cause + remediation safety) resolves
    assert report["citations"], "action report carries no citation trail"
    doc_ids = {c["doc_id"] for c in report["citations"]}
    assert "site-safety-dc-power-plant" in doc_ids          # remediation safety cite
    # part matched to a real seeded stock line by the real CID agent
    assert report["inventory"]["part_no"] == "PN-RECT-48-2000"
    assert orch.state == st.IDLE
    assert_contract(bus.history, event_validator)


async def test_pivot_run_visibly_reruns_phase1(bus, seeds, tools, tmp_path, event_validator):
    orch = _orch(bus, seeds, tools, tmp_path)
    await orch.handle_fault("SITE-PAR-014", "energy", FAULT_FAILURES, TRIGGER)
    await orch.join()

    await orch.handle_validation(_validation_body(orch, value=53.9))       # normal => contradicted
    await orch.join()

    pivots = [e for e in bus.history if e["type"] == "phase_started" and e["data"]["cause"] == "pivot"]
    assert len(pivots) == 1, "pivot did not visibly re-run phase 1"
    vr = [e for e in bus.history if e["type"] == "validation_result"][0]
    assert vr["data"]["result"] == "pivot"
    # pivot still lands an action report (downgraded outcome)
    assert [e for e in bus.history if e["type"] == "action_report_ready"]
    assert_contract(bus.history, event_validator)


async def test_remediation_adapter_satisfies_protocol():
    from contracts import Agent
    assert isinstance(RemediationAgentAdapter(FakeRemediationVultr(), RemRetriever()), Agent)
