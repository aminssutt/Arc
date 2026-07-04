"""Responder-matching agent -- route a diagnosed fault to ONE employee.

Owner: aminssutt. Feature: employee-matching.

Runs after Root-Cause (it needs family + equipment + cause + difficulty). It
reads the diagnosed fault + the site's region from the envelope, picks the single
best responder with the deterministic matcher (difficulty-routed, zone-preferred),
and returns the notification decision (``payload["notify"]`` = the one employee id).

Conforms to the frozen ``contracts.Agent`` protocol, so it drops into the
orchestrator registry like every other agent; its ``payload`` rides the existing
``agent_completed`` event (no new frozen event needed to surface the match).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

from contracts.agent_interface import AgentInput, AgentOutput

from agents.responder_matching.matcher import (
    REFERENCE_DATE,
    fault_difficulty,
    match_responder,
    rank_candidates,
)

NAME = "responder_matching"

_DEFAULT_ROSTER = pathlib.Path(__file__).resolve().parents[2] / "data" / "employees.json"


def _fault_text(fault: dict[str, Any]) -> str:
    return (f"{fault.get('family', '')} / {fault.get('equipment_class', '')} / "
            f"{fault.get('code', '')} [{fault_difficulty(fault)}] @ {fault.get('region', '?')}")


def fault_from_context(data: AgentInput) -> dict[str, Any]:
    """Assemble the fault features (incl. difficulty + site region) the matcher needs.

    Accepts an explicit ``context['fault']`` (tests / direct calls) or derives it
    from upstream findings: correlation's equipment class, the primary failure's
    alarm code, an optional explicit difficulty, and the site's region.
    """
    ctx = data.context or {}
    if isinstance(ctx.get("fault"), dict):
        base = dict(ctx["fault"])
        base.setdefault("family", data.failure_family)
        base.setdefault("region", ctx.get("site", {}).get("region"))
        return base

    findings = ctx.get("findings", {})
    correlation = findings.get("correlation") or ctx.get("correlation") or {}
    failures = ctx.get("failures") or (ctx.get("fault_event") or {}).get("failures") or []
    primary = failures[0] if failures else {}

    return {
        "family": data.failure_family,
        "equipment_class": correlation.get("equipment_class") or primary.get("equipment_class"),
        # canonical alarm_code first (matcher keys on it); raw trap only as fallback.
        "code": primary.get("alarm_code") or primary.get("code") or ctx.get("code"),
        "difficulty": ctx.get("difficulty") or primary.get("difficulty"),
        "region": ctx.get("region") or ctx.get("site", {}).get("region") or correlation.get("region"),
    }


class ResponderMatchingAgent:
    """Route a diagnosed fault to ONE responder (post Root-Cause)."""

    name = NAME

    def __init__(
        self,
        roster: list[dict[str, Any]] | None = None,
        *,
        roster_path: str | pathlib.Path | None = None,
        as_of: str = REFERENCE_DATE,
    ) -> None:
        if roster is not None:
            self._roster = roster
        else:
            path = pathlib.Path(roster_path) if roster_path else _DEFAULT_ROSTER
            self._roster = json.loads(path.read_text(encoding="utf-8"))
        self._as_of = as_of

    async def run(self, data: AgentInput) -> AgentOutput:
        fault = fault_from_context(data)
        chosen = match_responder(self._roster, fault, as_of=self._as_of)
        # Alternatives (transparency / fallback if the notified person declines).
        alternatives = [c for c in rank_candidates(self._roster, fault, as_of=self._as_of)
                        if not chosen or c["employee_id"] != chosen["employee_id"]][:3]

        if chosen is not None:
            zone = "hors-zone (aucun dispo en zone)" if chosen.get("out_of_zone") else "en zone"
            summary = (f"Notify {chosen['name']} ({chosen['employee_id']}, {chosen['tier']}, {zone}) "
                       f"for {_fault_text(fault)} — {chosen['reason']}")
            notify = [chosen["employee_id"]]
            confidence = float(chosen["score"])
        else:
            summary = f"No eligible available responder for {_fault_text(fault)} — escalate to on-call lead"
            notify = []
            confidence = 0.0

        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=summary,
            payload={
                "fault": fault,
                "difficulty": fault_difficulty(fault),
                "responder": chosen,
                "notify": notify,
                "out_of_zone": bool(chosen and chosen.get("out_of_zone")),
                "escalate": chosen is None,
                "alternatives": alternatives,
            },
            retrieved_refs=[],
            citations=[],
            confidence=confidence,
        )
