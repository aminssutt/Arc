"""Deterministic responder matcher -- score employees against a diagnosed fault.

Owner: aminssutt. Feature: employee-matching.

Pure, side-effect-free scoring so it is trivially testable and explainable
(no LLM, no network). Given a fault (family + equipment_class + code) and the
employee roster, it returns the best-fit **available** responders, each with a
human-readable reason. An optional semantic re-rank can blend an injected
embedding score on top (see ``agent.py``); this module stays deterministic.

Score:
    score = W_SKILL     * skill_score        # skill/family fit for THIS fault
          + W_SENIORITY * seniority_score    # experience (years, capped)
          + W_HISTORY   * history_score       # has fixed similar faults before

``as_of`` is passed in (never ``date.today()``) so results are reproducible.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

REFERENCE_DATE = "2026-07-04"

# Canonical skill vocabulary per fault family (aligned with data/schema.md).
FAMILY_SKILLS: dict[str, set[str]] = {
    "energy": {"power", "rectifier", "battery", "genset", "fuse"},
    "environment": {"hvac", "thermal", "cooling", "water", "intrusion"},
    "rf": {"rf", "antenna", "feeder", "gps", "radio"},
    "transport": {"transport", "backhaul", "router", "fiber", "microwave"},
}

# Skills a specific alarm code demands (the strongest signal when known).
CODE_SKILLS: dict[str, set[str]] = {
    "PWR-DC-UV": {"power", "rectifier"},
    "PWR-RECT-FAIL": {"power", "rectifier"},
    "PWR-GRID-LOSS": {"power", "rectifier"},
    "PWR-BATT-DEGRADED": {"power", "battery"},
    "PWR-FUSE-BLOWN": {"power", "fuse"},
    "ENV-HVAC-FAIL": {"hvac"},
    "ENV-THERMAL-SHUT": {"thermal", "hvac"},
    "ENV-WATER": {"water"},
    "RF-VSWR-HIGH": {"rf", "feeder", "antenna"},
    "RF-CELL-DOWN": {"rf", "radio"},
    "RF-GPS-LOSS": {"gps"},
    "TRN-BACKHAUL-DOWN": {"backhaul", "fiber", "transport"},
    "TRN-DEGRADED": {"transport", "microwave"},
    "TRN-ROUTER-FAIL": {"router", "transport"},
}

W_SKILL, W_SENIORITY, W_HISTORY = 0.55, 0.15, 0.30
DEFAULT_MIN_SCORE = 0.25   # floor: below this a person is NOT a confident responder
SENIORITY_CAP_YEARS = 12.0
HISTORY_CAP = 3


def required_skills(fault: dict[str, Any]) -> set[str]:
    """The skills THIS fault demands: alarm code first, else equipment + family."""
    code = str(fault.get("code") or "").upper()
    if code in CODE_SKILLS:
        return set(CODE_SKILLS[code])
    req: set[str] = set()
    if fault.get("equipment_class"):
        req.add(fault["equipment_class"])
    fam_skills = FAMILY_SKILLS.get(fault.get("family", ""))
    if fam_skills:
        req.add(sorted(fam_skills)[0])  # deterministic primary skill
    return req or ({fault["family"]} if fault.get("family") else set())


def _years(start: str, as_of: str) -> float:
    s = _dt.date.fromisoformat(start)
    a = _dt.date.fromisoformat(as_of)
    return max((a - s).days / 365.25, 0.0)


def score_employee(emp: dict[str, Any], fault: dict[str, Any], *, as_of: str) -> tuple[float, dict[str, Any]]:
    """Return (score, detail) for one employee against one fault."""
    family = fault.get("family")
    req = required_skills(fault)
    emp_skills = set(emp.get("skills", []))
    matched = sorted(req & emp_skills)

    skill_overlap = len(matched) / len(req) if req else 0.0
    family_match = 1.0 if family in emp.get("families", []) else 0.0
    skill_score = 0.6 * skill_overlap + 0.4 * family_match

    years = _years(emp["seniority_start"], as_of)
    seniority_score = min(years / SENIORITY_CAP_YEARS, 1.0)

    similar = sum(
        1 for r in emp.get("resolved", [])
        if r.get("family") == family
        and (r.get("equipment_class") == fault.get("equipment_class") or r.get("code") == fault.get("code"))
    )
    history_score = min(similar / HISTORY_CAP, 1.0)

    score = W_SKILL * skill_score + W_SENIORITY * seniority_score + W_HISTORY * history_score

    reason = (
        f"{'famille ' + str(family) if family_match else 'hors-famille'}; "
        f"skills {len(matched)}/{len(req)}"
        + (f" ({','.join(matched)})" if matched else "")
        + f"; {years:.1f} ans d'ancienneté; {similar} fix(es) similaire(s)"
    )
    detail = {
        "matched_skills": matched,
        "family_match": bool(family_match),
        "seniority_years": round(years, 1),
        "similar_fixes": similar,
        "reason": reason,
    }
    return round(score, 4), detail


def match_responders(
    employees: list[dict[str, Any]],
    fault: dict[str, Any],
    *,
    as_of: str = REFERENCE_DATE,
    top_k: int = 3,
    min_score: float = DEFAULT_MIN_SCORE,
    include_unavailable: bool = False,
) -> list[dict[str, Any]]:
    """Best-fit responders for ``fault``, available-only, above the confidence floor.

    Returns up to ``top_k`` entries sorted by score (ties: more similar fixes,
    then more seniority). An empty list means no confident responder -> escalate.
    """
    scored: list[dict[str, Any]] = []
    for emp in employees:
        if not include_unavailable and emp.get("status") != "available":
            continue
        score, detail = score_employee(emp, fault, as_of=as_of)
        if score < min_score:
            continue
        scored.append({
            "employee_id": emp["employee_id"],
            "name": emp["name"],
            "role": emp.get("role", ""),
            "status": emp.get("status"),
            "score": score,
            **detail,
        })
    scored.sort(key=lambda r: (r["score"], r["similar_fixes"], r["seniority_years"]), reverse=True)
    return scored[:top_k]
