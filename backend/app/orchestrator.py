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
from typing import Any

from contracts import Agent, AgentInput

from backend.app.bus import EventBus
from backend.app.seeds import Seeds


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
    PHASE1: {AWAITING, PHASE2},          # PHASE2 direct only on the pivot re-entry
    AWAITING: {PHASE2, PHASE1},          # confirmed -> phase2 · pivot -> phase1
    PHASE2: {REPORT_READY},
    REPORT_READY: {RESOLVED},
    RESOLVED: {IDLE},
}


class Orchestrator:
    def __init__(self, bus: EventBus, seeds: Seeds, agents: dict[str, Agent],
                 push_service: Any, agent_timeout_s: float = 120.0) -> None:
        self.bus = bus
        self.seeds = seeds
        self.agents = agents
        self.push = push_service
        self.agent_timeout_s = agent_timeout_s
        self.state = IDLE
        self.incident: dict[str, Any] | None = None
        self._incident_counter = 0
        self._failure_counter = 0
        self._task: asyncio.Task | None = None
        self.on_incident_closed = None  # set by main to notify the watchdog

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
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        self.incident = None
        self.state = IDLE

    # -- fault intake (from the Watchdog) --------------------------------------
    async def handle_fault(self, site_id: str, family: str,
                           failures: list[dict], trigger: dict) -> str | None:
        if self.state != IDLE:
            return None  # one incident at a time; feed keeps flowing, no crash
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
        corr = await self._run_agent("correlation", 1, base_ctx)
        if corr is None:
            return
        for f in corr.payload.get("added_failures", []):
            inc["failures"].append(self._assign_id(f))

        rc = await self._run_agent("root_cause", 1, {**base_ctx, "correlation": corr.payload.get("correlation", {})})
        if rc is None:
            return
        diagnostic = rc.payload.get("diagnostic", {})
        inc["diagnostic"] = diagnostic

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

        payload = await self.push.send(inc)  # emits push_sent
        self.bus.emit(inc["id"], "awaiting_field_validation", {
            "failure_ids": [f["id"] for f in inc["failures"]],
            "requested_measurements": [
                {"metric": v.get("metric", ""), "point": v.get("point", ""), "unit": ""}
                for v in diagnostic.get("verification_requests", [])],
        })
        self._transition(AWAITING)

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

        rem = await self._run_agent("remediation", 2, {
            "failures": inc["failures"],
            "diagnostic": inc["diagnostic"],
            "validation_result": inc["validation_result"],
            "suspect_part": self._suspect_part(),
        })
        if rem is None:
            return
        inc["remediation"] = rem.payload
        self.bus.emit(inc["id"], "remediation_ready", {
            "procedure": rem.payload.get("procedure", {"title": rem.summary, "steps": []}),
            "parts": rem.payload.get("parts", []),
        })

        hints = rem.payload.get("action_hints", [])
        cid = await self._run_agent("cost_inventory_dispatch", 2, {
            "parts": rem.payload.get("parts", []),
            "remediation_title": rem.payload.get("procedure", {}).get("title", rem.summary),
            "top_priority": hints[0]["priority"] if hints else "P1",
        })
        if cid is None:
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

    def _suspect_part(self) -> str | None:
        """Part of the first implicated equipment (seed topology lookup, mechanical)."""
        inc = self.incident
        for f in inc["failures"]:
            for eq in self.seeds.equipment.values():
                if eq["site_id"] == inc["site"].get("site_id") and eq.get("part_number") \
                        and (f["equipment"] in (eq["equipment_id"], eq["class"], eq.get("model", ""))
                             or eq["class"] in f["equipment"]):
                    return eq["part_number"]
        return None

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

        honesty = []
        if inc["validation_result"] == "pivot":
            honesty.append("initial telemetry-based diagnosis was contradicted by the field "
                           "measurement; this report is the post-pivot re-diagnosis")
        if not disp.get("booked", False):
            honesty.append("no crew available for immediate dispatch — booking conflict flagged")

        return {
            "diagnosis": {"cause": top["cause"], "confidence": top["confidence"],
                          "citations": top.get("citations", [])},
            "actions": actions,
            "cost": {"currency": cost.get("currency", "EUR"),
                     "intervention": cost.get("repair_cost", 0.0),
                     "avoided": cost.get("downtime_cost_avoided", 0.0),
                     "notes": "; ".join(f"{k}: {v:.2f}" for k, v in cost.get("breakdown", {}).items())},
            "inventory": {"part_no": first_match.get("part_number", ""),
                          "qty_available": first_match.get("quantity", 0),
                          "location": first_match.get("warehouse_id") or "",
                          "in_stock": first_match.get("in_stock", False)},
            "dispatch": {"crew": disp.get("crew_id", ""),
                         **({"conflict": "no crew available"} if not disp.get("booked", False) else {}),
                         "booking_id": f"BK-{inc['id'].rsplit('-', 1)[-1]}" if disp.get("booked") else ""},
            "honesty_notes": honesty,
            "citations": deduped,
        }
