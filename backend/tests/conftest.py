import json
import os

# Tests NEVER call the network or spend shared credits: blank the Vultr keys
# BEFORE any backend import (settings' .env loader respects existing env), so
# _wire_real_agents takes the offline/dummy path even on a keyed machine.
os.environ["VULTR_INFERENCE_API_KEY"] = ""
os.environ["VULTR_API_KEY"] = ""

import pytest
from jsonschema import Draft202012Validator

from backend.app.bus import EventBus
from backend.app.dummy_agents import default_registry
from backend.app.orchestrator import Orchestrator
from backend.app.push_service import PushService
from backend.app.seeds import load_seeds
from backend.app.settings import REPO_ROOT, Settings
from backend.app.tools import CostEngineTool, CrewDispatchTool, InventoryLookupTool
from backend.app.watchdog import Watchdog


@pytest.fixture()
def seeds():
    s = Settings()
    return load_seeds(s.data_dir, s.seed_fallback_dir)


@pytest.fixture()
def bus():
    return EventBus()


@pytest.fixture()
def tools(seeds):
    return (CostEngineTool(seeds), InventoryLookupTool(seeds), CrewDispatchTool(seeds))


@pytest.fixture()
def orchestrator(bus, seeds, tools, tmp_path):
    settings = Settings(push_out_dir=tmp_path / "push_out")
    push = PushService(bus, settings)
    return Orchestrator(bus, seeds, default_registry(*tools), push, agent_timeout_s=5.0)


@pytest.fixture()
def watchdog(seeds, orchestrator):
    wd = Watchdog(seeds, orchestrator.handle_fault, orchestrator.add_failures)
    orchestrator.on_incident_closed = wd.incident_closed
    return wd


@pytest.fixture(scope="session")
def event_validator():
    schema = json.loads((REPO_ROOT / "contracts" / "events.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def assert_contract(envelopes, validator):
    """Every emitted envelope must satisfy the FROZEN event contract."""
    for e in envelopes:
        errors = [err.message for err in validator.iter_errors(e)]
        assert not errors, f"{e['type']} (seq {e['seq']}) violates contract: {errors}"


VALIDATION_BODY_ALL_REAL = {
    "incident_id": "PLACEHOLDER",
    "client_event_id": "test-001",
    "submitted_at": "2026-07-05T09:33:00Z",
    "technician": {"id": "tech-07"},
    "validations": [],  # filled per-test from the push payload failure ids
    "measurements": [{"metric": "dc_plant_voltage_v", "point": "busbar", "value": 43.9, "unit": "V"}],
}
