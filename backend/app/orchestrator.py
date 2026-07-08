"""Orchestrator runtime (BE.3) — incident commander: routes and holds state,
NEVER diagnoses.

State machine (ROADMAP):
    idle -> fault_triggered -> phase1_running -> awaiting_field_validation
         -> phase2_running -> report_ready -> resolved -> idle
plus the pivot loop:
    awaiting_field_validation -> phase1_running (cause=pivot) -> phase2_running
(after a pivot re-diagnosis the field measurement already exists, so the
orchestrator may proceed to phase 2 without a second push loop — EVENTS.md §10).

Agents are pluggable through the FROZEN protocol (contracts.Agent): the runtime
only awaits `run(AgentInput) -> AgentOutput` on whatever the registry holds.
All content in the emitted events comes from agent payloads or seeds — this
module only assembles, it holds no domain judgement (backend acceptance).
Agent failures/timeouts become `agent_completed status=error|timeout` events,
never a crash (INT.5 groundwork).
"""
import asyncio
import logging
from typing import Any

from contracts import Agent, AgentInput

from agents.orchestration.citations import enrich_citations

from backend.app.bus import EventBus
from backend.app.seeds import Seeds

logger = logging.getLogger("arc.orchestrator")


class IllegalTransition(RuntimeError):
    pass


IDLE = "idle"
FAULT_TRIGGERED = "fault_triggered"
PHASE1 = "phase1_running"
AWAITING = "awaiting_field_validation"
PHASE2 = "phase2_running"
REPORT_READY = "report_ready"
RESOLVED = "resolved"

TRANSITIONS: dict[str, set[str]] = {
    IDLE: {FAULT_TRIGGERED},
    FAULT_TRIGGERED: {PHASE1},
    PHASE1: {AWAITING, PHASE2, RESOLVED},  # PHASE2 on pivot re-entry; RESOLVED = degraded terminal (INT.5)
    AWAITING: {PHASE2, PHASE1},          # confirmed -> phase2 · pivot -> phase1
    PHASE2: {REPORT_READY},
    REPORT_READY: {RESOLVED},
    RESOLVED: {IDLE},
}


class Orchestrator:
    def __init__(self, bus: EventBus, seeds: Seeds, agents: dict[str, Agent],
                 push_service: Any, agent_timeout_s: float = 120.0,
                 auto_reset_s: float = 0.0) -> None:
        self.bus = bus
        self.seeds = seeds
        self.agents = agents
        self.push = push_service
        self.agent_timeout_s = agent_timeout_s
        self.auto_reset_s = auto_reset_s
        self.state = IDLE
        self.incident: dict[str, Any] | None = None
        self._incident_counter = 0
        self._failure_counter = 0
        self._task: asyncio.Task | None = None
        self._auto_reset_task: asyncio.Task | None = None
        self.on_incident_closed = None  # set by main to notify the watchdog
        self.reset_hook = None          # set by main: the full app reset (auto-reset TTL)

    # -- state machine (BE.3: every transition asserted + unit-tested) --------
    def _transition(self, to: str) -> None:
        if to not in TRANSITIONS[self.state]:
            raise IllegalTransition(f"{self.state} -> {to}")
        self.state = to

    async def join(self) -> None:
        """Await the in-flight pipeline (tests + demo determinism)."""
        while self._task is not None and not self._task.done():
            await asyncio.shield(self._task)

    def reset(self) -> None:
        """Demo reset (BE.11): back to idle, < 5 s (it is immediate)."""
        self._cancel_auto_reset()
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        self.incident = None
        self.state = IDLE

    # -- auto-reset TTL (idle-return after a terminal state) -------------------
    def _arm_auto_reset(self) -> None:
        """After a terminal state, schedule the TTL return to a clean idle.
        No-op when auto_reset_s <= 0. Only one timer at a time (the new one
        replaces any pending one); a manual reset or a new incident cancels it,
        so an ACTIVE run is never reset."""
        if self.auto_reset_s <= 0:
            return
        self._cancel_auto_reset()
        self._auto_reset_task = asyncio.create_task(
            self._auto_reset_after(self._incident_counter))

    async def _auto_reset_after(self, generation: int) -> None:
        """Wait the TTL, then run the SAME reset as POST /api/demo/reset — but
        only if nothing changed: a bumped incident counter or a non-idle state
        means a new/active run, which must never be reset. Any exception is
        swallowed so a failed auto-reset can never take the server down."""
        try:
            await asyncio.sleep(self.auto_reset_s)
            if generation != self._incident_counter or self.state != IDLE:
                return  # a new incident / active run since arming — leave it alone
            self._auto_reset_task = None  # disarm before the hook (it calls reset())
            (self.reset_hook or self.reset)()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - a crashing auto-reset must never crash the server
            logger.exception("auto-reset failed")

    def _cancel_auto_reset(self) -> None:
        task, self._auto_reset_task = self._auto_reset_task, None
        if task is not None and not task.done():
            task.cancel()

    # -- fault intake (from the Watchdog) --------------------------------------
    async def handle_fault(self, site_id: str, family: str,
                           failures: list[dict], trigger: dict) -> str | None:
        if self.state != IDLE:
            return None  # one incident at a time; feed keeps flowing, no crash
        self._cancel_auto_reset()  # a new incident cancels any pending TTL auto-reset
        self._incident_counter += 1
        self._failure_counter = 0
        incident_id = f"INC-LIVE-{self._incident_counter:03d}"
        site = self.seeds.sites.get(site_id, {"site_id": site_id, "name": site_id, "lat": 0.0, "lon": 0.0})
        self.incident = {
            "id": incident_id,
            "site": site,
            "family": family,
            "failures": [self._assign_id(f) for f in failures],
            "trigger": trigger,
            "validation": None,
            "validation_result": None,
            "diagnostic": None,
            "remediation": None,
            "cid": None,
        }
        self._transition(FAULT_TRIGGERED)
        self.bus.emit(incident_id, "fault_detected", {
            "site": self._site_ref(),
            "family": family,
            "failures": self.incident["failures"],
            "trigger": trigger,
        })
        self._task = asyncio.create_task(self._run_phase1("initial"))
        return incident_id

    async def add_failures(self, site_id: str, failures: list[dict]) -> None:
        """Failures fired while an incident is active attach to it (BE.2)."""
        if self.incident and self.incident["site"].get("site_id", self.incident["site"].get("id")) == site_id:
            self.incident["failures"].extend(self._assign_id(f) for f in failures)

    def _assign_id(self, failure: dict) -> dict:
        self._failure_counter += 1
        return {"id": f"F{self._failure_counter}", **failure}

    def _site_ref(self) -> dict:
        s = self.incident["site"]
        return {"id": s.get("site_id", s.get("id", "unknown")), "name": s.get("name", ""),
                "lat": float(s.get("lat", 0.0)), "lon": float(s.get("lon", 0.0)),
                "address": s.get("address", "")}

    # -- citation transform (AUDIT P0-1, #76) -----------------------------------
    # Agents produce contracts Citation {doc_id, section, snippet?}; the frozen
    # event schema transports {doc_id, claim REQUIRED, title?, page?}. This is
    # THE agent->event transform, applied at every emission point so any real
    # agent's citations are event-legal.
    @staticmethod
    def _event_citation(c: dict[str, Any]) -> dict[str, Any]:
        claim = c.get("claim") or c.get("section") or (c.get("snippet") or "").strip()[:120]
        out: dict[str, Any] = {"doc_id": c.get("doc_id") or "unknown",
                               "claim": claim or "supporting source"}
        if c.get("title"):
            out["title"] = c["title"]
        if isinstance(c.get("page"), int):
            out["page"] = c["page"]
        return out

    @classmethod
    def _event_citations(cls, citations: list | None) -> list[dict[str, Any]]:
        return [cls._event_citation(c) for c in (citations or [])]

    @classmethod
    def _cite(cls, citations: Any) -> list[dict[str, Any]]:
        """Event-legal citations, enriched with an openable source (drill-down)."""
        return enrich_citations(cls._event_citations(citations))

    @classmethod
    def _normalize_diagnostic(cls, diagnostic: dict[str, Any]) -> dict[str, Any]:
        out = dict(diagnostic)
        out["causes"] = [{**c, "citations": cls._cite(c.get("citations"))}
                         for c in diagnostic.get("causes", [])]
        if diagnostic.get("urgency"):
            u = dict(diagnostic["urgency"])
            if u.get("citations"):
                u["citations"] = cls._cite(u["citations"])
            out["urgency"] = u
        return out

    @classmethod
    def _normalize_procedure(cls, procedure: dict[str, Any]) -> dict[str, Any]:
        out = dict(procedure)
        out["steps"] = [{**s, "citations": cls._cite(s.get("citations"))}
                        for s in procedure.get("steps", [])]
        if procedure.get("safety"):
            out["safety"] = [{**s, "citations": cls._cite(s.get("citations"))}
                             for s in procedure["safety"]]
        return out

    # -- agent runner (frozen protocol; timeout-safe) --------------------------
    async def _run_agent(self, name: str, phase: int, context: dict[str, Any]):
        inc = self.incident
        self.bus.emit(inc["id"], "agent_started", {"agent": name, "phase": phase})
        agent = self.agents[name]
        data = AgentInput(
            incident_id=inc["id"],
            site_id=inc["site"].get("site_id", "unknown"),
            failure_family=inc["family"],
            context=context,
        )
        loop = asyncio.get_running_loop()
        started = loop.time()
        try:
            output = await asyncio.wait_for(agent.run(data), timeout=self.agent_timeout_s)
        except asyncio.TimeoutError:
            self.bus.emit(inc["id"], "agent_completed", {
                "agent": name, "phase": phase, "status": "timeout",
                "duration_ms": int((loop.time() - started) * 1000),
                "summary": f"{name} exceeded {self.agent_timeout_s}s — run aborted gracefully"})
            return None
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # graceful error event, no crash (INT.5)
            self.bus.emit(inc["id"], "agent_completed", {
                "agent": name, "phase": phase, "status": "error",
                "duration_ms": int((loop.time() - started) * 1000),
                "summary": f"{name} failed: {exc}"})
            return None
        for r in output.payload.get("retrievals", []):
            self.bus.emit(inc["id"], "retrieval_performed", {
                "agent": name, "pass": r["pass"], "query": r["query"], "results": r["results"]})
        self.bus.emit(inc["id"], "agent_completed", {
            "agent": name, "phase": phase, "status": "ok",
            "duration_ms": int((loop.time() - started) * 1000),
            "summary": output.summary})
        return output

    # -- phase 1 ---------------------------------------------------------------
    async def _run_phase1(self, cause: str) -> None:
        inc = self.incident
        self._transition(PHASE1)
        self.bus.emit(inc["id"], "phase_started", {"phase": 1, "cause": cause})

        base_ctx = {"failures": inc["failures"], "phase_cause": cause,
                    "validations": (inc["validation"] or {}).get("validations", []),
                    "measurements": (inc["validation"] or {}).get("measurements", [])}
        # Physical interpretation of any field measurement, computed IN CODE in
        # magnitudes (a -48 V plant reads negative; undervoltage fires on |v| below
        # threshold) so the pivot re-diagnosis never reads -53.9 V as "worse than"
        # -44.8 V. Empty on the initial pass (no field measurement yet).
        base_ctx["measurement_interpretation"] = self._interpret_measurements(
            base_ctx["measurements"], inc["failures"])
        corr = await self._run_agent("correlation", 1, base_ctx)
        if corr is None:
            await self._terminate_degraded_phase1("correlation")  # never leave the incident stuck (INT.5)
            return
        for f in corr.payload.get("added_failures", []):
            inc["failures"].append(self._assign_id(f))

        rc = await self._run_agent("root_cause", 1, {**base_ctx, "correlation": corr.payload.get("correlation", {})})
        if rc is None:
            await self._terminate_degraded_phase1("root_cause")  # never leave the incident stuck (INT.5)
            return
        diagnostic = self._normalize_diagnostic(rc.payload.get("diagnostic", {}))
        inc["diagnostic"] = diagnostic

        # Root-Cause's mandatory missing-doc path (grounding gate) -> the
        # doc_requested event, surfaced BEFORE the diagnostic it qualifies.
        doc_req = diagnostic.pop("doc_request", None) or rc.payload.get("doc_request")
        if isinstance(doc_req, dict):
            self.bus.emit(inc["id"], "doc_requested", {
                "agent": "root_cause",
                "description": doc_req.get("description", "document missing from corpus"),
                "query": doc_req.get("query", ""),
                "status": doc_req.get("status", "missing")})

        self.bus.emit(inc["id"], "diagnostic_ready", {
            "correlation": corr.payload.get("correlation",
                                            {"site_id": inc["site"].get("site_id", ""), "equipment": []}),
            "causes": diagnostic.get("causes", []),
            **({"urgency": diagnostic["urgency"]} if diagnostic.get("urgency") else {}),
            "failures": [],
            "verification_requests": diagnostic.get("verification_requests", []),
        })

        if cause == "pivot":
            await self._run_phase2()  # field data already in hand — no second push loop
            return

        responders = await self._match_responders(corr)  # employee-matching (aminssutt)
        operator_id = responders[0].get("employee_id") if responders else None
        payload = await self.push.send(inc, operator_id=operator_id)  # emits push_sent, routed to the matched tech
        self.bus.emit(inc["id"], "awaiting_field_validation", {
            "failure_ids": [f["id"] for f in inc["failures"]],
            "requested_measurements": [
                {"metric": v.get("metric", ""), "point": v.get("point", ""), "unit": ""}
                for v in diagnostic.get("verification_requests", [])],
            **({"responders": responders} if responders else {}),
        })
        self._transition(AWAITING)

    async def _match_responders(self, corr) -> list[dict[str, Any]]:
        """Employee-matching: route the diagnosed fault to ONE responder to notify.

        Runs the deterministic ResponderMatchingAgent directly (it is not a
        frozen `agent` enum value, so it never goes through `_run_agent`); its
        pick rides the `awaiting_field_validation` event's `data` (schema is open,
        no contract change). Never breaks the run — degrades to no responder.
        """
        agent = self.agents.get("responder_matching")
        if agent is None:
            return []
        inc = self.incident
        primary = inc["failures"][0] if inc["failures"] else {}
        fault = {
            "family": inc["family"],
            "equipment_class": corr.payload.get("correlation", {}).get("equipment_class"),
            "code": primary.get("alarm_code") or primary.get("code"),  # canonical alarm_code
            "region": inc["site"].get("region", ""),
        }
        try:
            out = await agent.run(AgentInput(
                incident_id=inc["id"], site_id=inc["site"].get("site_id", "unknown"),
                failure_family=inc["family"], context={"fault": fault}))
        except Exception:  # noqa: BLE001 - notification is best-effort, never fatal
            return []
        inc["responders"] = out.payload
        chosen = out.payload.get("responder")
        if not chosen:
            return []
        self._emit_responder_matched(out.payload, fault)  # matchmaking narrowing event
        return [chosen]

    @staticmethod
    def _responder_card(r: dict[str, Any]) -> dict[str, Any]:
        """Compact roster view the front renders: name, skill, zone, seniority."""
        card = {
            "employee_id": r.get("employee_id", ""),
            "name": r.get("name", ""),
            "tier": r.get("tier", ""),
            "region": r.get("region", ""),
            "matched_skills": r.get("matched_skills", []),
            "score": r.get("score", 0.0),
        }
        if r.get("reason"):
            card["reason"] = r["reason"]
        if "out_of_zone" in r:
            card["out_of_zone"] = bool(r["out_of_zone"])
        return card

    def _emit_responder_matched(self, payload: dict[str, Any], fault: dict[str, Any]) -> None:
        """Surface the matchmaking narrowing as its own event: the candidates
        considered (name, skill, zone) and the single retained technician with the
        skill+zone reason. Additive event type; every field stays contract-legal."""
        chosen = payload.get("responder") or {}
        alternatives = payload.get("alternatives", []) or []
        candidates = [self._responder_card(chosen)] + [self._responder_card(a) for a in alternatives]
        self.bus.emit(self.incident["id"], "responder_matched", {
            "fault": payload.get("fault", fault),
            "difficulty": payload.get("difficulty", ""),
            "chosen": self._responder_card(chosen),
            "candidates": candidates,
        })

    # -- human loop (from POST /api/validation, BE.6) ---------------------------
    async def handle_validation(self, body: dict[str, Any]) -> dict[str, Any]:
        inc = self.incident
        self.bus.emit(inc["id"], "validation_received", {
            "validations": body["validations"],
            "measurements": body.get("measurements", []),
            **({"technician": body["technician"]} if body.get("technician") else {}),
            "client_event_id": body["client_event_id"],
        })
        inc["validation"] = body
        out = await self._run_agent("validation", 1, {
            "failures": inc["failures"],
            "validations": body["validations"],
            "measurements": body.get("measurements", []),
            "diagnostic": inc["diagnostic"],      # load-bearing failure + top cause
            "validation_event": body,             # the raw frozen-contract POST body
        })
        result = (out.payload.get("result") if out else None) or "confirmed"
        inc["validation_result"] = result
        self.bus.emit(inc["id"], "validation_result", {
            "result": result,
            "rationale": (out.payload.get("rationale") if out else "validation agent unavailable — defaulting"),
            "contradictions": (out.payload.get("contradictions", []) if out else []),
        })
        if result == "pivot":
            self._task = asyncio.create_task(self._run_phase1("pivot"))
        else:
            self._task = asyncio.create_task(self._run_phase2_from_awaiting())
        return {"status": "accepted", "incident_id": inc["id"], "result": result}

    async def _run_phase2_from_awaiting(self) -> None:
        await self._run_phase2()

    # -- phase 2 ---------------------------------------------------------------
    async def _run_phase2(self) -> None:
        inc = self.incident
        self._transition(PHASE2)
        self.bus.emit(inc["id"], "phase_started", {"phase": 2, "cause": "initial"})

        suspect_part = self._suspect_part()  # topology-resolved catalog part (seed lookup)
        rem = await self._run_agent("remediation", 2, {
            "failures": inc["failures"],
            "diagnostic": inc["diagnostic"],
            "validation_result": inc["validation_result"],
            "suspect_part": suspect_part,
        })
        if rem is None:
            await self._terminate_degraded("remediation")  # never leave the incident stuck
            return
        procedure = self._ensure_steps(
            self._normalize_procedure(rem.payload.get("procedure", {"title": rem.summary, "steps": []})))
        inc["remediation"] = {**rem.payload, "procedure": procedure}
        self.bus.emit(inc["id"], "remediation_ready", {
            "procedure": procedure,
            "parts": rem.payload.get("parts", []),
        })

        hints = rem.payload.get("action_hints", [])
        # Lead the Inventory lookup with the TOPOLOGY-resolved catalog part: Remediation
        # emits free-text part names (LLM) that miss the exact-match inventory get(), so
        # the report showed qty 0 / in_stock false for a part that is actually in stock.
        # The free-text parts still follow (kept for the report/context).
        rem_parts = rem.payload.get("parts", [])
        cid_parts = list(rem_parts)
        if suspect_part and not any(
                isinstance(p, dict) and (p.get("part_no") or p.get("part_number")) == suspect_part
                for p in rem_parts):
            cid_parts.insert(0, {"part_no": suspect_part,
                                 "description": "topology-matched spare", "qty": 1})
        cid = await self._run_agent("cost_inventory_dispatch", 2, {
            "parts": cid_parts,
            "suspect_part": suspect_part,
            "remediation_title": rem.payload.get("procedure", {}).get("title", rem.summary),
            "top_priority": hints[0]["priority"] if hints else "P1",
        })
        if cid is None:
            await self._terminate_degraded("cost_inventory_dispatch")  # never leave the incident stuck
            return
        inc["cid"] = cid.payload

        self.bus.emit(inc["id"], "action_report_ready", {"report": self._assemble_report()})
        self._transition(REPORT_READY)
        outcome = "resolved" if inc["validation_result"] == "confirmed" else "downgraded"
        self.bus.emit(inc["id"], "incident_resolved", {
            "summary": f"action report issued ({outcome}); top action: "
                       f"{(inc['remediation'].get('action_hints') or [{}])[0].get('action', 'n/a')}",
            "outcome": outcome,
        })
        self._transition(RESOLVED)
        self._transition(IDLE)
        if self.on_incident_closed:
            self.on_incident_closed(inc["site"].get("site_id", ""))
        self._arm_auto_reset()  # TTL return to a clean idle (no-op when disabled)

    # -- degraded terminal path, phase 1 (INT.5 #51): same guarantee as #97 -----
    async def _terminate_degraded_phase1(self, failed_agent: str) -> None:
        """A phase-1 agent returned nothing (failed/timed out): no diagnosis
        exists, so no action report is possible — but the incident still closes
        with incident_resolved (outcome 'downgraded') so no consumer hangs.
        The agent_completed error/timeout event before this names the cause."""
        inc = self.incident
        self.bus.emit(inc["id"], "incident_resolved", {
            "summary": f"incident closed DEGRADED: phase-1 agent '{failed_agent}' "
                       "unavailable — no diagnosis produced, manual triage required",
            "outcome": "downgraded",
        })
        self._transition(RESOLVED)
        self._transition(IDLE)
        if self.on_incident_closed:
            self.on_incident_closed(inc["site"].get("site_id", ""))
        self._arm_auto_reset()  # TTL return to a clean idle (no-op when disabled)

    # -- degraded terminal path (issue #97): the demo must ALWAYS finish --------
    @staticmethod
    def _ensure_steps(procedure: dict[str, Any]) -> dict[str, Any]:
        """Guarantee procedure.steps is non-empty. The frozen events.schema
        requires remediation_ready.procedure.steps minItems>=1, so a degraded
        fallback (real adapter) or an agent that omits `procedure` still gets one
        explicit manual-intervention step rather than an invalid empty array."""
        if not procedure.get("steps"):
            return {**procedure,
                    "steps": [{"n": 1,
                               "text": "Manual intervention required — see diagnostic",
                               "citations": []}]}
        return procedure

    async def _terminate_degraded(self, failed_agent: str) -> None:
        """A phase-2 agent returned nothing (failed/timed out): still close the
        incident with a DEGRADED action report + incident_resolved so the UI
        never hangs (issue #97). The frozen schema constrains
        incident_resolved.outcome to {resolved, downgraded}; a phase-2 failure
        terminates as 'downgraded' with the failing agent named in the summary."""
        inc = self.incident
        self.bus.emit(inc["id"], "action_report_ready",
                      {"report": self._assemble_degraded_report(failed_agent)})
        self._transition(REPORT_READY)
        self.bus.emit(inc["id"], "incident_resolved", {
            "summary": f"incident closed DEGRADED: phase-2 agent '{failed_agent}' "
                       "unavailable — remediation/costing incomplete, manual "
                       "intervention required",
            "outcome": "downgraded",
        })
        self._transition(RESOLVED)
        self._transition(IDLE)
        if self.on_incident_closed:
            self.on_incident_closed(inc["site"].get("site_id", ""))
        self._arm_auto_reset()  # TTL return to a clean idle (no-op when disabled)

    def _assemble_degraded_report(self, failed_agent: str) -> dict[str, Any]:
        """Phase-1 diagnosis + a manual-intervention action, schema-valid with no
        remediation/cost/dispatch data (issue #97). diagnosis.citations has
        minItems>=1, so an empty phase-1 citation set falls back to a marker."""
        inc = self.incident
        causes = (inc["diagnostic"] or {}).get("causes", [])
        top = causes[0] if causes else {"cause": "unknown", "confidence": 0.0, "citations": []}
        diag_citations = top.get("citations") or [
            {"doc_id": "n/a", "claim": "no grounded source — phase-2 degraded"}]
        note = (f"phase 2 incomplete: '{failed_agent}' unavailable — remediation and "
                "costing could not be produced; manual intervention required")
        return {
            "diagnosis": {"cause": top["cause"], "confidence": top["confidence"],
                          "citations": diag_citations},
            "actions": [{"priority": "P1",
                         "action": "Manual intervention required — remediation/costing unavailable"}],
            "cost": {"currency": "USD", "intervention": 0.0, "avoided": 0.0, "notes": note},
            "honesty_notes": [note],
            "citations": diag_citations,
        }

    _MAG_OPS = {"lt": lambda v, t: v < t, "lte": lambda v, t: v <= t,
                "gt": lambda v, t: v > t, "gte": lambda v, t: v >= t,
                "eq": lambda v, t: v == t, "neq": lambda v, t: v != t}

    def _interpret_measurements(self, measurements: list[dict[str, Any]] | None,
                                failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compute each field measurement's physical status IN CODE, in MAGNITUDES.

        A -48 V DC plant reads negative; the undervoltage alarm fires on |v| below
        the seeded threshold (alarm_dictionary), so a larger magnitude is HEALTHIER,
        not worse. This structured verdict feeds the pivot prompt so the LLM reasons
        from correct physics instead of the raw signed number. A missing/unparseable
        threshold yields status 'unknown' — never a crash, never a false claim."""
        out: list[dict[str, Any]] = []
        for m in measurements or []:
            metric, value = m.get("metric"), m.get("value")
            if metric is None or not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            magnitude = round(abs(value), 2)
            rule = next((r for r in self.seeds.alarm_dictionary.values()
                         if r.get("signal") == metric), None)
            telem = next((f.get("value") for f in failures
                          if f.get("metric") == metric and isinstance(f.get("value"), (int, float))
                          and not isinstance(f.get("value"), bool)), None)
            interp: dict[str, Any] = {
                "metric": metric, "point": m.get("point"), "unit": m.get("unit", ""),
                "value": value, "magnitude": magnitude, "telemetry": telem,
                "telemetry_magnitude": round(abs(telem), 2) if isinstance(telem, (int, float)) else None,
            }
            try:
                op = rule and rule.get("threshold_op")
                if rule and op in self._MAG_OPS and rule.get("threshold_value") is not None:
                    threshold = float(rule["threshold_value"])
                    abnormal = self._MAG_OPS[op](magnitude, threshold)
                    interp.update({"threshold": threshold, "abnormal": abnormal,
                                   "status": "unhealthy" if abnormal else "healthy"})
                else:
                    interp["status"] = "unknown"
            except (TypeError, ValueError):
                interp["status"] = "unknown"
            out.append(interp)
        return out

    def _topology_part(self) -> str | None:
        """Catalog part of the first implicated equipment (seed topology lookup)."""
        inc = self.incident
        for f in inc["failures"]:
            for eq in self.seeds.equipment.values():
                if eq["site_id"] == inc["site"].get("site_id") and eq.get("part_number") \
                        and (f["equipment"] in (eq["equipment_id"], eq["class"], eq.get("model", ""))
                             or eq["class"] in f["equipment"]):
                    return eq["part_number"]
        return None

    def _suspect_part(self) -> str | None:
        """Topology part to LEAD the inventory lookup (the exact-match fix for
        free-text remediation parts). Deterministically NOT applied after a pivot:
        the pivoted cause is no longer the originally-implicated equipment, so the
        rectifier spare must NEVER lead a sensing-fault report — the lookup then
        follows the remediation's own parts (SP2-MU), on 100% of pivots."""
        if self.incident.get("validation_result") == "pivot":
            return None
        return self._topology_part()

    # -- report assembly (mechanical merge of agent payloads + tool results) ---
    def _assemble_report(self) -> dict[str, Any]:
        inc = self.incident
        causes = (inc["diagnostic"] or {}).get("causes", [])
        top = causes[0] if causes else {"cause": "unknown", "confidence": 0.0, "citations": []}
        cid = inc["cid"] or {}
        cost, inv, disp = cid.get("cost", {}), cid.get("inventory", {}), cid.get("dispatch", {})
        first_match = (inv.get("matches") or [{}])[0]

        actions = [
            {"priority": h["priority"], "action": h["action"],
             **({"owner": disp.get("crew_id")} if disp.get("booked") else {})}
            for h in (inc["remediation"] or {}).get("action_hints", [])
        ] or [{"priority": "P1", "action": (inc["remediation"] or {}).get("procedure", {}).get("title", "remediate")}]

        citations: list[dict] = []
        for c in causes:
            citations.extend(c.get("citations", []))
        for step in (inc["remediation"] or {}).get("procedure", {}).get("steps", []):
            citations.extend(step.get("citations", []))
        for s in (inc["remediation"] or {}).get("procedure", {}).get("safety", []):
            citations.extend(s.get("citations", []))
        seen, deduped = set(), []
        for c in citations:
            key = (c["doc_id"], c.get("claim"))
            if key not in seen:
                seen.add(key)
                deduped.append(c)
        # Citation drill-down: attach an openable source (title/url/open_url/page)
        # to each citation while preserving doc_id + claim (event-schema required).
        enriched = enrich_citations(deduped)

        honesty = []
        if inc["validation_result"] == "pivot":
            honesty.append("initial telemetry-based diagnosis was contradicted by the field "
                           "measurement; this report is the post-pivot re-diagnosis")
        if not disp.get("booked", False):
            honesty.append("no crew available for immediate dispatch — booking conflict flagged")

        avoided = cost.get("downtime_cost_avoided", 0.0)
        cost_notes = "; ".join(f"{k}: {v:.2f}" for k, v in cost.get("breakdown", {}).items())
        if inc["validation_result"] == "pivot":
            # Spurious-alarm pivot: no outage occurs, so "avoided" is the needless
            # emergency replacement the false alarm would have triggered (original
            # topology part + 2 h labor + truck roll, from the seeds), NOT the
            # outage cost — a defensible figure for catching a false alarm.
            part = self._topology_part()
            part_price = self.seeds.inventory.get(part, {}).get("unit_price_usd", 0.0) if part else 0.0
            cp = self.seeds.cost_params
            labor = round(cp.get("labor_rate", {}).get("value_usd", 0.0) * 2.0, 2)
            truck = cp.get("truck_roll_flat", {}).get("value_usd", 0.0)
            avoided = round(part_price + labor + truck, 2)
            cost_notes = (f"spurious alarm — avoided a needless emergency replacement "
                          f"(part {part_price:.2f} + 2 h labor {labor:.2f} + truck roll {truck:.2f})")
        return {
            "diagnosis": {"cause": top["cause"], "confidence": top["confidence"],
                          "citations": top.get("citations", [])},
            "actions": actions,
            "cost": {"currency": cost.get("currency", "USD"),
                     "intervention": cost.get("repair_cost", 0.0),
                     "avoided": avoided,
                     "notes": cost_notes},
            "inventory": {"part_no": first_match.get("part_number", ""),
                          "qty_available": first_match.get("quantity", 0),
                          "location": first_match.get("warehouse_id") or "",
                          "in_stock": first_match.get("in_stock", False)},
            "dispatch": {"crew": disp.get("crew_id", ""),
                         **({"conflict": "no crew available"} if not disp.get("booked", False) else {}),
                         "booking_id": f"BK-{inc['id'].rsplit('-', 1)[-1]}" if disp.get("booked") else ""},
            "honesty_notes": honesty,
            "citations": enriched,
        }
