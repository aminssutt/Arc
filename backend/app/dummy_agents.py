"""Dummy agents — canned stand-ins satisfying the FROZEN Agent protocol (BE.3).

These prove the orchestrator runs end-to-end through the registry. They contain
NO diagnosis logic (backend acceptance): outputs are canned shapes referencing
seeded corpus doc ids, mechanically parameterized by the incident context. The
real agents (vgtray: correlation/root_cause · aminssutt: validation/remediation/
cost_inventory_dispatch) replace them by registering under the same names.

The cost_inventory_dispatch stand-in is special: it calls the THREE REAL TOOLS
through the frozen Tool protocol, so tools are exercised live in every E2E run.
"""
from typing import Any

from contracts import (
    Agent,
    AgentInput,
    AgentOutput,
    Citation,
    CostQuery,
    CostTool,
    DispatchRequest,
    DispatchTool,
    InventoryQuery,
    InventoryTool,
    RetrievedRef,
)

_FAMILY_SKILL = {"energy": "power", "environment": "power", "rf": "rf", "transport": "transport"}


class DummyCorrelationAgent:
    name = "correlation"

    async def run(self, data: AgentInput) -> AgentOutput:
        failures: list[dict] = data.context.get("failures", [])
        equipment = sorted({f["equipment"] for f in failures}) or ["unknown"]
        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=f"{data.site_id}: {', '.join(equipment)} implicated ({len(failures)} failure(s)) [dummy]",
            payload={
                "correlation": {
                    "site_id": data.site_id,
                    "equipment": equipment,
                    "blast_radius": "site-wide (dummy placeholder)",
                },
                "added_failures": [],
            },
            retrieved_refs=[],
            citations=[],
            confidence=0.9,
        )


class DummyRootCauseAgent:
    name = "root_cause"

    async def run(self, data: AgentInput) -> AgentOutput:
        failures: list[dict] = data.context.get("failures", [])
        top = failures[0] if failures else {"code": "UNKNOWN", "id": "F1"}
        pivot = data.context.get("phase_cause") == "pivot"
        if pivot:
            causes = [
                {"rank": 1, "cause": "telemetry/sensing path fault — field measurement contradicts feed (dummy re-diagnosis)",
                 "confidence": 0.84,
                 "citations": [{"doc_id": "DOC-OUT-045", "claim": "historical: fault mistaken for DC issue"}]},
                {"rank": 2, "cause": f"{top['code']} as originally reported — demoted after contradiction",
                 "confidence": 0.2,
                 "citations": [{"doc_id": "DOC-INC-114", "claim": "original signature match"}]},
            ]
            retrievals = [{"pass": 3, "query": "measurement contradicts telemetry sensing fault",
                           "results": [{"doc_id": "DOC-OUT-045", "title": "Outage OUT-045", "score": 0.83}]}]
            urgency = {"kind": "none_immediate", "basis": "field measurement normal (dummy)"}
        else:
            causes = [
                {"rank": 1, "cause": f"{top['code']} — primary suspected cause (dummy)",
                 "confidence": 0.87,
                 "citations": [{"doc_id": "DOC-INC-114", "claim": "matching historical incident"},
                               {"doc_id": "DOC-RAN-001", "claim": "vendor O&M alarm signature"}]},
                {"rank": 2, "cause": "grid loss", "confidence": 0.06,
                 "rejected_because": "mains signal normal (dummy)",
                 "citations": [{"doc_id": "DOC-RAN-001", "claim": "mains alarm definition"}]},
            ]
            retrievals = [
                {"pass": 1, "query": f"{top['code']} alarm signature",
                 "results": [{"doc_id": "DOC-INC-114", "title": "INC-114 ticket", "score": 0.86},
                             {"doc_id": "DOC-RAN-001", "title": "NetSure-48 O&M", "score": 0.74}]},
                {"pass": 2, "query": "battery autonomy discharge procedure",
                 "results": [{"doc_id": "DOC-PWR-002", "title": "DC undervoltage procedure", "score": 0.81}]},
            ]
            urgency = {"kind": "time_to_lvd", "estimate_min": 210,
                       "basis": "design autonomy from power_plant seed (dummy)",
                       "citations": [{"doc_id": "DOC-PWR-002", "claim": "discharge criteria"}]}
        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=causes[0]["cause"],
            payload={
                "retrievals": retrievals,
                "diagnostic": {
                    "causes": causes,
                    "urgency": urgency,
                    "verification_requests": [
                        {"failure_id": top.get("id", "F1"),
                         "action": "physically verify at the measurement point",
                         "metric": top.get("metric", ""), "point": top.get("equipment", "")}
                    ] if not pivot else [],
                },
            },
            retrieved_refs=[RetrievedRef(doc_id=r["results"][0]["doc_id"], section="s", snippet="…", score=r["results"][0].get("score"))
                            for r in retrievals],
            citations=[Citation(doc_id=c["citations"][0]["doc_id"], section=c["citations"][0]["claim"]) for c in causes],
            confidence=causes[0]["confidence"],
        )


class DummyValidationAgent:
    name = "validation"

    async def run(self, data: AgentInput) -> AgentOutput:
        verdicts: list[dict] = data.context.get("validations", [])
        measurements: list[dict] = data.context.get("measurements", [])
        all_real = bool(verdicts) and all(v["verdict"] == "real" for v in verdicts)
        result = "confirmed" if all_real else "pivot"
        contradictions = [
            {"failure_id": v["failure_id"], "measured": (measurements[0]["value"] if measurements else None)}
            for v in verdicts if v["verdict"] == "false"
        ]
        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=f"field validation → {result} (dummy rule: any false verdict pivots)",
            payload={"result": result,
                     "rationale": "all failures confirmed real by technician" if all_real
                     else "technician contradicted at least one detected failure",
                     "contradictions": contradictions},
            retrieved_refs=[],
            citations=[],
            confidence=0.95,
        )


class DummyRemediationAgent:
    name = "remediation"

    async def run(self, data: AgentInput) -> AgentOutput:
        pivot = data.context.get("validation_result") == "pivot"
        part = data.context.get("suspect_part") or "PN-RECT-48-2000"
        if pivot:
            procedure = {
                "title": "Replace sensing path / verify telemetry; schedule original fix (dummy)",
                "steps": [
                    {"n": 1, "text": "Replace/reseat the sensing module; verify telemetry matches DMM",
                     "citations": [{"doc_id": "DOC-OUT-045", "claim": "post-incident corrective action"}]},
                    {"n": 2, "text": "Schedule the originally reported repair in the next maintenance window",
                     "citations": [{"doc_id": "DOC-RAN-001", "claim": "hot-swap maintenance procedure"}]},
                ],
                "safety": [{"text": "Standard DC plant PPE; insulated tools",
                            "citations": [{"doc_id": "DOC-RAN-001", "claim": "safety section"}]}],
            }
            hints = [{"priority": "P2", "action": "Replace sensing module and verify telemetry"},
                     {"priority": "P3", "action": "Scheduled repair of originally reported failure (demoted)"}]
        else:
            procedure = {
                "title": "Replace failed module per vendor procedure (dummy)",
                "steps": [
                    {"n": 1, "text": "Verify redundancy carries load before extraction",
                     "citations": [{"doc_id": "DOC-RAN-001", "claim": "hot-swap precondition"}]},
                    {"n": 2, "text": "Swap module; verify plant returns to float",
                     "citations": [{"doc_id": "DOC-PWR-002", "claim": "recovery procedure"}]},
                ],
                "safety": [{"text": "DC plant lockout per SOP; insulated tools",
                            "citations": [{"doc_id": "DOC-RAN-001", "claim": "safety section"}]}],
            }
            hints = [{"priority": "P1", "action": "Replace failed module (part matched to stock)"},
                     {"priority": "P2", "action": "Post-restore health check per procedure"}]
        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=procedure["title"],
            payload={"procedure": procedure, "parts": [{"part_no": part, "description": "matched spare (dummy)", "qty": 1}],
                     "action_hints": hints},
            retrieved_refs=[],
            citations=[Citation(doc_id="DOC-PWR-002", section="recovery procedure")],
            confidence=0.88,
        )


class ToolCallingCIDAgent:
    """cost_inventory_dispatch stand-in that makes REAL tool calls (BE.7-9 E2E)."""

    name = "cost_inventory_dispatch"

    def __init__(self, cost: CostTool, inventory: InventoryTool, dispatch: DispatchTool) -> None:
        self._cost, self._inventory, self._dispatch = cost, inventory, dispatch

    async def run(self, data: AgentInput) -> AgentOutput:
        parts: list[str] = [p["part_no"] for p in data.context.get("parts", [])]
        remediation: str = data.context.get("remediation_title", "remediation")
        priority: str = data.context.get("top_priority", "P1")
        inv = await self._inventory(InventoryQuery(
            incident_id=data.incident_id, site_id=data.site_id, part_numbers=parts))
        cost = await self._cost(CostQuery(
            incident_id=data.incident_id, site_id=data.site_id,
            failure_family=data.failure_family, remediation=remediation, parts=parts))
        booking = await self._dispatch(DispatchRequest(
            incident_id=data.incident_id, site_id=data.site_id,
            skill=_FAMILY_SKILL.get(data.failure_family, "power"),
            priority=priority, parts=parts))
        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=f"3 tool calls: cost {cost.repair_cost:.2f} {cost.currency}, "
                    f"{sum(1 for m in inv.matches if m.in_stock)}/{len(inv.matches)} parts in stock, "
                    f"crew {'booked: ' + booking.crew_id if booking.booked else 'CONFLICT — none available'}",
            payload={
                "cost": cost.model_dump(mode="json"),
                "inventory": inv.model_dump(mode="json"),
                "dispatch": booking.model_dump(mode="json"),
            },
            retrieved_refs=[],
            citations=[],
            confidence=1.0,
        )


def default_registry(cost: CostTool, inventory: InventoryTool, dispatch: DispatchTool) -> dict[str, Agent]:
    return {
        "correlation": DummyCorrelationAgent(),
        "root_cause": DummyRootCauseAgent(),
        "validation": DummyValidationAgent(),
        "remediation": DummyRemediationAgent(),
        "cost_inventory_dispatch": ToolCallingCIDAgent(cost, inventory, dispatch),
    }
