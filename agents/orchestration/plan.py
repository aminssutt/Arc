"""Phase plan -- the declarative agent sequence per phase.

Owner: aminssutt. Ticket: AGA.4 (#31).

The orchestrator sequences specialized agents in two phases with a human
validation loop in the middle (see docs/ROADMAP.md). This module is *data*, not
control flow: it names which agents run, in what order, per phase. The backend
state machine (#15) maps its states onto these phases; the offline harness
(``harness.py``) walks them directly.

    idle -> fault_triggered
         -> PHASE1  (correlation -> root_cause)
         -> awaiting_field_validation
         -> HUMAN_LOOP (validation: confirm | PIVOT back to PHASE1)
         -> PHASE2  (remediation -> cost_inventory_dispatch)
         -> report_ready -> resolved
"""

from __future__ import annotations

from enum import Enum


class Phase(str, Enum):
    """Ordered phases the orchestrator walks."""

    PHASE1 = "phase1"
    HUMAN_LOOP = "human_loop"
    PHASE2 = "phase2"


# Ordered agent names executed in each phase. Names are the ``Agent.name`` keys
# used by the registry and, once emitted, MUST match the frozen
# ``events.schema.json`` agent enum. Wire name vs module path: the Cost/Inventory/
# Dispatch agent's wire name is ``cost_inventory_dispatch`` (Agent.name + events
# enum); its implementing module intentionally stays at ``agents/cost_inventory/``
# -- module path != wire name, so do NOT rename that directory. The two agentic
# devs own disjoint lanes (ROADMAP split).
PHASE_PLAN: dict[Phase, tuple[str, ...]] = {
    Phase.PHASE1: ("correlation", "root_cause"),
    Phase.HUMAN_LOOP: ("validation",),
    Phase.PHASE2: ("remediation", "cost_inventory_dispatch"),
}

# Convenience: every agent name referenced by the plan, in execution order.
ALL_AGENTS: tuple[str, ...] = tuple(
    name for phase in Phase for name in PHASE_PLAN[phase]
)


def agents_for(phase: Phase) -> tuple[str, ...]:
    """Ordered agent names for ``phase``."""
    return PHASE_PLAN[phase]
