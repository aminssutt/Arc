"""Orchestration glue (aminssutt, AGA.4 #31).

Registry + declarative phase plan + persona loader + an offline chain harness.
The backend runtime (#15) plugs real agents into the same registry and plan;
this package holds no state and does no diagnosis.
"""

from agents.orchestration.citations import load_sources, resolve_citation, resolve_report_citations
from agents.orchestration.harness import ChainResult, run_phase, run_plan
from agents.orchestration.personas import available_personas, load_persona, persona_path
from agents.orchestration.plan import ALL_AGENTS, PHASE_PLAN, Phase, agents_for
from agents.orchestration.registry import AgentRegistry

__all__ = [
    "AgentRegistry",
    "Phase",
    "PHASE_PLAN",
    "ALL_AGENTS",
    "agents_for",
    "ChainResult",
    "run_phase",
    "run_plan",
    "load_persona",
    "available_personas",
    "persona_path",
    "resolve_citation",
    "resolve_report_citations",
    "load_sources",
]
