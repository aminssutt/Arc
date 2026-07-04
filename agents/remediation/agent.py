"""Remediation agent -- cited repair procedure + safety steps.

Owner: aminssutt. Ticket: AGA.2 (#29).

Runs first in Phase 2, only after the field CONFIRMS the diagnosis. It grounds
a repair procedure in the telecom corpus via VultronRetriever and synthesizes an
**ordered, actionable procedure** plus **cited safety steps** with the pinned
Vultr model. -48V DC and battery work is hazardous, so every safety step must
carry a citation that resolves to a retrieved corpus doc -- the agent enforces
that (>= 2 cited safety steps) rather than trusting the model.

Dependencies (#24 Vultr, #25 retriever) are injected, so the agent is unit-
testable offline with fakes and needs no API key in tests.
"""

from __future__ import annotations

from typing import Any, Protocol

from contracts.agent_interface import AgentInput, AgentOutput, Citation, RetrievedRef

NAME = "remediation"
MIN_SAFETY_STEPS = 2


class RemediationError(RuntimeError):
    """Raised when the corpus cannot support a safe, cited procedure."""


# --------------------------------------------------------------------------- #
# Injected dependency protocols (duck-typed; concrete impls live in common/)
# --------------------------------------------------------------------------- #
class Retriever(Protocol):
    async def query(self, text: str, top_k: int = 5) -> list[RetrievedRef]: ...


class Vultr(Protocol):
    async def structured_json(
        self, prompt: str | list[dict[str, Any]], *, schema: dict[str, Any] | None = ...,
        max_tokens: int = ..., temperature: float = ...,
    ) -> dict[str, Any]: ...


# --------------------------------------------------------------------------- #
# Structured output schema enforced on the model
# --------------------------------------------------------------------------- #
REMEDIATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["procedure", "safety_steps", "parts_needed", "crew_skill"],
    "properties": {
        "procedure": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
            "description": "Ordered, actionable repair steps.",
        },
        "safety_steps": {
            "type": "array",
            "minItems": MIN_SAFETY_STEPS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["step", "doc_id"],
                "properties": {
                    "step": {"type": "string"},
                    "doc_id": {"type": "string", "description": "must match a retrieved ref"},
                    "section": {"type": "string"},
                },
            },
        },
        "parts_needed": {"type": "array", "items": {"type": "string"}},
        "crew_skill": {"type": "string"},
    },
}

_DEFAULT_PERSONA = (
    "You are the Remediation agent. Produce an ordered, actionable repair "
    "procedure and safety steps, each safety step grounded in the provided "
    "sources. Never invent a safety step without a source."
)


def _persona() -> str:
    try:
        from agents.orchestration.personas import load_persona

        return load_persona(NAME)
    except Exception:
        return _DEFAULT_PERSONA


def _confirmed_cause(context: dict[str, Any]) -> dict[str, Any]:
    """Pull the confirmed top cause from accumulated findings (or context)."""
    findings = context.get("findings", {})
    rc = findings.get("root_cause", {})
    cause = rc.get("top_cause") or context.get("top_cause")
    if not cause:
        raise RemediationError(
            "no confirmed cause: expected context['findings']['root_cause']['top_cause']"
        )
    return cause


def _render_refs(refs: list[RetrievedRef]) -> str:
    lines = []
    for r in refs:
        lines.append(f"- [{r.doc_id} §{r.section}] {r.snippet}".strip())
    return "\n".join(lines)


def _build_prompt(cause: dict[str, Any], proc_refs: list[RetrievedRef],
                  safety_refs: list[RetrievedRef]) -> list[dict[str, str]]:
    label = cause.get("label") or cause.get("cause") or "the confirmed fault"
    user = (
        f"Confirmed root cause: {label}.\n\n"
        f"PROCEDURE SOURCES:\n{_render_refs(proc_refs)}\n\n"
        f"SAFETY SOURCES (cite these by doc_id):\n{_render_refs(safety_refs)}\n\n"
        "Return the ordered procedure and at least "
        f"{MIN_SAFETY_STEPS} safety steps, each citing a doc_id from the SAFETY "
        "SOURCES above. Name the exact part(s) the repair needs."
    )
    return [
        {"role": "system", "content": _persona()},
        {"role": "user", "content": user},
    ]


class RemediationAgent:
    """Grounded, cited remediation for a confirmed fault (Phase 2, step 1)."""

    name = NAME

    def __init__(self, vultr: Vultr, retriever: Retriever, *, top_k: int = 5) -> None:
        self._vultr = vultr
        self._retriever = retriever
        self._top_k = top_k

    async def run(self, data: AgentInput) -> AgentOutput:
        cause = _confirmed_cause(data.context)
        label = cause.get("label") or cause.get("cause") or data.failure_family

        # Two targeted retrievals: repair procedure and safety.
        proc_refs = await self._retriever.query(
            f"{label} corrective repair procedure", top_k=self._top_k
        )
        safety_refs = await self._retriever.query(
            f"{data.failure_family} power plant servicing safety lockout tagout PPE",
            top_k=self._top_k,
        )
        refs = proc_refs + safety_refs
        if not safety_refs:
            raise RemediationError("no safety documentation retrieved; refusing to emit a procedure")

        result = await self._vultr.structured_json(
            _build_prompt(cause, proc_refs, safety_refs),
            schema=REMEDIATION_SCHEMA,
            max_tokens=900,
        )

        # Grounding guard: keep only safety steps whose doc_id resolves to a
        # retrieved ref -- the model may not be trusted to cite honestly.
        retrieved_by_id = {r.doc_id: r for r in refs}
        cited_safety: list[dict[str, Any]] = []
        citations: list[Citation] = []
        seen: set[tuple[str, str | None]] = set()
        for step in result.get("safety_steps", []):
            doc_id = step.get("doc_id")
            ref = retrieved_by_id.get(doc_id)
            if ref is None:
                continue  # drop uncited/hallucinated citation
            section = step.get("section") or ref.section
            cited_safety.append({"step": step["step"], "doc_id": doc_id, "section": section})
            key = (doc_id, section)
            if key not in seen:
                seen.add(key)
                citations.append(Citation(doc_id=doc_id, section=section))

        if len(cited_safety) < MIN_SAFETY_STEPS:
            raise RemediationError(
                f"only {len(cited_safety)} grounded safety step(s); "
                f"need >= {MIN_SAFETY_STEPS} that resolve to retrieved corpus docs"
            )

        procedure = [s for s in result.get("procedure", []) if s.strip()]
        parts = result.get("parts_needed", [])
        crew_skill = result.get("crew_skill", "")

        payload = {
            "confirmed_cause": label,
            "procedure": procedure,
            "safety_steps": cited_safety,
            "parts_needed": parts,
            "crew_skill": crew_skill,
        }
        summary = (
            f"Remediation for {label}: {len(procedure)}-step procedure, "
            f"{len(cited_safety)} cited safety steps; parts: {', '.join(parts) or 'none'}."
        )
        # Confidence: full when both procedure + safety grounded and parts named.
        confidence = 0.85 if (procedure and parts) else 0.7

        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=summary,
            payload=payload,
            retrieved_refs=refs,
            citations=citations,
            confidence=confidence,
        )
