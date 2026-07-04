"""FROZEN Agent & Tool interfaces for Arc (issue #7 / P0.7).

Every specialized agent and the orchestrator runtime import from this module.
It is the single frozen contract that lets the agentic lane build in parallel:
the orchestrator runs against dummy agents, agents run standalone via a CLI
harness, tools are stubbed from their frozen signatures.

Design rules (this file is FROZEN after phase 0 -- change = PR + producer AND
consumers approve):
- Every field must justify itself; no speculative fields.
- All models are JSON-serializable (`model_dump(mode="json")`): AgentOutput
  instances transit inside the SSE event stream.
- Docstrings note producer/consumer per docs/ROADMAP.md.

Producer/consumer summary:
- AgentInput  -- produced by the orchestrator, consumed by every agent.
- AgentOutput -- produced by every agent, consumed by the orchestrator runtime
  and rendered into the SSE stream / prioritized action report.
- RetrievedRef / Citation -- produced by retrieving agents (Correlation,
  Root-Cause, Remediation) via VultronRetriever, consumed by the control-room
  report renderer as the full citation trail.
"""

from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "RetrievedRef",
    "Citation",
    "AgentInput",
    "AgentOutput",
    "Agent",
    "Tool",
    # DRAFT tool signatures
    "CostQuery",
    "CostReport",
    "InventoryQuery",
    "InventoryLine",
    "InventoryMatch",
    "DispatchRequest",
    "DispatchBooking",
    "CostTool",
    "InventoryTool",
    "DispatchTool",
]


# --------------------------------------------------------------------------- #
# Evidence & citation trail
# --------------------------------------------------------------------------- #
class RetrievedRef(BaseModel):
    """A candidate evidence chunk returned by VultronRetriever.

    Producer: any retrieving agent. Consumer: the same agent (to reason and to
    decide what to cite). The pool of refs an agent pulled lands on
    AgentOutput.retrieved_refs for traceability.
    """

    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(description="Identifier of the source document in the corpus.")
    section: str = Field(description="Section / heading / clause the chunk came from.")
    snippet: str = Field(description="Retrieved text used as evidence.")
    score: float | None = Field(default=None, description="Retriever relevance score, if available.")


class Citation(BaseModel):
    """One entry of the full citation trail backing a claim in an AgentOutput.

    Producer: the agent that made the claim. Consumer: the control-room report
    renderer. Minimal by contract: doc id + section pinpoint the source.
    """

    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(description="Identifier of the cited source document.")
    section: str = Field(description="Cited section / heading / clause within the document.")
    snippet: str | None = Field(default=None, description="Optional quoted text, for display in the trail.")


# --------------------------------------------------------------------------- #
# Agent I/O
# --------------------------------------------------------------------------- #
class AgentInput(BaseModel):
    """What the orchestrator hands to an agent's `run`.

    Producer: orchestrator runtime. Consumer: every agent. The typed spine
    (incident id + site + failure family) is universal across the whole system;
    everything else (raw FaultEvent, accumulated upstream findings, human
    validation result) rides in `context`, whose inner shape is owned by the
    event contract (issue #6 / P0.6, simerugby).
    """

    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(description="Run correlation id; ties every agent output to one incident (SSE stream key).")
    site_id: str = Field(description="Telecom site under fault (cell tower / base station / central office).")
    failure_family: str = Field(description="Fault taxonomy family, e.g. 'energy/power', 'rf/radio'.")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Incident/fault info + accumulated upstream findings; shape owned by the event contract.",
    )


class AgentOutput(BaseModel):
    """What an agent returns from `run`.

    Producer: every agent. Consumer: orchestrator runtime + SSE stream +
    prioritized action report. `confidence` drives the Root-Cause re-query gate
    (Vultr compliance: retrieve more than once when confidence is low).
    """

    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(description="Echoes AgentInput.incident_id (SSE correlation).")
    agent: str = Field(description="Name of the producing agent, e.g. 'root_cause'.")
    summary: str = Field(description="Human-readable result for the NOC timeline / report.")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured agent-specific result (ranked causes, remediation steps, tool results, ...).",
    )
    retrieved_refs: list[RetrievedRef] = Field(
        default_factory=list,
        description="Evidence this agent pulled from VultronRetriever.",
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Subset actually used to justify the output -- the citation trail.",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Self-assessed confidence in this output, 0..1.")


# --------------------------------------------------------------------------- #
# Agent protocol
# --------------------------------------------------------------------------- #
@runtime_checkable
class Agent(Protocol):
    """Structural contract every agent satisfies -- no base class to inherit.

    Implement `name` and an async `run`; that is the whole contract. The
    orchestrator uses `name` for routing/telemetry and awaits `run` per step.
    """

    name: str

    async def run(self, data: AgentInput) -> AgentOutput: ...


# --------------------------------------------------------------------------- #
# Generic tool protocol
# --------------------------------------------------------------------------- #
TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


@runtime_checkable
class Tool(Protocol[TInput, TOutput]):
    """Generic async tool: a name, the JSON Schema of its input, an async call.

    Producer: backend (simerugby). Consumer: the Cost/Inventory/Dispatch agent
    (aminssutt). `input_schema` is typically `<InputModel>.model_json_schema()`.
    """

    name: str
    input_schema: dict[str, Any]

    async def __call__(self, payload: TInput) -> TOutput: ...


# --------------------------------------------------------------------------- #
# DRAFT concrete tool signatures
# DRAFT -- to be approved by simerugby via PR review (backend owns the tool APIs).
# Field sets below are a plausible starting point, not frozen; only the
# Agent/Tool interfaces above are frozen by this issue.
# --------------------------------------------------------------------------- #
class CostQuery(BaseModel):
    """DRAFT -- input to the Cost Engine tool."""

    incident_id: str
    site_id: str
    failure_family: str
    remediation: str = Field(description="Proposed remediation action being priced.")
    parts: list[str] = Field(default_factory=list, description="Candidate part numbers involved.")


class CostReport(BaseModel):
    """DRAFT -- output of the Cost Engine tool (feeds 'cost avoided' in the report)."""

    incident_id: str
    downtime_cost_avoided: float = Field(description="Estimated cost avoided by acting now.")
    repair_cost: float = Field(description="Estimated cost of the remediation.")
    currency: str = "USD"
    breakdown: dict[str, float] = Field(default_factory=dict, description="Optional line items.")


class InventoryQuery(BaseModel):
    """DRAFT -- input to the Inventory Lookup tool."""

    incident_id: str
    site_id: str = Field(description="Site needing the parts (drives nearest-warehouse match).")
    part_numbers: list[str] = Field(description="Candidate parts required by the remediation.")


class InventoryLine(BaseModel):
    """DRAFT -- per-part availability inside an InventoryMatch."""

    part_number: str
    in_stock: bool
    quantity: int = 0
    warehouse_id: str | None = None
    eta_hours: float | None = Field(default=None, description="Lead time if not in stock.")


class InventoryMatch(BaseModel):
    """DRAFT -- output of the Inventory Lookup tool (part matched to stock)."""

    incident_id: str
    matches: list[InventoryLine] = Field(default_factory=list)


class DispatchRequest(BaseModel):
    """DRAFT -- input to the Crew Dispatch tool."""

    incident_id: str
    site_id: str
    skill: str = Field(description="Required crew skill, e.g. 'power', 'rf', 'transport'.")
    priority: str = Field(description="Dispatch priority, e.g. 'P1'.")
    parts: list[str] = Field(default_factory=list, description="Parts the crew must bring.")


class DispatchBooking(BaseModel):
    """DRAFT -- output of the Crew Dispatch tool (field crew booked)."""

    incident_id: str
    crew_id: str
    booked: bool
    eta_hours: float | None = None
    window: str | None = Field(default=None, description="Scheduled arrival window.")


# Typed tool contracts (DRAFT) -- the three real tools the CID agent calls.
CostTool = Tool[CostQuery, CostReport]
InventoryTool = Tool[InventoryQuery, InventoryMatch]
DispatchTool = Tool[DispatchRequest, DispatchBooking]
