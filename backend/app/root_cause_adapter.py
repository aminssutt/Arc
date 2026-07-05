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
        correlation = data.context.get("correlation", {})
        point = (correlation.get("equipment") or [""])[0]
        top = raw_causes[0] if raw_causes else {}
        verification_requests: list[dict[str, Any]] = []
        expected = top.get("expected_measurement")
        if expected:
            # Direct the verification at the failure carrying the discriminating
            # numeric telemetry (e.g. busbar dc_voltage) and use ITS metric/point,
            # so the technician measures the quantity that can actually contradict
            # the alarm — the pitch's "test at the site" beat.
            vf = self._verification_failure(failures, expected)
            verification_requests = [{
                "failure_id": vf.get("id", "F1"),
                "action": "physically verify at the measurement point",
                "metric": vf.get("metric") or expected,
                "point": vf.get("equipment") or point,
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
                "results": [self._result_ref(r) for r in chunk],
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

    # Continuous quantities a technician reads with an instrument (voltage /
    # current / temperature / ratio) vs boolean status signals stored as 0/1
    # (module_status, mains_present, cell_active, backhaul_up) — which are numeric
    # but are NOT a field measurement, so they must never win the verification.
    _CONTINUOUS = ("voltage", "_v", "current", "_a", "temp", "_c", "ratio", "pct", "loss", "autonomy", "_min")
    _BOOLEANISH = ("status", "present", "active", "_up")

    @classmethod
    def _verification_failure(cls, failures: list[dict[str, Any]], expected: str) -> dict[str, Any]:
        """The failure carrying the discriminating CONTINUOUS telemetry to measure
        (busbar dc_voltage), so the field check can contradict the alarm. Prefer a
        metric-name match, then a continuous measurable metric (never a boolean
        status signal encoded as 0/1), then any non-boolean numeric, else first."""
        if not failures:
            return {"id": "F1"}
        exp = (expected or "").lower()
        for f in failures:
            fm = str(f.get("metric") or "").lower()
            if fm and (fm == exp or fm in exp or exp in fm):
                return f
        for f in failures:
            fm = str(f.get("metric") or "").lower()
            if fm and any(k in fm for k in cls._CONTINUOUS) and not any(b in fm for b in cls._BOOLEANISH):
                return f
        for f in failures:
            fm = str(f.get("metric") or "").lower()
            v = f.get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool) and not any(b in fm for b in cls._BOOLEANISH):
                return f
        return failures[0]

    @staticmethod
    def _result_ref(r: Any) -> dict[str, Any]:
        # Surface the real retrieval score when the retriever provides one; the
        # text VultronRetriever exposes none, so omit the field (schema-optional)
        # rather than emit a misleading 0.0.
        res: dict[str, Any] = {"doc_id": r.doc_id, "title": r.section or r.doc_id}
        if r.score is not None:
            res["score"] = r.score
        return res
