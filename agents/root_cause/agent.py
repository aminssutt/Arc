"""RootCauseAgent — ranked causes + confidence behind a multi-pass retrieval gate.

Issue #27 / AGV.4. The differentiator this agent proves for the Vultr bar is
*retrieval behind a confidence gate*: it retrieves once, ranks the candidate root
causes, and — only when its own confidence is below threshold — retrieves **again
with an LLM-reformulated query** before committing. If confidence is still low
after the pass budget, it stops guessing and asks for the specific document type
that would resolve it (``doc_request``).

The agent is a plain class that structurally satisfies the frozen ``Agent``
protocol (``contracts.agent_interface``): a ``name`` attribute and an async
``run(AgentInput) -> AgentOutput``. No base class.

Dependency injection
--------------------
``VultrClient`` (chat/JSON) and ``VultronRetriever`` (vector search) are injected,
so the agent runs unit-tested against fakes with no network and in production
against the shared, pinned Vultr endpoint. Both are duck-typed via the minimal
``_VultrLike`` / ``_RetrieverLike`` protocols below — anything exposing the two
awaited methods works.

payload contract (consumed by the orchestrator + Validation agent)
------------------------------------------------------------------
``AgentOutput.payload`` is::

    {
      "ranked_causes": [
        {"cause", "confidence", "citations": [Citation, ...], "expected_measurement"}
      ],
      "retrieval_passes": [{"pass_number", "query", "refs_count"}],
      "doc_request": null | {"agent", "description", "query", "status": "missing"}
    }

Invariants the consumers rely on:

* **Every ranked cause carries >= 1 citation** whenever any evidence was
  retrieved (structurally enforced here, not left to the LLM: a cause with no
  valid model-supplied citation falls back to the most relevant retrieved ref).
  Degenerate case -- if retrieval returned **no evidence at all**, causes cannot
  be cited: each is flagged ``"uncited": true`` with confidence floored to 0.0,
  and a ``doc_request`` is emitted. Zero citable evidence *is* a missing doc, so
  an ungrounded hypothesis never presents as a cited, confident fact.
* ``AgentOutput.retrieved_refs`` is the full evidence pool **in pass order**
  (pass-1 refs, then pass-2 refs, ...). Combined with each pass's ``refs_count``
  this lets the orchestrator slice the pool per pass and emit one
  ``retrieval_performed`` event per pass (``pass`` number = compliance proof;
  see ``contracts/EVENTS.md`` event #5).
* ``doc_request`` matches the ``doc_requested`` event shape (event #13):
  ``{agent, description, query, status}``.
* ``expected_measurement`` is drawn from the alarm-dictionary measurement
  vocabulary (``data/schema.md`` section 1) — the field the Validation agent
  compares the technician's reading against.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Protocol, runtime_checkable

from contracts.agent_interface import AgentInput, AgentOutput, Citation, RetrievedRef

__all__ = [
    "RootCauseAgent",
    "GateConfig",
    "CANONICAL_MEASUREMENTS",
    "DEFAULT_CONFIDENCE_THRESHOLD",
]

logger = logging.getLogger("arc.root_cause")

_PROMPT_PATH = Path(__file__).with_name("prompt.md")

DEFAULT_CONFIDENCE_THRESHOLD = 0.7
DEFAULT_TOP_K = 5
DEFAULT_MAX_PASSES = 2
DEFAULT_MAX_TOKENS = 600
_SNIPPET_CHARS = 500  # evidence chunk length shown to the model, per ref

# Canonical measurement signals — data/schema.md section 1 (expected_measurement
# column of the alarm dictionary). The Validation agent matches the technician's
# reading against the field of this name, so causes must speak this vocabulary.
CANONICAL_MEASUREMENTS = (
    "dc_plant_voltage_v",
    "mains_voltage_v",
    "rectifier_output_a",
    "battery_voltage_v",
    "cabinet_temp_c",
    "radio_temp_c",
    "vswr_ratio",
    "cell_active",
    "backhaul_up",
    "backhaul_loss_pct",
)
_MEASUREMENT_LOOKUP = {m.lower(): m for m in CANONICAL_MEASUREMENTS}


# --------------------------------------------------------------------------- #
# Injected dependency shapes (duck-typed; no import coupling to the concrete
# clients, which keeps the agent trivially mockable).
# --------------------------------------------------------------------------- #
@runtime_checkable
class _RetrieverLike(Protocol):
    async def query(self, text: str, top_k: int = ...) -> list[RetrievedRef]: ...


@runtime_checkable
class _VultrLike(Protocol):
    async def structured_json(
        self, prompt: str | list[dict[str, Any]], *, max_tokens: int = ..., temperature: float = ...
    ) -> dict[str, Any]: ...


@dataclass(slots=True)
class GateConfig:
    """Tunables for the confidence gate.

    ``confidence_threshold`` (default 0.7) is the bar below which the agent
    re-retrieves; ``max_passes`` (default 2) caps the retrieval budget. With the
    defaults the flow is exactly: pass 1 -> gate -> pass 2 (reformulated) -> gate
    -> doc_request if still low.
    """

    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
    top_k: int = DEFAULT_TOP_K
    max_passes: int = DEFAULT_MAX_PASSES
    max_tokens: int = DEFAULT_MAX_TOKENS


def _clamp01(value: Any) -> float:
    """Coerce to a float in ``[0, 1]``; junk (None, NaN, non-numeric) -> 0.0."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if v != v:  # NaN
        return 0.0
    return max(0.0, min(1.0, v))


def _normalize_measurement(value: Any) -> str:
    """Snap a model-supplied measurement onto the canonical vocabulary if possible.

    Exact/case-insensitive matches canonicalize; anything else is passed through
    stripped (still a string) so the field is never silently dropped.
    """
    if not isinstance(value, str):
        return ""
    stripped = value.strip()
    return _MEASUREMENT_LOOKUP.get(stripped.lower(), stripped)


class RootCauseAgent:
    """Rank root causes with a confidence-gated, multi-pass retrieval loop."""

    name = "root_cause"

    def __init__(
        self,
        vultr: _VultrLike,
        retriever: _RetrieverLike,
        *,
        config: GateConfig | None = None,
        system_prompt: str | None = None,
    ) -> None:
        if vultr is None or retriever is None:
            raise ValueError(
                "RootCauseAgent requires an injected vultr client and retriever "
                "(pass fakes in tests, the shared VultrClient/VultronRetriever in prod)."
            )
        self._vultr = vultr
        self._retriever = retriever
        self.config = config or GateConfig()
        self._system_prompt = system_prompt if system_prompt is not None else _PROMPT_PATH.read_text(encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Agent protocol entry point
    # ------------------------------------------------------------------ #
    async def run(self, data: AgentInput) -> AgentOutput:
        started = time.perf_counter()
        evidence: list[RetrievedRef] = []
        passes: list[dict[str, Any]] = []
        query = self._seed_query(data)
        ranking: dict[str, Any] = {}
        missing_doc: dict[str, Any] | None = None

        for pass_no in range(1, self.config.max_passes + 1):
            refs = await self._retriever.query(query, top_k=self.config.top_k)
            evidence.extend(refs)
            passes.append({"pass_number": pass_no, "query": query, "refs_count": len(refs)})

            ranking = await self._rank(data, evidence, pass_no)
            missing_doc = ranking.get("missing_doc") if isinstance(ranking.get("missing_doc"), dict) else None
            # Gate on GROUNDED confidence: with no evidence retrieved at all, no
            # cause can be cited, so it cannot clear the gate however confident
            # the LLM claims to be -- ungrounded certainty is the exact failure
            # the confidence bar exists to catch.
            grounded_confidence = self._top_confidence(ranking) if evidence else 0.0

            logger.info(
                "root_cause %s pass %d/%d: query=%r refs=%d grounded_confidence=%.2f",
                data.incident_id, pass_no, self.config.max_passes, query, len(refs), grounded_confidence,
            )

            if grounded_confidence >= self.config.confidence_threshold:
                break
            if pass_no < self.config.max_passes:
                query = self._reformulate(ranking, data)

        return self._build_output(data, evidence, passes, ranking, missing_doc, started)

    # ------------------------------------------------------------------ #
    # LLM ranking call
    # ------------------------------------------------------------------ #
    async def _rank(self, data: AgentInput, evidence: list[RetrievedRef], pass_no: int) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": self._build_user_message(data, evidence, pass_no)},
        ]
        try:
            return await self._vultr.structured_json(
                messages, max_tokens=self.config.max_tokens, temperature=0.0
            )
        except Exception as exc:  # noqa: BLE001 - degrade to low-confidence, don't crash the pipeline
            logger.warning("root_cause %s ranking call failed on pass %d: %s", data.incident_id, pass_no, exc)
            return {"ranked_causes": [], "followup_query": "", "missing_doc": None}

    def _build_user_message(self, data: AgentInput, evidence: list[RetrievedRef], pass_no: int) -> str:
        lines = [
            f"INCIDENT {data.incident_id} — retrieval pass {pass_no} of up to {self.config.max_passes}.",
            f"Site: {data.site_id}",
            f"Failure family: {data.failure_family}",
        ]
        fault_lines = self._describe_fault(data)
        if fault_lines:
            lines.append("Fault / upstream correlation:")
            lines.extend(f"  - {ln}" for ln in fault_lines)

        if pass_no > 1:
            lines.append(
                "This is a re-retrieval: your previous confidence was below threshold. "
                "The evidence below now includes the reformulated-query results — "
                "re-rank and only raise confidence if the new evidence genuinely resolves the gap."
            )

        lines.append("")
        lines.append(f"EVIDENCE ({len(evidence)} chunks, cite by [index]):")
        if evidence:
            for i, ref in enumerate(evidence):
                snippet = " ".join((ref.snippet or "").split())[:_SNIPPET_CHARS]
                doc = ref.doc_id or "unknown-doc"
                section = f" §{ref.section}" if ref.section else ""
                lines.append(f"[{i}] {doc}{section}: {snippet}")
        else:
            lines.append("(no evidence retrieved — you cannot ground any cause; report missing_doc.)")

        lines.append("")
        lines.append(
            "Return the JSON object defined in the system prompt: ranked_causes "
            "(each with cause, confidence, expected_measurement, citation_refs), "
            "followup_query, missing_doc."
        )
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Gate helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _top_confidence(ranking: dict[str, Any]) -> float:
        causes = ranking.get("ranked_causes")
        if not isinstance(causes, list) or not causes:
            return 0.0
        return max((_clamp01(c.get("confidence")) for c in causes if isinstance(c, dict)), default=0.0)

    def _reformulate(self, ranking: dict[str, Any], data: AgentInput) -> str:
        """Next-pass query: the LLM's reformulation, else a widened seed fallback."""
        followup = ranking.get("followup_query")
        if isinstance(followup, str) and followup.strip():
            return followup.strip()
        # Fallback keeps the loop useful even if the model omitted a reformulation.
        return f"{data.site_id} {data.failure_family} historical incident resolution root cause"

    # ------------------------------------------------------------------ #
    # Output assembly
    # ------------------------------------------------------------------ #
    def _build_output(
        self,
        data: AgentInput,
        evidence: list[RetrievedRef],
        passes: list[dict[str, Any]],
        ranking: dict[str, Any],
        missing_doc: dict[str, Any] | None,
        started: float,
    ) -> AgentOutput:
        ranked_causes: list[dict[str, Any]] = []
        aggregate: dict[tuple[str, str, str | None], Citation] = {}
        grounded_confidences: list[float] = []
        any_uncited = False

        raw_causes = ranking.get("ranked_causes") if isinstance(ranking.get("ranked_causes"), list) else []
        for cause in raw_causes:
            if not isinstance(cause, dict):
                continue
            cites = self._citations_for(cause, evidence)
            entry: dict[str, Any] = {
                "cause": str(cause.get("cause", "")).strip(),
                "confidence": _clamp01(cause.get("confidence")),
                "citations": [c.model_dump(mode="json") for c in cites],
                "expected_measurement": _normalize_measurement(cause.get("expected_measurement")),
            }
            if cites:
                for c in cites:
                    aggregate.setdefault((c.doc_id, c.section, c.snippet), c)
                grounded_confidences.append(entry["confidence"])
            else:
                # Reachable only when NO evidence was retrieved on any pass: the
                # cause cannot be backed by the citation trail. Flag it and floor
                # its confidence so it never reads as a cited, confident fact.
                entry["confidence"] = 0.0
                entry["uncited"] = True
                any_uncited = True
            ranked_causes.append(entry)

        ranked_causes.sort(key=lambda c: c["confidence"], reverse=True)
        top_confidence = max(grounded_confidences, default=0.0)

        # doc_request is MANDATORY when nothing could be grounded (no evidence /
        # uncited causes) or grounded confidence stayed below threshold. Zero
        # citable evidence is exactly what the doc_requested event means.
        doc_request: dict[str, Any] | None = None
        if any_uncited or not evidence or top_confidence < self.config.confidence_threshold:
            doc_request = self._doc_request(data, missing_doc, passes)

        payload = {
            "ranked_causes": ranked_causes,
            "retrieval_passes": passes,
            "doc_request": doc_request,
        }

        elapsed_ms = (time.perf_counter() - started) * 1000
        has_grounded = bool(grounded_confidences)
        summary = self._summary(data, ranked_causes, passes, doc_request, top_confidence, has_grounded)
        logger.info(
            "root_cause %s done: passes=%d top_confidence=%.2f uncited=%s doc_request=%s in %.0fms",
            data.incident_id, len(passes), top_confidence, any_uncited, doc_request is not None, elapsed_ms,
        )

        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=summary,
            payload=payload,
            retrieved_refs=evidence,
            citations=list(aggregate.values()),
            confidence=top_confidence,
        )

    def _citations_for(self, cause: dict[str, Any], evidence: list[RetrievedRef]) -> list[Citation]:
        """Resolve a cause's ``citation_refs`` indices to Citation objects.

        Enforces the >= 1 citation invariant: if the model gave no valid index but
        evidence exists, the top-ranked ref is attached as the fallback citation.
        """
        idxs: list[int] = []
        for raw in cause.get("citation_refs", []) or []:
            if isinstance(raw, bool):
                continue
            if isinstance(raw, int) and 0 <= raw < len(evidence) and raw not in idxs:
                idxs.append(raw)
        if not idxs and evidence:
            idxs = [0]
        # Dedup within a cause: the corpus may surface the same (doc_id, section)
        # across passes, and one source cited twice for one claim is trail noise.
        citations: list[Citation] = []
        seen: set[tuple[str, str, str | None]] = set()
        for i in idxs:
            ref = evidence[i]
            key = (ref.doc_id, ref.section, ref.snippet or None)
            if key in seen:
                continue
            seen.add(key)
            citations.append(
                Citation(doc_id=ref.doc_id, section=ref.section, snippet=(ref.snippet or None))
            )
        return citations

    def _doc_request(
        self, data: AgentInput, missing_doc: dict[str, Any] | None, passes: list[dict[str, Any]]
    ) -> dict[str, Any]:
        md = missing_doc or {}
        description = str(md.get("description") or "").strip() or (
            f"Site-specific historical/vendor document to resolve the {data.failure_family} "
            f"root cause at {data.site_id}; retrieved corpus was insufficient after "
            f"{len(passes)} pass(es)."
        )
        last_query = passes[-1]["query"] if passes else data.failure_family
        query = str(md.get("query") or "").strip() or last_query
        return {"agent": self.name, "description": description, "query": query, "status": "missing"}

    @staticmethod
    def _summary(
        data: AgentInput,
        ranked_causes: list[dict[str, Any]],
        passes: list[dict[str, Any]],
        doc_request: dict[str, Any] | None,
        top_confidence: float,
        has_grounded: bool,
    ) -> str:
        pass_word = "pass" if len(passes) == 1 else "passes"
        if has_grounded and ranked_causes:
            head = f"top cause: {ranked_causes[0]['cause']} ({top_confidence:.2f})"
        elif ranked_causes:
            head = "no cause could be grounded in retrieved evidence (all uncited)"
        else:
            head = "no cause produced"
        tail = f"{len(passes)} retrieval {pass_word}"
        if doc_request is not None:
            tail += "; confidence below threshold — document requested"
        return f"{head} — {tail}"

    # ------------------------------------------------------------------ #
    # Context reading (AgentInput.context shape is owned by the event contract,
    # so read it defensively — extract what is there, require nothing).
    # ------------------------------------------------------------------ #
    def _seed_query(self, data: AgentInput) -> str:
        parts: list[str] = [data.failure_family, data.site_id]
        for failure in self._iter_failures(data.context):
            code = failure.get("code")
            equipment = failure.get("equipment")
            if code:
                parts.append(str(code))
            if equipment:
                parts.append(str(equipment))
        correlation = data.context.get("correlation") if isinstance(data.context, dict) else None
        if isinstance(correlation, dict):
            for equip in correlation.get("equipment", []) or []:
                parts.append(str(equip))
            if correlation.get("localized_to"):
                parts.append(str(correlation["localized_to"]))
        parts.append("root cause diagnosis")
        # dedup preserving order, drop falsy
        return " ".join(dict.fromkeys(p for p in parts if p))

    def _describe_fault(self, data: AgentInput) -> list[str]:
        lines: list[str] = []
        for failure in self._iter_failures(data.context):
            code = failure.get("code", "?")
            equip = failure.get("equipment", "?")
            metric = failure.get("metric")
            value = failure.get("value")
            severity = failure.get("severity")
            desc = f"{code} on {equip}"
            if severity:
                desc += f" [{severity}]"
            if metric is not None and value is not None:
                desc += f" ({metric}={value})"
            lines.append(desc)
        correlation = data.context.get("correlation") if isinstance(data.context, dict) else None
        if isinstance(correlation, dict):
            if correlation.get("localized_to"):
                lines.append(f"localized to {correlation['localized_to']}")
            if correlation.get("blast_radius"):
                lines.append(f"blast radius: {correlation['blast_radius']}")
        return lines

    @staticmethod
    def _iter_failures(context: Any) -> Iterator[dict[str, Any]]:
        if not isinstance(context, dict):
            return
        seen_direct = context.get("failures")
        if isinstance(seen_direct, list):
            for f in seen_direct:
                if isinstance(f, dict):
                    yield f
        for key in ("fault", "fault_event"):
            fault = context.get(key)
            if isinstance(fault, dict):
                for f in fault.get("failures", []) or []:
                    if isinstance(f, dict):
                        yield f
