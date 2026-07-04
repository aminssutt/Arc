"""Responder-matching agent -- match a diagnosed fault to the best employees.

Owner: aminssutt. Feature: employee-matching.

Runs after Root-Cause (it needs the family + equipment + cause). It reads the
diagnosed fault from ``AgentInput`` + context, ranks the roster with the
deterministic matcher, and returns the top 2-3 **available** responders plus the
notification decision (``payload["notify"]`` = the employee ids to push to).

Conforms to the frozen ``contracts.Agent`` protocol, so it drops into the
orchestrator registry like every other agent; its ``payload`` rides the existing
``agent_completed`` event (no new frozen event needed to surface the match).

Optional semantic re-rank: inject ``semantic_scorer`` -- an async callable
``(fault_text, [employee_text]) -> [float in 0..1]`` (e.g. backed by Vultr
embeddings) -- to blend a similarity signal on top of the deterministic score.
Left ``None`` (default) the agent is fully deterministic and offline.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Awaitable, Callable, Protocol

from contracts.agent_interface import AgentInput, AgentOutput

from agents.responder_matching.matcher import REFERENCE_DATE, match_responders

NAME = "responder_matching"
MAX_NOTIFY = 3

_DEFAULT_ROSTER = pathlib.Path(__file__).resolve().parents[2] / "data" / "employees.json"


class SemanticScorer(Protocol):
    async def __call__(self, fault_text: str, employee_texts: list[str]) -> list[float]: ...


def _employee_text(r: dict[str, Any]) -> str:
    return f"{r.get('name', '')} — {r.get('role', '')}; {r.get('reason', '')}"


def _fault_text(fault: dict[str, Any]) -> str:
    return f"{fault.get('family', '')} / {fault.get('equipment_class', '')} / {fault.get('code', '')}"


def fault_from_context(data: AgentInput) -> dict[str, Any]:
    """Assemble the fault features the matcher needs from the agent envelope.

    Accepts an explicit ``context['fault']`` (tests / direct calls) or derives
    it from the upstream findings: correlation's equipment class + the primary
    failure's alarm code.
    """
    ctx = data.context or {}
    if isinstance(ctx.get("fault"), dict):
        base = dict(ctx["fault"])
        base.setdefault("family", data.failure_family)
        return base

    findings = ctx.get("findings", {})
    correlation = findings.get("correlation") or ctx.get("correlation") or {}
    equipment_class = correlation.get("equipment_class")

    failures = ctx.get("failures") or (ctx.get("fault_event") or {}).get("failures") or []
    code = failures[0].get("code") if failures else ctx.get("code")
    if equipment_class is None and failures:
        equipment_class = failures[0].get("equipment_class")

    return {"family": data.failure_family, "equipment_class": equipment_class, "code": code}


class ResponderMatchingAgent:
    """Match a diagnosed fault to the best available responders (post Root-Cause)."""

    name = NAME

    def __init__(
        self,
        roster: list[dict[str, Any]] | None = None,
        *,
        roster_path: str | pathlib.Path | None = None,
        as_of: str = REFERENCE_DATE,
        top_k: int = MAX_NOTIFY,
        min_score: float | None = None,
        semantic_scorer: SemanticScorer | None = None,
        semantic_weight: float = 0.3,
    ) -> None:
        if roster is not None:
            self._roster = roster
        else:
            path = pathlib.Path(roster_path) if roster_path else _DEFAULT_ROSTER
            self._roster = json.loads(path.read_text(encoding="utf-8"))
        self._as_of = as_of
        self._top_k = top_k
        self._min_score = min_score
        self._semantic = semantic_scorer
        self._semantic_weight = semantic_weight

    async def run(self, data: AgentInput) -> AgentOutput:
        fault = fault_from_context(data)

        kwargs: dict[str, Any] = {"as_of": self._as_of, "top_k": max(self._top_k, MAX_NOTIFY)}
        if self._min_score is not None:
            kwargs["min_score"] = self._min_score
        responders = match_responders(self._roster, fault, **kwargs)

        if self._semantic is not None and responders:
            responders = await self._rerank(fault, responders)

        responders = responders[: self._top_k]
        notify = [r["employee_id"] for r in responders]

        if responders:
            names = ", ".join(f"{r['name']} ({r['score']:.2f})" for r in responders)
            summary = f"{len(responders)} responder(s) matched for {_fault_text(fault)}: {names}"
            confidence = float(responders[0]["score"])
        else:
            summary = f"No confident responder for {_fault_text(fault)} — escalate to on-call lead"
            confidence = 0.0

        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=summary,
            payload={"fault": fault, "responders": responders, "notify": notify,
                     "escalate": not responders},
            retrieved_refs=[],
            citations=[],
            confidence=confidence,
        )

    async def _rerank(self, fault: dict[str, Any], responders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sims = await self._semantic(_fault_text(fault), [_employee_text(r) for r in responders])
        a = self._semantic_weight
        for r, sim in zip(responders, sims):
            r["deterministic_score"] = r["score"]
            r["semantic_score"] = round(float(sim), 4)
            r["score"] = round((1 - a) * r["score"] + a * float(sim), 4)
        responders.sort(key=lambda r: (r["score"], r["similar_fixes"], r["seniority_years"]), reverse=True)
        return responders
