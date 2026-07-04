"""Watchdog (BE.2) — deterministic: ingest → normalize → threshold → debounce.

ZERO LLM calls, zero diagnosis. Every threshold/debounce/severity/family comes
from the alarm dictionary seed (data/schema.md §1) — the Watchdog is pure
mechanism, entirely data-driven.

Signals (the raw feed / injector shape):
    {"ts": ISO-8601, "site_id": str, "signal": str, "value": num|bool, "equipment_id": str?}

Debounce is on EVENT time (signal `ts`), not wall time, so fixture replays at
10-30x behave identically (validation/GROUND_TRUTH_SCENARIOS.md note).
One incident per site at a time: while an incident is active, newly fired
failures are attached to it — never a second FaultEvent (BE.2 acceptance).
"""
from datetime import datetime
from typing import Any, Awaitable, Callable

from backend.app.seeds import Seeds

_OPS: dict[str, Callable[[float, float], bool]] = {
    "lt": lambda v, t: v < t,
    "lte": lambda v, t: v <= t,
    "gt": lambda v, t: v > t,
    "gte": lambda v, t: v >= t,
    "eq": lambda v, t: v == t,
    "neq": lambda v, t: v != t,
}


def _ts(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


class Watchdog:
    def __init__(
        self,
        seeds: Seeds,
        on_fault: Callable[[str, str, list[dict], dict], Awaitable[None]],
        on_additional_failures: Callable[[str, list[dict]], Awaitable[None]] | None = None,
    ) -> None:
        self._rules_by_signal: dict[str, list[dict]] = {}
        for rule in seeds.alarm_dictionary.values():
            self._rules_by_signal.setdefault(rule["signal"], []).append(rule)
        self._on_fault = on_fault
        self._on_additional = on_additional_failures
        # (site_id, alarm_code) -> {"first_breach": epoch, "fired": bool}
        self._states: dict[tuple[str, str], dict[str, Any]] = {}
        self._active_incident_sites: set[str] = set()

    # -- lifecycle -----------------------------------------------------------
    def reset(self) -> None:
        self._states.clear()
        self._active_incident_sites.clear()

    def incident_closed(self, site_id: str) -> None:
        self._active_incident_sites.discard(site_id)
        self._states = {k: v for k, v in self._states.items() if k[0] != site_id}

    # -- ingestion -----------------------------------------------------------
    async def ingest(self, signal: dict[str, Any]) -> None:
        await self.ingest_batch([signal])

    async def ingest_batch(self, signals: list[dict[str, Any]]) -> None:
        """Process signals in order; at most ONE FaultEvent per site per batch."""
        fired: dict[str, list[dict]] = {}
        trigger: dict[str, dict] = {}
        for sig in signals:
            for failure, rule, at in self._evaluate(sig):
                fired.setdefault(sig["site_id"], []).append(failure)
                trigger.setdefault(sig["site_id"], {
                    "rule": rule["alarm_code"],
                    "debounce_s": rule["debounce_s"],
                    "triggered_at": at,
                })
        for site_id, failures in fired.items():
            if site_id in self._active_incident_sites:
                if self._on_additional:
                    await self._on_additional(site_id, failures)
                continue
            self._active_incident_sites.add(site_id)
            family = self._family_of(failures[0])
            await self._on_fault(site_id, family, failures, trigger[site_id])

    def _family_of(self, failure: dict) -> str:
        for rules in self._rules_by_signal.values():
            for r in rules:
                if r["alarm_code"] == failure["code"]:
                    return r["family"]
        raise KeyError(f"no alarm rule for fired failure {failure['code']}")

    def _evaluate(self, sig: dict[str, Any]):
        """Yield (failure, rule, triggered_at_iso) for every rule that fires."""
        now = _ts(sig["ts"])
        value = float(sig["value"]) if not isinstance(sig["value"], bool) else float(sig["value"])
        for rule in self._rules_by_signal.get(sig["signal"], []):
            key = (sig["site_id"], rule["alarm_code"])
            breach = _OPS[rule["threshold_op"]](value, rule["threshold_value"])
            state = self._states.get(key)
            if not breach:
                self._states.pop(key, None)  # condition cleared -> debounce restarts
                continue
            if state is None:
                state = {"first_breach": now, "fired": False, "first_iso": sig["ts"]}
                self._states[key] = state
                if rule["debounce_s"] > 0:
                    continue
            if state["fired"]:
                continue  # already fired for this episode -> no duplicate
            if now - state["first_breach"] >= rule["debounce_s"]:
                state["fired"] = True
                yield (
                    {
                        # failure `id` is assigned by the orchestrator (F1, F2, ...)
                        "code": rule["alarm_code"],
                        "severity": rule["severity_default"],
                        "equipment": sig.get("equipment_id") or rule["subfamily"],
                        "metric": sig["signal"],
                        "value": sig["value"],
                        "first_seen": state["first_iso"],
                    },
                    rule,
                    sig["ts"],
                )
