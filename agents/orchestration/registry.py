"""Agent registry -- name -> Agent lookup for the orchestrator.

Owner: aminssutt. Ticket: AGA.4 (#31).

The backend orchestrator runtime (#15, simerugby) holds state and *never*
diagnoses; it runs agents purely by name through this registry. Any object that
structurally satisfies the frozen ``contracts.Agent`` protocol can be
registered -- real agents (validation, root_cause, ...) or dummy/stub agents for
the offline harness. Registration is validated at insert time so a
non-conforming object fails loudly here, not mid-incident.
"""

from __future__ import annotations

from contracts.agent_interface import Agent


class AgentRegistry:
    """Ordered, name-keyed collection of ``Agent``-conforming objects."""

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> Agent:
        """Register ``agent`` under its ``name``; returns it for chaining.

        Raises ``TypeError`` if it does not satisfy the Agent protocol and
        ``ValueError`` on a duplicate name.
        """
        if not isinstance(agent, Agent):
            raise TypeError(
                f"{agent!r} does not satisfy the contracts.Agent protocol "
                "(needs a `name` attribute and an async `run(AgentInput)`)."
            )
        name = agent.name
        if name in self._agents:
            raise ValueError(f"agent name already registered: {name!r}")
        self._agents[name] = agent
        return agent

    def register_all(self, agents: list[Agent]) -> None:
        for a in agents:
            self.register(a)

    def get(self, name: str) -> Agent:
        try:
            return self._agents[name]
        except KeyError:
            raise KeyError(
                f"no agent registered as {name!r}; registered: {self.names()}"
            ) from None

    def has(self, name: str) -> bool:
        return name in self._agents

    def names(self) -> list[str]:
        return list(self._agents)

    def __contains__(self, name: object) -> bool:
        return name in self._agents

    def __len__(self) -> int:
        return len(self._agents)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"AgentRegistry({self.names()})"
