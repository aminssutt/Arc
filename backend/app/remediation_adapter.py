"""Adapter wiring aminssutt's REAL Remediation agent (AGA.2, /agents/remediation)
into the orchestrator registry — replacing the dummy under the same key (INT.3).

The real agent grounds a cited procedure + safety steps in the corpus. It reads
the confirmed cause from ``context["findings"]["root_cause"]["top_cause"]`` and
emits ``{procedure: [str], safety_steps: [{step, doc_id, section}],
parts_needed: [str], crew_skill}``. The orchestrator's phase-2 code consumes a
richer procedure object (``{title, steps:[{n,text,citations}], safety:[{text,
citations}]}``) plus ``parts`` and ``action_hints``, so this adapter bridges the
input (diagnostic -> top_cause) and translates the output.

Requires the shared Vultr client + retriever (fakes in tests). Backend lane —
``/agents`` is untouched.
"""
from typing import Any

from contracts import AgentInput, AgentOutput

from agents.remediation import RemediationAgent, RemediationError


class RemediationAgentAdapter:
    name = "remediation"

    def __init__(self, vultr: Any, retriever: Any) -> None:
        self._inner = RemediationAgent(vultr, retriever)

    async def run(self, data: AgentInput) -> AgentOutput:
        diagnostic = data.context.get("diagnostic", {})
        causes = diagnostic.get("causes", [])
        top_cause = {"label": causes[0]["cause"]} if causes else {"label": data.failure_family}

        inner_input = AgentInput(
            incident_id=data.incident_id,
            site_id=data.site_id,
            failure_family=data.failure_family,
            context={"findings": {"root_cause": {"top_cause": top_cause}}},
        )
        try:
            out = await self._inner.run(inner_input)
        except RemediationError:
            # Corpus can't support a safe cited procedure — surface as a graceful
            # empty remediation; the orchestrator emits a normal (thin) report
            # rather than crashing the run.
            return AgentOutput(
                incident_id=data.incident_id, agent=self.name,
                summary="remediation unavailable: corpus lacks a cited safe procedure",
                payload={"procedure": {"title": top_cause["label"], "steps": [], "safety": []},
                         "parts": [], "action_hints": []},
                retrieved_refs=[], citations=[], confidence=0.2,
            )

        p = out.payload
        procedure = {
            "title": p.get("confirmed_cause") or out.summary,
            "steps": [{"n": i, "text": step, "citations": []}
                      for i, step in enumerate(p.get("procedure", []), start=1)],
            "safety": [{"text": s["step"],
                        "citations": [{"doc_id": s["doc_id"], "claim": s.get("section", "")}]}
                       for s in p.get("safety_steps", [])],
        }
        parts = [{"part_no": pn, "description": "", "qty": 1} for pn in p.get("parts_needed", [])]
        first_step = procedure["steps"][0]["text"] if procedure["steps"] else procedure["title"]
        action_hints = [{"priority": "P1", "action": first_step}]

        return AgentOutput(
            incident_id=out.incident_id,
            agent=self.name,
            summary=out.summary,
            payload={"procedure": procedure, "parts": parts, "action_hints": action_hints},
            retrieved_refs=out.retrieved_refs,
            citations=out.citations,
            confidence=out.confidence,
        )
