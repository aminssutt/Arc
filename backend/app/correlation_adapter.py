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
import json
import os
import tempfile
from typing import Any

from contracts import AgentInput, AgentOutput

from agents.correlation.agent import CorrelationAgent


def _build_correlation_agent(vultr: Any, retriever: Any, seeds: Any) -> CorrelationAgent:
    """Construct the CorrelationAgent with a topology built from the CURRENT seeds.

    The agent's bundled fixture is a static copy of /data that drifts when the
    seeds are renamed (e.g. the PAR-021-NORD audit), making correlation fail to
    localize on the real demo site. Building the topology from the loaded seeds
    is the single source of truth — no drift. The agent reads the topology file
    once at construction, so the temp file is removed immediately after.
    """
    if seeds is None:
        return CorrelationAgent(vultr, retriever)  # backwards-compatible fixture path

    topo = {
        "sites": [dict(s) for s in seeds.sites.values()],
        "equipment": [{**dict(e), "parent_id": (e.get("parent_id") or None)}
                      for e in seeds.equipment.values()],
    }
    f = tempfile.NamedTemporaryFile("w", suffix="_arc_topology.json", delete=False, encoding="utf-8")
    try:
        json.dump(topo, f)
        f.close()
        return CorrelationAgent(vultr, retriever, topology_path=f.name)  # read at __init__
    finally:
        try:
            os.unlink(f.name)
        except OSError:
            pass


class CorrelationAgentAdapter:
    name = "correlation"

    def __init__(self, vultr: Any = None, retriever: Any = None, *, seeds: Any = None) -> None:
        # No system_prompt override: the agent uses its own tuned prompt.md.
        self._inner = _build_correlation_agent(vultr, retriever, seeds)

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
