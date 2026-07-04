"""EchoAgent -- minimal reference implementation of the frozen Agent protocol.

Proves the contract in `agent_interface` is implementable with no base class:
EchoAgent is a plain class that structurally satisfies `Agent` (verified with
`isinstance(EchoAgent(), Agent)` thanks to `@runtime_checkable`).

Run standalone:  `python -m contracts.echo_agent`
"""

from contracts.agent_interface import Agent, AgentInput, AgentOutput


class EchoAgent:
    """Echoes the incident back as a trivial, high-confidence AgentOutput.

    No retrieval, no citations -- it exists so the orchestrator can run against
    a dummy agent and so the contract test has something to assert against.
    """

    name = "echo"

    async def run(self, data: AgentInput) -> AgentOutput:
        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=f"echo for incident {data.incident_id} "
            f"({data.failure_family} @ {data.site_id})",
            payload={"echoed_context": data.context},
            retrieved_refs=[],
            citations=[],
            confidence=1.0,
        )


def _demo() -> None:
    import asyncio

    sample = AgentInput(
        incident_id="INC-001",
        site_id="SITE-42",
        failure_family="energy/power",
        context={"alarm": "rectifier_failure", "dc_plant_v": -47.1},
    )
    agent = EchoAgent()

    # Structural conformance to the frozen protocol -- no inheritance required.
    assert isinstance(agent, Agent), "EchoAgent must satisfy the Agent protocol"

    output = asyncio.run(agent.run(sample))
    print(output.model_dump_json(indent=2))


if __name__ == "__main__":
    _demo()
