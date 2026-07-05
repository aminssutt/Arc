"""P1 fix (task #53): the field measurement binds to the failure it physically
measures (busbar dc_voltage, not rectifier module_status), the pivot re-diagnosis
query is driven by the measurement (no longer byte-identical to the initial), and
after a pivot the suspect part follows the pivoted cause (no rectifier spare for a
sensing fault). All offline.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from contracts import AgentInput, RetrievedRef

from backend.app import orchestrator as st
from backend.app.dummy_agents import default_registry
from backend.app.orchestrator import Orchestrator
from backend.app.push_service import PushService
from backend.app.settings import Settings
from backend.app.validation_adapter import ValidationAgentAdapter
from backend.app.api.routes_validation import _expand_pitch

from backend.tests.conftest import assert_contract

# Two failures: F1 rectifier module_status (bool), F2 busbar dc_voltage (numeric V).
FAILURES = [
    {"code": "alarmMajorRectifier", "alarm_code": "PWR-RECT-FAIL", "severity": "major",
     "equipment": "rectifier-2", "metric": "module_status", "value": "fail",
     "first_seen": "2026-07-05T09:00:00Z"},
    {"code": "DC_UNDERVOLTAGE", "alarm_code": "PWR-DC-UV", "severity": "major",
     "equipment": "busbar", "metric": "dc_voltage_v", "value": -45.0,
     "first_seen": "2026-07-05T09:12:00Z"},
]
TRIGGER = {"rule": "undervoltage_major", "debounce_s": 120, "triggered_at": "2026-07-05T09:20:00Z"}


def _orch_real_validation(bus, seeds, tools, tmp_path):
    registry = default_registry(*tools)
    registry["validation"] = ValidationAgentAdapter(seeds)   # the real one
    push = PushService(bus, Settings(push_out_dir=tmp_path / "push"))
    return Orchestrator(bus, seeds, registry, push, agent_timeout_s=5.0)


async def test_measurement_binds_to_busbar_not_module_status(bus, seeds, tools, tmp_path, event_validator):
    orch = _orch_real_validation(bus, seeds, tools, tmp_path)
    await orch.handle_fault("PAR-021-NORD", "energy", FAILURES, TRIGGER)
    await orch.join()
    # The dummy Root-Cause points verification at F1 (module_status); the busbar
    # voltage reading must still bind to F2 and drive the pivot on physics.
    body = {
        "incident_id": orch.incident["id"], "client_event_id": "mb-1",
        "submitted_at": "2026-07-05T09:33:00Z",
        "validations": [{"failure_id": "F1", "verdict": "real"}, {"failure_id": "F2", "verdict": "real"}],
        "measurements": [{"metric": "dc_voltage_v", "point": "busbar", "value": -53.9, "unit": "V"}],
    }
    await orch.handle_validation(body)
    await orch.join()

    vr = [e for e in bus.history if e["type"] == "validation_result"][0]["data"]
    assert vr["result"] == "pivot"
    assert vr["contradictions"] == [{"failure_id": "F2", "telemetry": -45.0, "measured": -53.9, "unit": "V"}]
    assert "no field measurement" not in vr["rationale"]
    assert_contract(bus.history, event_validator)


async def test_pitch_rejected_binds_measurement_by_unit(bus, seeds, tools, tmp_path):
    orch = _orch_real_validation(bus, seeds, tools, tmp_path)
    await orch.handle_fault("PAR-021-NORD", "energy", FAILURES, TRIGGER)
    await orch.join()
    raw = {"incident_id": orch.incident["id"], "status": "rejected",
           "measurement": {"value": -53.9, "unit": "V"}}
    body, err = _expand_pitch(raw, orch)
    assert err is None
    false_ids = [v["failure_id"] for v in body["validations"] if v["verdict"] == "false"]
    assert false_ids == ["F2"]                                  # the voltage failure, not the module one
    meas = body["measurements"][0]
    assert meas["metric"] == "dc_voltage_v" and meas["point"] == "busbar" and meas["value"] == -53.9


async def test_root_cause_pivot_query_is_measurement_driven():
    class RecordingRetriever:
        def __init__(self): self.queries = []
        async def query(self, text, top_k=5):
            self.queries.append(text)
            return [RetrievedRef(doc_id="V4", section="alarm", snippet="rectifier lost", score=None)]

    class FakeVultr:
        last_user = ""
        async def structured_json(self, prompt, *, max_tokens=600, temperature=0.0):
            FakeVultr.last_user = prompt[-1]["content"] if isinstance(prompt, list) else str(prompt)
            return {"ranked_causes": [{"cause": "rectifier module failure", "confidence": 0.85,
                                       "citation_refs": [0], "expected_measurement": "dc_voltage_v"}],
                    "followup_query": "", "missing_doc": None}

    from agents.root_cause.agent import RootCauseAgent
    ret, vultr = RecordingRetriever(), FakeVultr()
    agent = RootCauseAgent(vultr, ret)
    failures = [{"id": "F1", "code": "PWR-DC-UV", "equipment": "busbar",
                 "metric": "dc_voltage_v", "value": -45.0, "severity": "major"}]

    await agent.run(AgentInput(incident_id="INC-1", site_id="PAR-021-NORD", failure_family="energy",
                               context={"failures": failures, "phase_cause": "initial", "measurements": []}))
    initial_query, initial_prompt = ret.queries[0], FakeVultr.last_user
    ret.queries.clear()
    await agent.run(AgentInput(incident_id="INC-1", site_id="PAR-021-NORD", failure_family="energy",
                               context={"failures": failures, "phase_cause": "pivot",
                                        "measurements": [{"metric": "dc_voltage_v", "point": "busbar",
                                                          "value": -53.9, "unit": "V"}]}))
    pivot_query, pivot_prompt = ret.queries[0], FakeVultr.last_user

    assert initial_query != pivot_query                        # not byte-identical anymore
    assert "-53.9" in pivot_query
    assert "FIELD MEASUREMENT" in pivot_prompt and "-53.9" in pivot_prompt
    assert "FIELD MEASUREMENT" not in initial_prompt           # initial stays a physical-cause read


async def test_suspect_part_follows_pivoted_cause(orchestrator):
    fault = [{"code": "PWR-DC-UV", "severity": "critical", "equipment": "rectifier",
              "metric": "dc_voltage_v", "value": 44.0, "first_seen": "2026-07-05T09:00:00Z"}]
    await orchestrator.handle_fault("PAR-021-NORD", "energy", fault, TRIGGER)
    await orchestrator.join()

    # Confirm path (no pivot): the topology part resolves as today.
    assert orchestrator._suspect_part() == "APR48-3G"

    # After a pivot to a sensing-card cause, the rectifier spare must NOT lead.
    orchestrator.incident["validation_result"] = "pivot"
    orchestrator.incident["diagnostic"]["causes"][0]["cause"] = \
        "supervision/sensing card fault (false undervoltage reading)"
    assert orchestrator._suspect_part() is None                # clean stock-out (no seeded sensing part)


# --- Acceptance (addendum #53 P0): frozen and pitch shapes must AGREE -----------
def _frozen_body(orch, verdicts: dict, measurement=None):
    body = {
        "incident_id": orch.incident["id"],
        "client_event_id": "acc-" + "-".join(f"{k}{v[0]}" for k, v in verdicts.items()),
        "submitted_at": "2026-07-05T09:33:00Z", "technician": {"id": "tech-07"},
        "validations": [{"failure_id": fid, "verdict": v} for fid, v in verdicts.items()],
    }
    if measurement:
        body["measurements"] = [measurement]
    return body


async def _result(bus):
    return [e for e in bus.history if e["type"] == "validation_result"][0]["data"]["result"]


async def _to_awaiting_with_live_vreq(bus, seeds, tools, tmp_path):
    """Multi-failure incident whose verification_request points at F1 (the LIVE
    root_cause shape that triggered the P0), so the tests exercise the real bug."""
    orch = _orch_real_validation(bus, seeds, tools, tmp_path)
    await orch.handle_fault("PAR-021-NORD", "energy", FAILURES, TRIGGER)
    await orch.join()
    orch.incident["diagnostic"]["verification_requests"] = [
        {"failure_id": "F1", "action": "verify", "metric": "dc_plant_voltage_v", "point": "EQ-PAR-021N-RECT-2"}]
    return orch


async def test_acceptance_frozen_rejected_pivots(bus, seeds, tools, tmp_path, event_validator):
    orch = await _to_awaiting_with_live_vreq(bus, seeds, tools, tmp_path)
    await orch.handle_validation(_frozen_body(
        orch, {"F1": "real", "F2": "false"},
        {"metric": "dc_voltage_v", "point": "busbar", "value": -53.9, "unit": "V"}))
    await orch.join()
    assert await _result(bus) == "pivot"                       # frozen F2=false + -53.9 -> pivot
    assert_contract(bus.history, event_validator)


async def test_acceptance_pitch_rejected_pivots_same_as_frozen(bus, seeds, tools, tmp_path, event_validator):
    orch = await _to_awaiting_with_live_vreq(bus, seeds, tools, tmp_path)
    body, err = _expand_pitch({"incident_id": orch.incident["id"], "status": "rejected",
                               "measurement": {"value": -53.9, "unit": "V"}}, orch)
    assert err is None
    await orch.handle_validation(body)
    await orch.join()
    assert await _result(bus) == "pivot"                       # identical behaviour to frozen
    assert_contract(bus.history, event_validator)


async def test_acceptance_frozen_all_real_confirms(bus, seeds, tools, tmp_path, event_validator):
    orch = await _to_awaiting_with_live_vreq(bus, seeds, tools, tmp_path)
    await orch.handle_validation(_frozen_body(
        orch, {"F1": "real", "F2": "real"},
        {"metric": "dc_voltage_v", "point": "busbar", "value": -44.0, "unit": "V"}))  # undervoltage present
    await orch.join()
    assert await _result(bus) == "confirmed"
    assert_contract(bus.history, event_validator)


async def test_acceptance_pitch_confirmed_confirms(bus, seeds, tools, tmp_path, event_validator):
    orch = await _to_awaiting_with_live_vreq(bus, seeds, tools, tmp_path)
    body, err = _expand_pitch({"incident_id": orch.incident["id"], "status": "confirmed"}, orch)
    assert err is None
    await orch.handle_validation(body)
    await orch.join()
    assert await _result(bus) == "confirmed"
    assert_contract(bus.history, event_validator)


async def test_acceptance_frozen_pivots_even_if_measurement_metric_drifts(bus, seeds, tools, tmp_path, event_validator):
    # Defence-in-depth: even if the measurement metric does NOT match any failure
    # (the canonical-vs-seed drift QA saw), a verdict=false on F2 still pivots.
    orch = await _to_awaiting_with_live_vreq(bus, seeds, tools, tmp_path)
    await orch.handle_validation(_frozen_body(
        orch, {"F1": "real", "F2": "false"},
        {"metric": "dc_plant_voltage_v", "point": "busbar", "value": -53.9, "unit": "V"}))  # drifted metric
    await orch.join()
    assert await _result(bus) == "pivot"
    assert_contract(bus.history, event_validator)


# --- #54: deterministic physical interpretation of the field measurement --------
def _bare_orch(seeds):
    from backend.app.bus import EventBus
    from backend.app.orchestrator import Orchestrator
    return Orchestrator(EventBus(), seeds, {}, None)


def test_interpret_measurement_healthy_vs_unhealthy(seeds):
    orch = _bare_orch(seeds)
    failures = [{"id": "F2", "metric": "dc_voltage_v", "value": -44.8}]
    healthy = orch._interpret_measurements(
        [{"metric": "dc_voltage_v", "point": "busbar", "value": -53.9, "unit": "V"}], failures)[0]
    assert healthy["status"] == "healthy"                      # magnitude 53.9 >= 45 => above threshold
    assert healthy["magnitude"] == 53.9 and healthy["threshold"] == 45.0
    assert healthy["telemetry_magnitude"] == 44.8
    unhealthy = orch._interpret_measurements(
        [{"metric": "dc_voltage_v", "point": "busbar", "value": -44.8, "unit": "V"}], failures)[0]
    assert unhealthy["status"] == "unhealthy"                  # magnitude 44.8 < 45 => real undervoltage


def test_interpret_measurement_missing_threshold_no_crash(seeds):
    orch = _bare_orch(seeds)
    assert orch._interpret_measurements(
        [{"metric": "no_such_signal", "value": -5.0, "unit": "X"}], [])[0]["status"] == "unknown"
    assert orch._interpret_measurements([{"metric": "module_status", "value": False}], []) == []
    assert orch._interpret_measurements([], []) == []
    assert orch._interpret_measurements(None, []) == []


async def test_pivot_prompt_carries_computed_interpretation_block(seeds):
    from agents.root_cause.agent import RootCauseAgent
    orch = _bare_orch(seeds)
    failures = [{"id": "F2", "metric": "dc_voltage_v", "value": -44.8}]
    interp = orch._interpret_measurements(
        [{"metric": "dc_voltage_v", "point": "busbar", "value": -53.9, "unit": "V"}], failures)

    captured = {}

    class _FakeVultr:
        async def structured_json(self, prompt, *, max_tokens=600, temperature=0.0):
            captured["prompt"] = prompt[-1]["content"]
            return {"ranked_causes": [{"cause": "x", "confidence": 0.85, "citation_refs": [0],
                                       "expected_measurement": "dc_voltage_v"}],
                    "followup_query": "", "missing_doc": None}

    class _Ret:
        async def query(self, text, top_k=5):
            return [RetrievedRef(doc_id="V4", section="a", snippet="x", score=None)]

    await RootCauseAgent(_FakeVultr(), _Ret()).run(AgentInput(
        incident_id="I", site_id="PAR-021-NORD", failure_family="energy",
        context={"failures": failures, "phase_cause": "pivot",
                 "measurements": [{"metric": "dc_voltage_v", "point": "busbar", "value": -53.9, "unit": "V"}],
                 "measurement_interpretation": interp}))
    prompt = captured["prompt"]
    assert "FIELD MEASUREMENT INTERPRETATION" in prompt
    assert "HEALTHY" in prompt and "53.9" in prompt and "magnitude" in prompt
    assert "CONTRADICTED" in prompt                            # telemetry contradicted by the field
    assert "independent ground truth" not in prompt           # raw signed line replaced


# --- #56: part-card + pivot cost + verification-request target -------------------
@pytest.fixture()
async def app_client():
    from backend.app.main import create_app
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.app = app
            yield c


async def _run_pivot_report(app_client):
    await app_client.post("/api/demo/inject-fault", json={"scenario": "pivot"})
    orch = app_client.app.state.orchestrator
    await orch.join()
    await app_client.post("/api/validation", json={
        "incident_id": orch.incident["id"], "status": "rejected",
        "measurement": {"value": -53.9, "unit": "V"}})
    await orch.join()
    return [e for e in app_client.app.state.bus.history if e["type"] == "action_report_ready"][-1]["data"]["report"]


async def test_pivot_report_part_is_sp2mu_deterministic(app_client):
    for _ in range(3):                                         # deterministic on every run
        await app_client.post("/api/demo/reset")
        report = await _run_pivot_report(app_client)
        assert report["inventory"]["part_no"] == "SP2-MU"      # never the rectifier spare
        assert report["inventory"]["in_stock"] is False        # clean stock-out (not seeded)


async def test_pivot_cost_avoided_is_defensible(app_client):
    report = await _run_pivot_report(app_client)
    assert report["cost"]["avoided"] != 6800.0                 # not the outage figure
    assert report["cost"]["avoided"] == 1165.50                # part 769.04 + 2h labor 71.46 + truck 325
    assert "spurious alarm" in report["cost"]["notes"]


async def test_verification_request_targets_measurable_metric_not_boolean():
    # module_status is stored numerically (0/1) but is NOT a field measurement:
    # the verification must target the busbar dc_voltage failure. Guards the LIVE
    # divergence QA saw (vreqs[0] -> F1/module_status).
    from backend.app.root_cause_adapter import RootCauseAgentAdapter

    class _FV:
        async def structured_json(self, prompt, *, max_tokens=600, temperature=0.0):
            return {"ranked_causes": [{"cause": "rectifier module failure", "confidence": 0.85,
                                       "citation_refs": [0], "expected_measurement": "dc_plant_voltage_v"}],
                    "followup_query": "", "missing_doc": None}

    class _R:
        async def query(self, text, top_k=5):
            return [RetrievedRef(doc_id="V4", section="a", snippet="x", score=None)]

    failures = [{"id": "F1", "code": "alarmMajorRectifier", "metric": "module_status", "value": 0,
                 "equipment": "EQ-PAR-021N-RECT-2", "severity": "major"},
                {"id": "F2", "code": "DC_UNDERVOLTAGE", "metric": "dc_voltage_v", "value": -45.0,
                 "equipment": "busbar", "severity": "major"}]
    out = await RootCauseAgentAdapter(_FV(), _R()).run(AgentInput(
        incident_id="I", site_id="PAR-021-NORD", failure_family="energy", context={"failures": failures}))
    vreq = out.payload["diagnostic"]["verification_requests"][0]
    assert vreq["failure_id"] == "F2"                          # the measurable dc_voltage failure
    assert vreq["metric"] == "dc_voltage_v" and vreq["point"] == "busbar"
