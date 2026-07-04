"""Adapter wiring aminssutt's REAL Validation agent (AGA.1, /agents/validation)
into the orchestrator registry — replacing the dummy under the same key.

The real agent consumes a documented context slice:
    context = {"top_cause": {failure_id, label, signature{metric, unit,
               abnormal_when, threshold, citation}}, "validation_event": <POST body>}
and returns payload {"decision": "confirmed"|"contradicted", "rationale", ...}.

This adapter (backend lane — /agents untouched):
  1. builds `top_cause` from the incident: the load-bearing failure is the one
     Root-Cause asked to verify (verification_requests[0]); its measurement
     signature comes from the alarm dictionary seed — same data that fired the
     Watchdog, so detection and validation share one source of truth;
  2. passes the original POST /api/validation body straight through;
  3. translates the agent's decision dialect to the frozen event contract:
     "contradicted" -> validation_result.result "pivot", plus a contradictions
     list built from telemetry vs field measurement.
"""
from typing import Any

from contracts import Agent, AgentInput, AgentOutput

from agents.validation import ValidationAgent

from backend.app.seeds import Seeds


class ValidationAgentAdapter:
    name = "validation"

    def __init__(self, seeds: Seeds, inner: Agent | None = None) -> None:
        self._seeds = seeds
        self._inner: Agent = inner or ValidationAgent()

    _SEVERITY_RANK = {"critical": 0, "major": 1, "minor": 2, "warning": 3}

    def _load_bearing_failure(self, ctx: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        failures: list[dict] = ctx.get("failures", [])
        vreqs = (ctx.get("diagnostic") or {}).get("verification_requests", [])
        if vreqs:  # Root-Cause said what to verify — trust it
            failure_id = vreqs[0]["failure_id"]
        elif failures:  # fallback: highest-severity failure carries the diagnosis
            failure_id = min(failures, key=lambda f: self._SEVERITY_RANK.get(f.get("severity"), 9))["id"]
        else:
            failure_id = "F1"
        failure = next((f for f in failures if f["id"] == failure_id),
                       failures[0] if failures else {})
        return failure_id, failure

    def _signature(self, failure: dict[str, Any]) -> dict[str, Any]:
        # Canonical chain (schema §1.1): failure.alarm_code, else raw trap via
        # trap_map, else the code itself (legacy canonical-code callers).
        code = failure.get("code", "")
        alarm_code = (failure.get("alarm_code")
                      or self._seeds.trap_map.get(code, {}).get("alarm_code")
                      or code)
        rule = self._seeds.alarm_dictionary.get(alarm_code)
        if not rule:
            return {}  # agent falls back to verdict-only fusion — still decides
        op, threshold = rule["threshold_op"], rule["threshold_value"]
        from backend.app.seeds import SIGNED_METRICS
        if rule["signal"] in SIGNED_METRICS:
            # Dictionary thresholds are MAGNITUDES; field measurements are signed
            # negatives. |v| < t  <=>  v > -t  (and mirrored for the other ops).
            op = {"lt": "gt", "lte": "gte", "gt": "lt", "gte": "lte"}.get(op, op)
            threshold = -threshold
        return {
            "metric": rule["signal"],
            "unit": rule["unit"],
            "abnormal_when": op,
            "threshold": threshold,
            "citation": {"doc_id": "data/alarm_dictionary", "section": alarm_code},
        }

    async def run(self, data: AgentInput) -> AgentOutput:
        ctx = data.context
        failure_id, failure = self._load_bearing_failure(ctx)
        causes = (ctx.get("diagnostic") or {}).get("causes", [])
        inner_input = AgentInput(
            incident_id=data.incident_id,
            site_id=data.site_id,
            failure_family=data.failure_family,
            context={
                "top_cause": {
                    "failure_id": failure_id,
                    "label": causes[0]["cause"] if causes else failure.get("code", failure_id),
                    "signature": self._signature(failure),
                },
                "validation_event": ctx.get("validation_event") or {
                    "validations": ctx.get("validations", []),
                    "measurements": ctx.get("measurements", []),
                },
            },
        )
        out = await self._inner.run(inner_input)

        decision = out.payload.get("decision", "confirmed")
        result = "pivot" if decision == "contradicted" else "confirmed"
        contradictions: list[dict[str, Any]] = []
        if result == "pivot":
            m = out.payload.get("measurement") or {}
            c: dict[str, Any] = {"failure_id": out.payload.get("matched_failure_id", failure_id)}
            if failure.get("value") is not None:
                c["telemetry"] = failure["value"]
            if m.get("value") is not None:
                c["measured"] = m["value"]
            if m.get("unit"):
                c["unit"] = m["unit"]
            contradictions.append(c)

        return AgentOutput(
            incident_id=out.incident_id,
            agent=self.name,
            summary=out.summary,
            payload={
                **out.payload,
                "result": result,
                "rationale": out.payload.get("rationale", out.summary),
                "contradictions": contradictions,
            },
            retrieved_refs=out.retrieved_refs,
            citations=out.citations,
            confidence=out.confidence,
        )
