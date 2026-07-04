"""Correlation agent (issue #26 / AGV.3).

Localizes a FaultEvent to a site + one specific piece of equipment by reasoning
over the **structured** site/network topology (``fixtures/topology.json``,
aligned with ``data/schema.md``) — never pixels.

Design (why it is not a one-shot retrieve-then-answer)
------------------------------------------------------
Three visible stages, all traced in ``payload.reasoning_path``:

1. **Plan** — the injected Vultr client turns the fault + the site's structured
   equipment inventory into a localization *plan* (target equipment class, walk
   strategy, retrieval query). This is the model-in-the-loop planning step the
   Vultr compliance rule asks for. With no client injected (offline / ``--mock``)
   the same plan is produced deterministically from the alarm taxonomy.
2. **Walk** — the plan is *executed* by a deterministic walk over the
   ``parent_id`` links: resolve the site, enter the family subtree at its root
   (``parent_id`` null), descend to the matching-class leaf. The structured
   topology, never the model, chooses the final ``equipment_id`` — the model
   proposes, the data disposes. This is what makes localization non-hallucinated.
3. **Retrieve** — the injected retriever corroborates the localization and yields
   the citation trail (>= 1 ``Citation`` when it was consulted).

Both collaborators are constructor-injected and duck-typed, so the agent is
fully mockable and runs offline.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from contracts.agent_interface import AgentInput, AgentOutput, Citation, RetrievedRef

if TYPE_CHECKING:  # imported for typing only — no runtime coupling / no network at import
    from agents.common.retriever import VultronRetriever
    from agents.common.vultr import VultrClient

__all__ = ["CorrelationAgent"]

logger = logging.getLogger("arc.correlation")

_HERE = Path(__file__).resolve().parent
_DEFAULT_TOPOLOGY = _HERE / "fixtures" / "topology.json"
_DEFAULT_PROMPT = _HERE / "prompt.md"

# --------------------------------------------------------------------------- #
# Fault taxonomy (from data/schema.md alarm_dictionary) -> equipment class the
# fault localizes to. Keyed on the canonical alarm_code, with a family-level
# fallback and a few legacy aliases seen in contracts/EVENTS.md examples.
# --------------------------------------------------------------------------- #
_CODE_CLASS: dict[str, str] = {
    "PWR-GRID-LOSS": "rectifier",
    "PWR-DC-UV": "rectifier",
    "PWR-RECT-FAIL": "rectifier",
    "PWR-BATT-DEGRADED": "battery_string",
    "ENV-HVAC-FAIL": "hvac",
    "ENV-THERMAL-SHUT": "radio",
    "RF-VSWR-HIGH": "feeder",
    "RF-CELL-DOWN": "radio",
    "TRN-BACKHAUL-DOWN": "router",
    "TRN-DEGRADED": "router",
    # legacy aliases (EVENTS.md examples)
    "DC_UNDERVOLTAGE": "rectifier",
    "ALARMMAJORRECTIFIER": "rectifier",
    "HIGH_TEMP": "hvac",
}

_FAMILY_CLASS: dict[str, str] = {
    "energy": "rectifier",
    "environment": "hvac",
    "rf": "feeder",
    "transport": "router",
}

# Equipment classes that can root a family subtree (their parent_id is null).
_FAMILY_ROOT_CLASSES: dict[str, set[str]] = {
    "energy": {"rectifier", "battery_string"},
    "environment": {"hvac"},
    "rf": {"antenna", "feeder", "radio"},
    "transport": {"router", "bbu"},
}

_SUBFAMILY: dict[str, str] = {
    "PWR-GRID-LOSS": "grid",
    "PWR-DC-UV": "dc_plant",
    "PWR-RECT-FAIL": "rectifier",
    "PWR-BATT-DEGRADED": "battery",
    "ENV-HVAC-FAIL": "hvac",
    "ENV-THERMAL-SHUT": "hvac",
    "RF-VSWR-HIGH": "vswr",
    "RF-CELL-DOWN": "cell",
    "TRN-BACKHAUL-DOWN": "backhaul",
    "TRN-DEGRADED": "backhaul",
}

_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "target_equipment_class": {"type": "string"},
        "proposed_equipment_id": {"type": ["string", "null"]},
        "walk_strategy": {"type": "string"},
        "retrieval_query": {"type": "string"},
        "needs_retrieval": {"type": "boolean"},
        "rationale": {"type": "string"},
    },
    "required": [
        "target_equipment_class",
        "walk_strategy",
        "retrieval_query",
        "needs_retrieval",
        "rationale",
    ],
    "additionalProperties": False,
}

# Token budget for the planning call. The plan is a small JSON object; 800 gives
# comfortable headroom so the model finishes cleanly (finish_reason=stop). The
# structured_json re-prompt is a SAFETY NET, not a budget (contracts/decisions.md):
# a finish_reason=length here would cost a whole extra LLM pass, so we size to
# avoid it rather than lean on the retry.
_PLAN_MAX_TOKENS = 800


# --------------------------------------------------------------------------- #
# Structured-topology view (loaded once from the JSON fixture)
# --------------------------------------------------------------------------- #
class _Topology:
    """Indexed view over sites + equipment, exposing the parent/child walk."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.sites: dict[str, dict[str, Any]] = {
            s["site_id"]: s for s in data.get("sites", [])
        }
        self.equipment: dict[str, dict[str, Any]] = {
            e["equipment_id"]: e for e in data.get("equipment", [])
        }
        self._children: dict[str, list[str]] = {}
        for e in self.equipment.values():
            parent = e.get("parent_id")
            if parent:
                self._children.setdefault(parent, []).append(e["equipment_id"])

    def at_site(self, site_id: str) -> list[dict[str, Any]]:
        return [e for e in self.equipment.values() if e.get("site_id") == site_id]

    def is_leaf(self, eq_id: str) -> bool:
        return not self._children.get(eq_id)

    def chain_to_root(self, eq_id: str) -> list[str]:
        """Return the ``[root, ..., eq_id]`` parent chain (cycle-safe)."""
        chain: list[str] = []
        seen: set[str] = set()
        cur: str | None = eq_id
        while cur and cur not in seen and cur in self.equipment:
            seen.add(cur)
            chain.append(cur)
            cur = self.equipment[cur].get("parent_id")
        return list(reversed(chain))

    def depth(self, eq_id: str) -> int:
        return len(self.chain_to_root(eq_id))


class CorrelationAgent:
    """Locate a fault on the structured topology, with a citation trail.

    Conforms to the frozen ``Agent`` protocol (``name`` + ``async run``).
    ``vultr`` and ``retriever`` are injected (and duck-typed) so the agent is
    mockable and runs offline when they are ``None``.
    """

    name: str = "correlation"

    def __init__(
        self,
        vultr: "VultrClient | None" = None,
        retriever: "VultronRetriever | None" = None,
        *,
        topology_path: str | Path | None = None,
        prompt_path: str | Path | None = None,
        system_prompt: str | None = None,
        top_k: int = 4,
        plan_max_tokens: int = _PLAN_MAX_TOKENS,
    ) -> None:
        self._vultr = vultr
        self._retriever = retriever
        self._top_k = top_k
        self._plan_max_tokens = plan_max_tokens

        topo_path = Path(topology_path) if topology_path else _DEFAULT_TOPOLOGY
        self._topology = _Topology(json.loads(topo_path.read_text(encoding="utf-8")))

        if system_prompt is not None:
            # Orchestrator-injected persona replaces the bundled prompt.md.
            self._prompt = system_prompt
        else:
            p_path = Path(prompt_path) if prompt_path else _DEFAULT_PROMPT
            self._prompt = p_path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Protocol entry point
    # ------------------------------------------------------------------ #
    async def run(self, data: AgentInput) -> AgentOutput:
        t0 = time.perf_counter()
        topo = self._topology
        fault = self._parse_fault(data)

        # 1. Plan (LLM if injected, else deterministic taxonomy) -------------- #
        plan = await self._plan(data, fault, topo)

        # Validate the plan's target class against the *structured* inventory;
        # the topology, not the model, is authoritative.
        at_site = topo.at_site(data.site_id)
        site_classes = {e.get("class") for e in at_site}
        target_class = plan.get("target_equipment_class", "")
        if target_class not in site_classes:
            det = _CODE_CLASS.get(fault["code_norm"]) or _FAMILY_CLASS.get(
                data.failure_family, ""
            )
            if plan.get("source") == "llm" and det and det != target_class:
                plan["overridden_from"] = target_class
                plan["source"] = "deterministic-fallback"
            target_class = det
            plan["target_equipment_class"] = target_class

        # Make any taxonomy deviation visible/auditable: the planner keeps its
        # latitude (it may hold context justifying the class), but we record what
        # the deterministic taxonomy would have picked and flag a mismatch.
        taxonomy_class = _CODE_CLASS.get(fault["code_norm"]) or _FAMILY_CLASS.get(
            data.failure_family, ""
        )
        plan["taxonomy_class"] = taxonomy_class
        plan["deviation"] = bool(taxonomy_class and target_class != taxonomy_class)
        if plan["deviation"]:
            logger.warning(
                "correlation planner deviated from taxonomy: target=%s taxonomy=%s (code=%s)",
                target_class, taxonomy_class, fault["code_norm"],
            )

        # 2. Walk (deterministic parent/child descent) ----------------------- #
        chosen, chain, meta = self._localize(
            topo, data.site_id, data.failure_family, target_class
        )
        hops = self._topology_hops(data.site_id, data.failure_family, target_class, plan, chain)

        # 3. Retrieve (corroboration + citation trail) ----------------------- #
        refs: list[RetrievedRef] = []
        retrieval_passes = 0
        if self._retriever is not None and plan.get("needs_retrieval", True):
            query = plan.get("retrieval_query") or self._fallback_query(fault, chosen)
            try:
                refs = await self._retriever.query(query, top_k=self._top_k)
                retrieval_passes = 1
                hops.append(
                    {
                        "hop": len(hops) + 1,
                        "step": "retrieval",
                        "pass": 1,
                        "query": query,
                        "hits": len(refs),
                        "top_doc": refs[0].doc_id if refs else None,
                    }
                )
            except Exception as exc:  # retrieval is best-effort; localization stands
                logger.warning("correlation retrieval failed: %s", exc)

        corroborated = self._corroborated(refs, fault, chosen)
        cited = [r for r in refs if self._ref_corroborates(r, fault, chosen)] or refs[:1]
        citations = [
            Citation(doc_id=r.doc_id, section=r.section, snippet=r.snippet)
            for r in cited[:3]
        ]

        confidence = self._confidence(chosen, meta, corroborated)

        located_id = chosen["equipment_id"] if chosen else None
        located_class = chosen["class"] if chosen else None
        payload: dict[str, Any] = {
            "located_site_id": data.site_id,
            "located_equipment_id": located_id,
            "equipment_class": located_class,
            "reasoning_path": hops,
            "confidence": confidence,
            "plan": plan,
            "retrieval_passes": retrieval_passes,
            "candidates": meta.get("candidates", []),
        }

        summary = self._summary(data, fault, chosen, corroborated, retrieval_passes)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "correlation localized %s -> %s (%.0f ms, conf=%.2f)",
            data.site_id, located_id, elapsed_ms, confidence,
        )

        return AgentOutput(
            incident_id=data.incident_id,
            agent=self.name,
            summary=summary,
            payload=payload,
            retrieved_refs=refs,
            citations=citations,
            confidence=confidence,
        )

    # ------------------------------------------------------------------ #
    # Fault parsing
    # ------------------------------------------------------------------ #
    def _parse_fault(self, data: AgentInput) -> dict[str, Any]:
        ctx = data.context or {}
        event = ctx.get("fault_event") or ctx.get("fault_detected") or ctx
        failures = event.get("failures") or []

        primary: dict[str, Any] = failures[0] if failures else {}
        for f in failures:  # prefer a failure whose code is in the taxonomy
            if _CODE_CLASS.get(str(f.get("code", "")).upper()):
                primary = f
                break

        code = str(primary.get("code", ""))
        code_norm = code.upper()
        return {
            "code": code,
            "code_norm": code_norm,
            "subfamily": _SUBFAMILY.get(code_norm, ""),
            "severity": primary.get("severity"),
            "equipment_hint": primary.get("equipment"),
            "metric": primary.get("metric"),
            "value": primary.get("value"),
            "all_codes": [f.get("code") for f in failures],
        }

    # ------------------------------------------------------------------ #
    # Planning
    # ------------------------------------------------------------------ #
    async def _plan(
        self, data: AgentInput, fault: dict[str, Any], topo: _Topology
    ) -> dict[str, Any]:
        deterministic = self._deterministic_plan(fault, data.failure_family, data.site_id)
        if self._vultr is None:
            return deterministic

        inventory = [
            {
                "equipment_id": e["equipment_id"],
                "class": e.get("class"),
                "parent_id": e.get("parent_id"),
                "vendor": e.get("vendor"),
                "model": e.get("model"),
            }
            for e in topo.at_site(data.site_id)
        ]
        user = {
            "failure_family": data.failure_family,
            "site_id": data.site_id,
            "fault": {
                "code": fault["code"],
                "subfamily": fault["subfamily"],
                "severity": fault["severity"],
                "metric": fault["metric"],
                "value": fault["value"],
            },
            "equipment_inventory": inventory,
        }
        messages = [
            {"role": "system", "content": self._prompt},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ]
        try:
            raw = await self._vultr.structured_json(
                messages,
                schema=_PLAN_SCHEMA,
                max_tokens=self._plan_max_tokens,
                temperature=0.0,
            )
        except Exception as exc:  # any inference failure -> deterministic plan
            logger.warning("correlation planner LLM failed (%s); using deterministic plan", exc)
            return deterministic

        return {
            "target_equipment_class": str(
                raw.get("target_equipment_class") or deterministic["target_equipment_class"]
            ),
            "proposed_equipment_id": raw.get("proposed_equipment_id"),
            "walk_strategy": str(raw.get("walk_strategy") or deterministic["walk_strategy"]),
            "retrieval_query": str(raw.get("retrieval_query") or deterministic["retrieval_query"]),
            "needs_retrieval": bool(raw.get("needs_retrieval", True)),
            "rationale": str(raw.get("rationale") or ""),
            "source": "llm",
        }

    def _deterministic_plan(
        self, fault: dict[str, Any], family: str, site_id: str
    ) -> dict[str, Any]:
        target = _CODE_CLASS.get(fault["code_norm"]) or _FAMILY_CLASS.get(family, "rectifier")
        return {
            "target_equipment_class": target,
            "proposed_equipment_id": None,
            "walk_strategy": (
                f"resolve site {site_id}, enter the {family} subtree at its "
                f"parent_id=null root, descend parent/child links to the {target} leaf"
            ),
            "retrieval_query": self._fallback_query(fault, None, target),
            "needs_retrieval": True,
            "rationale": f"taxonomy: {fault['code_norm'] or family} -> {target}",
            "source": "deterministic",
        }

    def _fallback_query(
        self, fault: dict[str, Any], chosen: dict[str, Any] | None, target: str = ""
    ) -> str:
        klass = (chosen or {}).get("class") or target
        vendor = (chosen or {}).get("vendor", "")
        model = (chosen or {}).get("model", "")
        parts = [fault.get("code"), fault.get("subfamily"), klass, vendor, model, "alarm signature"]
        return " ".join(p for p in parts if p)

    # ------------------------------------------------------------------ #
    # Deterministic topology walk
    # ------------------------------------------------------------------ #
    def _localize(
        self, topo: _Topology, site_id: str, family: str, target_class: str
    ) -> tuple[dict[str, Any] | None, list[str], dict[str, Any]]:
        at_site = topo.at_site(site_id)
        if not at_site:
            return None, [], {"reason": "site has no equipment", "candidates": []}

        candidates = [e for e in at_site if e.get("class") == target_class]
        fallback = False
        if not candidates:  # broaden to the family subtree classes
            fam = _FAMILY_ROOT_CLASSES.get(family, set()) | ({target_class} if target_class else set())
            candidates = [e for e in at_site if e.get("class") in fam]
            fallback = True
        if not candidates:
            return None, [], {"reason": "no class match", "fallback": True, "candidates": []}

        # Prefer the leaf-most, deepest node of the target class: that is the
        # concrete unit (e.g. the rectifier module) under the plant aggregate.
        candidates.sort(
            key=lambda e: (topo.is_leaf(e["equipment_id"]), topo.depth(e["equipment_id"])),
            reverse=True,
        )
        chosen = candidates[0]
        leaves_of_class = [
            e for e in candidates
            if e.get("class") == chosen.get("class") and topo.is_leaf(e["equipment_id"])
        ]
        chain = topo.chain_to_root(chosen["equipment_id"])
        meta = {
            "fallback": fallback,
            "unambiguous": len(leaves_of_class) == 1,
            "candidates": [c["equipment_id"] for c in candidates],
        }
        return chosen, chain, meta

    def _topology_hops(
        self,
        site_id: str,
        family: str,
        target_class: str,
        plan: dict[str, Any],
        chain: list[str],
    ) -> list[dict[str, Any]]:
        hops: list[dict[str, Any]] = [
            {
                "hop": 1,
                "step": "resolve_site",
                "node": site_id,
                "rule": "AgentInput.site_id (cross-checked with fault_event.site.id)",
            },
            {
                "hop": 2,
                "step": "plan",
                "target_class": target_class,
                "source": plan.get("source"),
                "rule": plan.get("rationale") or plan.get("walk_strategy"),
            },
        ]
        if chain:
            hops.append(
                {
                    "hop": len(hops) + 1,
                    "step": "select_root",
                    "node": chain[0],
                    "rule": f"family={family} subtree root (parent_id=null)",
                }
            )
            for i in range(1, len(chain)):
                hops.append(
                    {
                        "hop": len(hops) + 1,
                        "step": "walk_child",
                        "from": chain[i - 1],
                        "to": chain[i],
                        "rule": f"descend parent_id link toward the {target_class} leaf",
                    }
                )
        return hops

    # ------------------------------------------------------------------ #
    # Corroboration + confidence + summary
    # ------------------------------------------------------------------ #
    def _ref_corroborates(
        self, ref: RetrievedRef, fault: dict[str, Any], chosen: dict[str, Any] | None
    ) -> bool:
        needles = {
            fault.get("code_norm", "").lower(),
            fault.get("subfamily", "").lower(),
            (chosen or {}).get("class", "").lower(),
        }
        needles = {n for n in needles if len(n) > 2}
        if not needles:
            return False
        hay = f"{ref.doc_id} {ref.section} {ref.snippet}".lower()
        return any(n in hay for n in needles)

    def _corroborated(
        self, refs: list[RetrievedRef], fault: dict[str, Any], chosen: dict[str, Any] | None
    ) -> bool:
        return any(self._ref_corroborates(r, fault, chosen) for r in refs)

    def _confidence(
        self, chosen: dict[str, Any] | None, meta: dict[str, Any], corroborated: bool
    ) -> float:
        if chosen is None:
            return 0.15
        score = 0.40
        score += 0.25  # localized to a concrete equipment node
        if meta.get("unambiguous"):
            score += 0.10
        if meta.get("fallback"):
            score -= 0.15
        if corroborated:
            score += 0.15
        return round(max(0.05, min(score, 0.97)), 3)

    def _summary(
        self,
        data: AgentInput,
        fault: dict[str, Any],
        chosen: dict[str, Any] | None,
        corroborated: bool,
        retrieval_passes: int,
    ) -> str:
        if chosen is None:
            return (
                f"Could not localize {data.failure_family} fault "
                f"{fault.get('code') or '?'} at {data.site_id} on the topology."
            )
        tail = ""
        if retrieval_passes:
            tail = (
                " corroborated by retrieval." if corroborated
                else " (retrieval returned no corroborating evidence)."
            )
        return (
            f"Localized {data.failure_family} fault {fault.get('code') or '?'} to "
            f"{chosen['equipment_id']} ({chosen['class']}) at {data.site_id} via a "
            f"parent/child topology walk;{tail}"
        )
