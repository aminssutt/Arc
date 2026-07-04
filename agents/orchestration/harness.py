"""Offline chain harness -- run a phase (or the whole plan) with no backend.

Owner: aminssutt. Ticket: AGA.4 (#31).

Proves the phase sequencing end-to-end **offline**: given a registry of
``Agent``-conforming objects and a seed ``AgentInput``, it runs each phase's
agents in order and threads every agent's ``payload`` forward under
``context["findings"][<agent name>]`` -- the accumulation slot the AgentInput
contract reserves for "accumulated upstream findings". No HTTP, no state
machine, no LLM required: the real backend runtime (#15) reuses the same
registry + plan; this harness is what makes the lane demo-able standalone
against dummy agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from contracts.agent_interface import AgentInput, AgentOutput
from agents.orchestration.plan import PHASE_PLAN, Phase
from agents.orchestration.registry import AgentRegistry

OnOutput = Callable[[AgentOutput], None]


@dataclass
class ChainResult:
    """Outputs of a chain run plus the accumulated context to feed the next phase."""

    outputs: list[AgentOutput] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def findings(self) -> dict[str, Any]:
        return self.context.get("findings", {})

    def last(self) -> AgentOutput | None:
        return self.outputs[-1] if self.outputs else None


def _step_input(seed: AgentInput, context: dict[str, Any]) -> AgentInput:
    return AgentInput(
        incident_id=seed.incident_id,
        site_id=seed.site_id,
        failure_family=seed.failure_family,
        context=context,
    )


async def run_phase(
    registry: AgentRegistry,
    phase: Phase,
    seed: AgentInput,
    *,
    context: dict[str, Any] | None = None,
    on_output: OnOutput | None = None,
) -> ChainResult:
    """Run ``phase``'s agents in order, threading findings forward.

    ``context`` seeds the accumulation (defaults to ``seed.context``); each
    agent sees all prior findings and its own required keys.
    """
    ctx: dict[str, Any] = dict(context if context is not None else seed.context)
    findings: dict[str, Any] = dict(ctx.get("findings", {}))
    ctx["findings"] = findings

    outputs: list[AgentOutput] = []
    for name in PHASE_PLAN[phase]:
        agent = registry.get(name)
        out = await agent.run(_step_input(seed, dict(ctx)))
        findings[out.agent] = out.payload
        outputs.append(out)
        if on_output is not None:
            on_output(out)

    return ChainResult(outputs=outputs, context=ctx)


async def run_plan(
    registry: AgentRegistry,
    phases: list[Phase],
    seed: AgentInput,
    *,
    context: dict[str, Any] | None = None,
    on_output: OnOutput | None = None,
) -> ChainResult:
    """Run several phases back to back, carrying findings across them."""
    ctx: dict[str, Any] = dict(context if context is not None else seed.context)
    all_outputs: list[AgentOutput] = []
    for phase in phases:
        result = await run_phase(registry, phase, seed, context=ctx, on_output=on_output)
        ctx = result.context
        all_outputs.extend(result.outputs)
    return ChainResult(outputs=all_outputs, context=ctx)


def _demo() -> None:
    """Run PHASE1 offline with two placeholder agents (real ones are vgtray's)."""
    import asyncio

    class _Stub:
        """Minimal Agent-conforming placeholder for the offline harness."""

        def __init__(self, name: str, payload: dict[str, Any], confidence: float) -> None:
            self.name = name
            self._payload = payload
            self._confidence = confidence

        async def run(self, data: AgentInput) -> AgentOutput:
            return AgentOutput(
                incident_id=data.incident_id,
                agent=self.name,
                summary=f"[stub] {self.name} for {data.incident_id}",
                payload={**self._payload, "saw_findings": sorted(data.context.get("findings", {}))},
                retrieved_refs=[],
                citations=[],
                confidence=self._confidence,
            )

    registry = AgentRegistry()
    registry.register(_Stub("correlation", {"site": "PAR-021-NORD", "equipment": "rectifier-2"}, 0.8))
    registry.register(_Stub("root_cause", {"top_cause": "rectifier module failure"}, 0.82))

    seed = AgentInput(incident_id="INC-DEMO-001", site_id="PAR-021-NORD", failure_family="energy")
    result = asyncio.run(run_phase(registry, Phase.PHASE1, seed, on_output=lambda o: print(f"  -> {o.agent}: {o.summary}")))
    print(f"\nfindings accumulated: {sorted(result.findings)}")
    print(f"root_cause saw upstream: {result.findings['root_cause']['saw_findings']}")


if __name__ == "__main__":
    _demo()
