"""Adapter wiring vgtray's REAL Correlation agent (AGV.3, /agents/correlation)
into the orchestrator registry — replacing the dummy under the same key (INT.1).

The real agent localizes a fault to a site + one equipment id over the
structured topology and emits payload keys
``located_site_id`` / ``located_equipment_id`` / ``equipment_class`` /
``reasoning_path``. The orchestrator's phase-1 code consumes a different slice
(``payload["correlation"] = {site_id, equipment, blast_radius}`` +
``payload["added_failures"]``), so this adapter translates the shapes.

Correlation runs offline (deterministic taxonomy plan when no Vultr client is
injected); the retriever, when present, adds the citation trail. Backend lane —
``/agents`` is untouched.
"""
from typing import Any

from contracts import AgentInput, AgentOutput

from agents.correlation.agent import CorrelationAgent


class CorrelationAgentAdapter:
    name = "correlation"

    def __init__(self, vultr: Any = None, retriever: Any = None) -> None:
        # No system_prompt override: the agent uses its own tuned prompt.md.
        self._inner = CorrelationAgent(vultr, retriever)

    async def run(self, data: AgentInput) -> AgentOutput:
        out = await self._inner.run(data)
        p = out.payload
        located = p.get("located_equipment_id")
        equipment = [located] if located else (
            [p["equipment_class"]] if p.get("equipment_class") else []
        )
        correlation = {
            "site_id": p.get("located_site_id", data.site_id),
            "equipment": equipment,
            "equipment_class": p.get("equipment_class"),
            "blast_radius": f"localized to {located}" if located else "site-wide",
            "reasoning_path": p.get("reasoning_path", []),
        }
        return AgentOutput(
            incident_id=out.incident_id,
            agent=self.name,
            summary=out.summary,
            payload={"correlation": correlation, "added_failures": []},
            retrieved_refs=out.retrieved_refs,
            citations=out.citations,
            confidence=out.confidence,
        )
