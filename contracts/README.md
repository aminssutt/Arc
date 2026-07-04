# Arc — frozen agent & tool contracts

`agent_interface.py` is the **FROZEN** interface every agent and the
orchestrator import (issue #7 / P0.7). Change after phase 0 = PR + producer
**and** consumers approve (per `docs/ROADMAP.md`, no-conflict rules).

> Requires Python ≥ 3.12 — see root README / `.python-version`.

## What's frozen here
- `AgentInput` / `AgentOutput` — the agent I/O envelope. `AgentOutput` carries
  the `retrieved_refs`, the `citations` trail, and a `confidence` score, and is
  JSON-serializable so it can transit the SSE event stream.
- `Agent` — an async `typing.Protocol` (`runtime_checkable`); implement it
  **without inheritance**.
- `Tool` — a generic async tool protocol (`name`, `input_schema`, async call).
- `RetrievedRef` / `Citation` — evidence pool and the full citation trail.

## What's DRAFT
The three concrete tool signatures — `CostQuery→CostReport`,
`InventoryQuery→InventoryMatch`, `DispatchRequest→DispatchBooking` — are
**DRAFT, to be approved by simerugby via PR review** (backend owns the tool
APIs). Field sets may change; the generic `Tool` protocol does not.

`contracts/events*` (event schema, push payload, validation event) belong to
issue #6 / P0.6 (simerugby) and are **not** defined in this file.

## Implement a conforming agent

No base class. Provide a `name` attribute and an async `run`:

```python
from contracts import Agent, AgentInput, AgentOutput, Citation, RetrievedRef

class RootCauseAgent:
    name = "root_cause"

    async def run(self, data: AgentInput) -> AgentOutput:
        refs = await retriever.query(data.failure_family)          # your retrieval
        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary="Most likely cause: rectifier failure.",
            payload={"ranked_causes": [...]},
            retrieved_refs=[RetrievedRef(doc_id=r.id, section=r.section,
                                         snippet=r.text, score=r.score) for r in refs],
            citations=[Citation(doc_id="ran-manual", section="4.2")],
            confidence=0.82,   # a low value should trigger a re-query
        )

# structural conformance, verified at runtime:
assert isinstance(RootCauseAgent(), Agent)
```

See `echo_agent.py` for the minimal reference implementation.

## Run the reference agent

```bash
python -m venv .venv && source .venv/bin/activate      # from repo root
pip install -r contracts/requirements.txt
python -m contracts.echo_agent                          # prints a sample AgentOutput as JSON
```
