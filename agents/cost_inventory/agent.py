"""Cost, Inventory & Dispatch (CID) agent -- the prioritized action report.

Owner: aminssutt. Ticket: AGA.3 (#30).

Last step of Phase 2. It calls the **three real backend tools** (Cost Engine,
Inventory Lookup, Crew Dispatch) through the frozen ``contracts.Tool`` protocol
and assembles the **prioritized action report** (diagnosis, remediation, cost
avoided, part matched to stock, crew booked) with a citation trail.

The agent does the reasoning; the tools do the lookups. It never fabricates a
price, stock line, ETA, or crew id -- every such value comes from a tool result.
Registers under the name ``cost_inventory_dispatch`` so it drops into the
backend orchestrator registry in place of the stand-in (backend #15).

Tools are injected (``contracts.Tool``), so the agent is unit-testable with
fakes and integration-testable against the real tools + seeds.
"""

from __future__ import annotations

from typing import Any, Protocol

from contracts.agent_interface import (
    AgentInput,
    AgentOutput,
    Citation,
    CostQuery,
    CostReport,
    DispatchBooking,
    DispatchRequest,
    InventoryMatch,
    InventoryQuery,
)

NAME = "cost_inventory_dispatch"

# Fault family -> required crew skill (mirrors the backend orchestrator).
_FAMILY_SKILL = {"energy": "power", "environment": "power", "rf": "rf", "transport": "transport"}


# --------------------------------------------------------------------------- #
# Injected tool protocols (the 3 real tools satisfy contracts.Tool)
# --------------------------------------------------------------------------- #
class _CostTool(Protocol):
    async def __call__(self, payload: CostQuery) -> CostReport: ...


class _InventoryTool(Protocol):
    async def __call__(self, payload: InventoryQuery) -> InventoryMatch: ...


class _DispatchTool(Protocol):
    async def __call__(self, payload: DispatchRequest) -> DispatchBooking: ...


# --------------------------------------------------------------------------- #
# Input helpers
# --------------------------------------------------------------------------- #
def _part_numbers(context: dict[str, Any]) -> list[str]:
    """Extract part numbers from the backend context shape or the agents-lane one."""
    parts: list[str] = []
    for p in context.get("parts", []) or []:
        pn = (p.get("part_no") or p.get("part_number")) if isinstance(p, dict) else p
        if pn:
            parts.append(pn)
    if not parts:  # agents-lane fallback: remediation.parts_needed = [str, ...]
        rem = context.get("findings", {}).get("remediation", {})
        parts = [p for p in rem.get("parts_needed", []) if p]
    return parts


def _remediation_title(context: dict[str, Any]) -> str:
    if context.get("remediation_title"):
        return context["remediation_title"]
    rem = context.get("findings", {}).get("remediation", {})
    return rem.get("confirmed_cause") or "remediation"


def _gather_citations(context: dict[str, Any]) -> list[Citation]:
    """Best-effort citation trail from upstream findings (root_cause + remediation)."""
    out: list[Citation] = []
    seen: set[tuple[str, str | None]] = set()
    findings = context.get("findings", {})

    def _add(doc_id: str | None, section: str | None) -> None:
        if doc_id and (doc_id, section) not in seen:
            seen.add((doc_id, section))
            out.append(Citation(doc_id=doc_id, section=section))

    for step in findings.get("remediation", {}).get("safety_steps", []):
        _add(step.get("doc_id"), step.get("section"))
    sig_cite = findings.get("root_cause", {}).get("top_cause", {}).get("signature", {}).get("citation")
    if isinstance(sig_cite, dict):
        _add(sig_cite.get("doc_id"), sig_cite.get("section"))
    return out


def _totals_consistent(cost: CostReport) -> bool:
    """Verify the report echoes the Cost Engine's own breakdown (no re-derivation)."""
    bd = cost.breakdown or {}
    repair = bd.get("parts", 0) + bd.get("labor", 0) + bd.get("truck_roll", 0)
    avoided = bd.get("downtime_avoided", 0) + bd.get("sla_penalty_avoided", 0)
    return abs(repair - cost.repair_cost) < 0.01 and abs(avoided - cost.downtime_cost_avoided) < 0.01


# --------------------------------------------------------------------------- #
# Agent
# --------------------------------------------------------------------------- #
class CostInventoryDispatchAgent:
    """Calls the 3 tools and emits the prioritized action report (Phase 2, step 2)."""

    name = NAME

    def __init__(self, cost: _CostTool, inventory: _InventoryTool, dispatch: _DispatchTool) -> None:
        self._cost = cost
        self._inventory = inventory
        self._dispatch = dispatch

    async def run(self, data: AgentInput) -> AgentOutput:
        parts = _part_numbers(data.context)
        remediation = _remediation_title(data.context)
        priority = data.context.get("top_priority", "P1")
        skill = _FAMILY_SKILL.get(data.failure_family, "power")

        # --- three real tool calls -------------------------------------- #
        inv_q = InventoryQuery(incident_id=data.incident_id, site_id=data.site_id, part_numbers=parts)
        inv = await self._inventory(inv_q)

        cost_q = CostQuery(incident_id=data.incident_id, site_id=data.site_id,
                           failure_family=data.failure_family, remediation=remediation, parts=parts)
        cost = await self._cost(cost_q)

        disp_q = DispatchRequest(incident_id=data.incident_id, site_id=data.site_id,
                                 skill=skill, priority=priority, parts=parts)
        booking = await self._dispatch(disp_q)

        # --- make each tool call explicit in the event payload ---------- #
        tool_calls = [
            {"tool": getattr(self._inventory, "name", "inventory_lookup"),
             "request": inv_q.model_dump(mode="json"),
             "response": {"matched": len(inv.matches),
                          "in_stock": sum(1 for m in inv.matches if m.in_stock)}},
            {"tool": getattr(self._cost, "name", "cost_engine"),
             "request": cost_q.model_dump(mode="json"),
             "response": {"repair_cost": cost.repair_cost,
                          "downtime_cost_avoided": cost.downtime_cost_avoided,
                          "currency": cost.currency}},
            {"tool": getattr(self._dispatch, "name", "crew_dispatch"),
             "request": disp_q.model_dump(mode="json"),
             "response": {"booked": booking.booked, "crew_id": booking.crew_id,
                          "eta_hours": booking.eta_hours}},
        ]

        # --- prioritized action report --------------------------------- #
        first = inv.matches[0] if inv.matches else None
        honesty: list[str] = []
        if not booking.booked:
            honesty.append("no crew available for immediate dispatch — booking conflict flagged")
        if first is not None and not first.in_stock:
            honesty.append(f"part {first.part_number} out of stock — lead time {first.eta_hours}h")

        report = {
            "diagnosis": data.context.get("findings", {}).get("root_cause", {}).get("top_cause")
            or {"cause": remediation},
            "actions": [{
                "priority": priority,
                "action": remediation,
                **({"owner": booking.crew_id} if booking.booked else {}),
            }],
            "cost": {"currency": cost.currency, "repair_cost": cost.repair_cost,
                     "cost_avoided": cost.downtime_cost_avoided, "breakdown": cost.breakdown},
            "part": None if first is None else {
                "part_number": first.part_number, "in_stock": first.in_stock,
                "quantity": first.quantity, "warehouse_id": first.warehouse_id,
                "eta_hours": first.eta_hours,
            },
            "crew": {"crew_id": booking.crew_id, "booked": booking.booked,
                     "eta_hours": booking.eta_hours, "window": booking.window},
            "citations": [c.model_dump(mode="json") for c in _gather_citations(data.context)],
            "honesty_notes": honesty,
        }

        payload = {
            # keys the backend _assemble_report consumes verbatim:
            "cost": cost.model_dump(mode="json"),
            "inventory": inv.model_dump(mode="json"),
            "dispatch": booking.model_dump(mode="json"),
            # #30 deliverables:
            "tool_calls": tool_calls,
            "action_report": report,
            "totals_consistent": _totals_consistent(cost),
        }

        in_stock = sum(1 for m in inv.matches if m.in_stock)
        summary = (
            f"3 tool calls: repair {cost.repair_cost:.2f} {cost.currency} "
            f"(avoided {cost.downtime_cost_avoided:.2f}), {in_stock}/{len(inv.matches)} parts in stock, "
            f"crew {'booked ' + booking.crew_id if booking.booked else 'CONFLICT — none available'}."
        )
        confidence = 1.0 if (booking.booked and in_stock and payload["totals_consistent"]) else 0.75

        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=summary,
            payload=payload,
            retrieved_refs=[],
            citations=_gather_citations(data.context),
            confidence=confidence,
        )
