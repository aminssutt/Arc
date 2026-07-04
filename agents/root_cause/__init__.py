"""Root-Cause agent package (issue #27 / AGV.4).

Exposes the confidence-gated, multi-pass ``RootCauseAgent`` and its ``GateConfig``.
"""

from agents.root_cause.agent import GateConfig, RootCauseAgent

__all__ = ["RootCauseAgent", "GateConfig"]
