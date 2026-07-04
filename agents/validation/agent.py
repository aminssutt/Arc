"""Validation agent -- confirm or PIVOT the Phase-1 diagnosis against the field.

Owner: aminssutt. Ticket: AGA.1 (#28).

The human loop sits between Phase 1 (Correlation -> Root-Cause) and Phase 2
(Remediation -> Cost/Inventory/Dispatch). A field technician physically tests
the site and reports, per detected failure, a real/false verdict plus the real
measurement. This agent fuses that human ground truth with the top cause's
*signature* and returns one of two decisions:

- ``confirmed``   -> the diagnosis holds; the orchestrator proceeds to Phase 2.
- ``contradicted`` -> the field disagrees; the agent emits a **pivot request**
  so the orchestrator re-runs Root-Cause with the measurement pinned as ground
  truth (the "telemetry lied" demo beat).

Design choice: the match is **deterministic** (measurement vs. a numeric
envelope + verdict fusion). No LLM call is needed to decide confirm/pivot, so
this agent is demo-able standalone against fixtures and does not depend on the
shared Vultr client (#24). Any prose polish can be layered later without
changing the decision.

Contract surface consumed from ``AgentInput.context`` (shape owned by the event
contract, issue #6 -- documented here as the orchestrator<->validation slice):

    context = {
        "top_cause": {
            "failure_id": "F2",                 # load-bearing failure for the top cause
            "label": "DC undervoltage (rectifier module failure)",
            "signature": {                      # how the field measurement should read IF real
                "metric": "dc_voltage_v",
                "point": "busbar",
                "unit": "V",
                "abnormal_when": "gte",         # gte|lte|gt|lt|outside_envelope
                "threshold": -47.0,
                "normal_envelope": [-57.0, -40.5],
                "citation": {"doc_id": "etsi-en-300-132-2", "section": "-48V DC envelope"},
            },
        },
        "validation_event": { ... },            # frozen validation_event.schema.json (POST /api/validation body)
    }
"""

from __future__ import annotations

from typing import Any

from contracts.agent_interface import AgentInput, AgentOutput, Citation

NAME = "validation"


# --------------------------------------------------------------------------- #
# Signature evaluation (pure, unit-testable)
# --------------------------------------------------------------------------- #
def _measurement_supports_fault(signature: dict[str, Any], value: float) -> bool:
    """True when a numeric measurement is consistent with the diagnosed fault.

    Voltages here are negative (-48 V plant): a DC undervoltage sags the busbar
    *up* toward the load-voltage disconnect (e.g. -54 V float -> -44 V), so an
    ``abnormal_when="gte"`` with threshold -47 reads "real undervoltage".
    """
    op = signature.get("abnormal_when", "outside_envelope")
    threshold = signature.get("threshold")

    if op == "gte":
        return value >= threshold
    if op == "gt":
        return value > threshold
    if op == "lte":
        return value <= threshold
    if op == "lt":
        return value < threshold
    if op == "outside_envelope":
        lo, hi = signature.get("normal_envelope", [float("-inf"), float("inf")])
        return not (lo <= value <= hi)
    raise ValueError(f"unknown abnormal_when operator: {op!r}")


def _find_verdict(validations: list[dict[str, Any]], failure_id: str) -> str | None:
    for v in validations:
        if v.get("failure_id") == failure_id:
            return v.get("verdict")
    return None


def _find_measurement(
    measurements: list[dict[str, Any]], signature: dict[str, Any]
) -> dict[str, Any] | None:
    """Match a measurement to the signature by metric (+ point when given)."""
    metric = signature.get("metric")
    point = signature.get("point")
    for m in measurements:
        if m.get("metric") != metric:
            continue
        if point is not None and m.get("point") not in (None, point):
            continue
        return m
    return None


def evaluate(top_cause: dict[str, Any], validation_event: dict[str, Any]) -> dict[str, Any]:
    """Decide confirm vs. pivot from the top cause and the technician's report.

    Physical measurement is the strongest signal: if a measurement matching the
    signature exists, it decides. A ``verdict="false"`` alone (no measurement)
    also contradicts. Returns a structured decision dict; the agent wraps it in
    an ``AgentOutput``.
    """
    failure_id = top_cause["failure_id"]
    signature = top_cause.get("signature", {})
    validations = validation_event.get("validations", [])
    measurements = validation_event.get("measurements", [])

    verdict = _find_verdict(validations, failure_id)
    measurement = _find_measurement(measurements, signature)

    supports: bool | None = None
    has_rule = "threshold" in signature or signature.get("abnormal_when") == "outside_envelope"
    if measurement is not None and has_rule:
        supports = _measurement_supports_fault(signature, float(measurement["value"]))

    # Decision: measurement is ground truth; verdict is the fallback.
    if supports is True:
        decision, confidence = "confirmed", 0.92
    elif supports is False:
        decision, confidence = "contradicted", 0.90
    elif verdict == "real":
        decision, confidence = "confirmed", 0.65   # verdict only, no measurement
    elif verdict == "false":
        decision, confidence = "contradicted", 0.70
    else:
        # nothing to go on for the load-bearing failure -> ask for verification
        decision, confidence = "contradicted", 0.40

    # A verdict that disagrees with a present measurement lowers confidence and
    # is surfaced honestly (the report states the contradiction).
    conflict = (
        supports is True and verdict == "false"
    ) or (supports is False and verdict == "real")
    if conflict:
        confidence = min(confidence, 0.72)

    return {
        "decision": decision,
        "confidence": confidence,
        "failure_id": failure_id,
        "cause_label": top_cause.get("label"),
        "verdict": verdict,
        "measurement": measurement,
        "measurement_supports_fault": supports,
        "verdict_measurement_conflict": conflict,
        "signature": signature,
    }


# --------------------------------------------------------------------------- #
# Prose + pivot payload
# --------------------------------------------------------------------------- #
def _fmt_measurement(m: dict[str, Any] | None) -> str:
    if not m:
        return "no field measurement"
    point = f" @ {m['point']}" if m.get("point") else ""
    return f"{m['metric']}{point} = {m['value']} {m.get('unit', '')}".strip()


def _summary(d: dict[str, Any]) -> str:
    label = d["cause_label"] or d["failure_id"]
    meas = _fmt_measurement(d["measurement"])
    if d["decision"] == "confirmed":
        return (
            f"Field validation CONFIRMS {label}: technician verdict={d['verdict']!r}, "
            f"{meas} within the fault envelope. Proceeding to remediation."
        )
    conflict = " (telemetry/field conflict flagged)" if d["verdict_measurement_conflict"] else ""
    return (
        f"Field validation CONTRADICTS {label}: {meas}, technician verdict={d['verdict']!r}"
        f"{conflict}. PIVOT: re-diagnose with the measurement as ground truth."
    )


def _pivot_request(d: dict[str, Any], incident_id: str) -> dict[str, Any]:
    return {
        "incident_id": incident_id,
        "reject_cause": d["cause_label"],
        "reject_failure_id": d["failure_id"],
        "reason": "field measurement contradicts the telemetry-derived diagnosis",
        "ground_truth": d["measurement"],
        "instruction": (
            "re-run root-cause with the field measurement pinned as ground truth; "
            "demote the rejected cause to planned maintenance"
        ),
    }


# --------------------------------------------------------------------------- #
# Agent (structurally satisfies contracts.Agent -- no base class)
# --------------------------------------------------------------------------- #
class ValidationAgent:
    """Confirm or pivot the diagnosis from the technician's field report."""

    name = NAME

    async def run(self, data: AgentInput) -> AgentOutput:
        top_cause = data.context.get("top_cause")
        validation_event = data.context.get("validation_event")
        if top_cause is None or validation_event is None:
            raise ValueError(
                "validation agent needs context['top_cause'] and "
                "context['validation_event']"
            )

        d = evaluate(top_cause, validation_event)

        payload: dict[str, Any] = {
            "decision": d["decision"],
            "matched_failure_id": d["failure_id"],
            "rationale": _summary(d),
            "verdict": d["verdict"],
            "measurement": d["measurement"],
            "measurement_supports_fault": d["measurement_supports_fault"],
            "verdict_measurement_conflict": d["verdict_measurement_conflict"],
        }
        if d["decision"] == "contradicted":
            payload["pivot_request"] = _pivot_request(d, data.incident_id)

        citations: list[Citation] = []
        cite = d["signature"].get("citation")
        if cite:
            citations.append(Citation(doc_id=cite["doc_id"], section=cite.get("section")))

        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=_summary(d),
            payload=payload,
            retrieved_refs=[],
            citations=citations,
            confidence=d["confidence"],
        )


def _demo() -> None:
    import asyncio
    import json
    import pathlib

    fx = pathlib.Path(__file__).parent / "fixtures"
    for name in ("confirm_input.json", "pivot_input.json"):
        raw = json.loads((fx / name).read_text(encoding="utf-8"))
        out = asyncio.run(ValidationAgent().run(AgentInput(**raw)))
        print(f"\n# {name}")
        print(out.model_dump_json(indent=2))


if __name__ == "__main__":
    _demo()
