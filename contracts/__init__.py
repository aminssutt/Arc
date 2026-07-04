"""Arc frozen contracts (phase 0).

Public agent/tool interface surface. Import from here rather than reaching into
submodules, e.g. `from contracts import AgentInput, AgentOutput, Agent, Tool`.
"""

from contracts.agent_interface import (
    Agent,
    AgentInput,
    AgentOutput,
    Citation,
    CostQuery,
    CostReport,
    CostTool,
    DispatchBooking,
    DispatchRequest,
    DispatchTool,
    InventoryLine,
    InventoryMatch,
    InventoryQuery,
    InventoryTool,
    RetrievedRef,
    Tool,
)

__all__ = [
    "Agent",
    "AgentInput",
    "AgentOutput",
    "Citation",
    "RetrievedRef",
    "Tool",
    "CostQuery",
    "CostReport",
    "CostTool",
    "InventoryQuery",
    "InventoryLine",
    "InventoryMatch",
    "InventoryTool",
    "DispatchRequest",
    "DispatchBooking",
    "DispatchTool",
]
