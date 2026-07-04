"""Adapter wiring vgtray's REAL Root-Cause agent (AGV.4, /agents/root_cause)
into the orchestrator registry — replacing the dummy under the same key (INT.1).

The real agent runs a confidence-gated, multi-pass retrieval loop and emits
``payload["ranked_causes"]`` (each ``{cause, confidence, citations, expected_measurement}``),
``payload["retrieval_passes"]`` and ``payload["doc_request"]``. The orchestrator
consumes ``payload["diagnostic"] = {causes, urgency, verification_requests}`` and
``payload["retrievals"]`` (emitted as ``retrieval_performed`` events). This
adapter translates the shapes and derives the verification request the human
loop needs from the top cause's expected measurement.

Root-Cause REQUIRES an injected Vultr client + retriever (it cannot run offline);
in tests these are fakes, in prod the shared VultrClient / VultronRetriever.
Backend lane — ``/agents`` is untouched.
"""
from typing import Any

from contracts import AgentInput, AgentOutput

from agents.root_cause.agent import RootCauseAgent


class RootCauseAgentAdapter:
    name = "root_cause"

    def __init__(self, vultr: Any, retriever: Any) -> None:
        # No system_prompt override: the agent uses its own tuned prompt.md.
        self._inner = RootCauseAgent(vultr, retriever)

    async def run(self, data: AgentInput) -> AgentOutput:
        out = await self._inner.run(data)
        p = out.payload
        raw_causes = p.get("ranked_causes", [])

        causes: list[dict[str, Any]] = []
        for i, c in enumerate(raw_causes, start=1):
            entry: dict[str, Any] = {
                "rank": i,
                "cause": c.get("cause", ""),
                "confidence": c.get("confidence", 0.0),
                "citations": [
                    {"doc_id": cit.get("doc_id", ""), "claim": cit.get("section") or cit.get("snippet") or ""}
                    for cit in c.get("citations", [])
                ],
            }
            if c.get("uncited"):
                entry["rejected_because"] = "no corpus evidence could ground this cause"
            causes.append(entry)

        # Verification request for the human loop, from the top cause's measurement.
        failures = data.context.get("failures", [])
        failure_id = failures[0]["id"] if failures else "F1"
        correlation = data.context.get("correlation", {})
        point = (correlation.get("equipment") or [""])[0]
        top = raw_causes[0] if raw_causes else {}
        verification_requests: list[dict[str, Any]] = []
        if top.get("expected_measurement"):
            verification_requests = [{
                "failure_id": failure_id,
                "action": "physically verify at the measurement point",
                "metric": top["expected_measurement"],
                "point": point,
            }]

        diagnostic: dict[str, Any] = {"causes": causes, "verification_requests": verification_requests}
        if p.get("doc_request"):
            diagnostic["doc_request"] = p["doc_request"]

        # retrieval_passes -> retrievals (per-pass results from the evidence pool).
        retrievals: list[dict[str, Any]] = []
        refs = out.retrieved_refs
        cursor = 0
        for pass_ in p.get("retrieval_passes", []):
            n = pass_.get("refs_count", 0) or 0
            chunk = refs[cursor:cursor + n]
            cursor += n
            retrievals.append({
                "pass": pass_.get("pass_number", len(retrievals) + 1),
                "query": pass_.get("query", ""),
                "results": [
                    {"doc_id": r.doc_id, "title": r.section or r.doc_id, "score": r.score if r.score is not None else 0.0}
                    for r in chunk
                ],
            })

        return AgentOutput(
            incident_id=out.incident_id,
            agent=self.name,
            summary=out.summary,
            payload={"diagnostic": diagnostic, "retrievals": retrievals},
            retrieved_refs=out.retrieved_refs,
            citations=out.citations,
            confidence=out.confidence,
        )
