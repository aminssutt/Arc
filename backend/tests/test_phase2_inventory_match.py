"""P1 (stage-C): the Inventory lookup must resolve the real catalog stock line.

Remediation emits free-text part names (LLM) that miss the exact-match inventory
`get()`. The orchestrator now leads the CID's inventory query with the
topology-resolved catalog part (`_suspect_part`), so the action report shows the
real stock line (APR48-3G, qty 3, WH-PAR-EST) instead of qty 0 / in_stock false.
"""
from contracts import AgentInput, AgentOutput

from backend.tests.conftest import assert_contract

# Fault at the gold Paris-Nord site; equipment "rectifier" resolves APR48-3G via
# data/equipment.csv topology (EQ-PAR-021N-* rectifier -> part APR48-3G).
FAULT = [{"code": "PWR-DC-UV", "severity": "critical", "equipment": "rectifier",
          "metric": "dc_voltage_v", "value": 44.0, "first_seen": "2026-07-05T09:00:00Z"}]
TRIGGER = {"rule": "PWR-DC-UV", "debounce_s": 60, "triggered_at": "2026-07-05T09:01:01Z"}


class _FreeTextRemediation:
    """Remediation whose parts are LLM free-text that miss the exact inventory get()."""

    name = "remediation"

    async def run(self, data: AgentInput) -> AgentOutput:
        return AgentOutput(
            incident_id=data.incident_id, agent=self.name,
            summary="replace the failed rectifier module",
            payload={
                "procedure": {"title": "Replace rectifier module",
                              "steps": [{"n": 1, "text": "swap the module", "citations": []}]},
                # free-text name, NOT the catalog part number -> exact get() miss
                "parts": [{"part_no": "Eaton 48V/2000W rectifier (generic name)", "qty": 1}],
                "action_hints": [{"priority": "P1", "action": "replace module"}],
            },
            retrieved_refs=[], citations=[], confidence=0.85,
        )


def _validation_body(orch, verdicts):
    return {
        "incident_id": orch.incident["id"], "client_event_id": "t-1",
        "submitted_at": "2026-07-05T09:33:00Z", "technician": {"id": "tech-07"},
        "validations": [{"failure_id": f["id"], "verdict": v}
                        for f, v in zip(orch.incident["failures"], verdicts)],
        "measurements": [{"metric": "dc_voltage_v", "point": "busbar", "value": 43.9, "unit": "V"}],
    }


async def test_inventory_matches_catalog_part_despite_freetext_remediation(orchestrator, bus, event_validator):
    await orchestrator.handle_fault("PAR-021-NORD", "energy", FAULT, TRIGGER)
    await orchestrator.join()

    orchestrator.agents["remediation"] = _FreeTextRemediation()   # LLM free-text parts
    await orchestrator.handle_validation(_validation_body(orchestrator, ["real"]))
    await orchestrator.join()

    report = [e for e in bus.history if e["type"] == "action_report_ready"][-1]["data"]["report"]
    inv = report["inventory"]
    # topology-resolved catalog part won, not the free-text name
    assert inv["part_no"] == "APR48-3G"
    assert inv["qty_available"] == 3
    assert inv["in_stock"] is True
    assert inv["location"] == "WH-PAR-EST"
    assert_contract(bus.history, event_validator)
