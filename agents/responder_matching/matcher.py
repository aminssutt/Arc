"""Deterministic responder matcher -- route ONE employee to a diagnosed fault.

Owner: aminssutt. Feature: employee-matching.

Pure, side-effect-free, explainable (no LLM, no network). It picks the SINGLE
best-fit **available** responder, routing by **task difficulty**:

- **simple**  -> the least-experienced *competent* person (juniors/newcomers gain
  experience);
- **complex** -> the most-experienced / best-adapted person;
- **medium**  -> a mid-level person.

**Zone workflow is preserved**: candidates in the site's own region win, EXCEPT
when nobody eligible is available in-zone -- then the best out-of-zone responder
is picked (flagged ``out_of_zone``). Competence is a hard gate (you can't send a
fibre tech to a rectifier fault, however junior-friendly the task).

Score among eligible candidates:
    score = 0.5 * competence          # skill/family fit for THIS fault
          + 0.5 * difficulty_fit      # how well the person's LEVEL fits the task

``as_of`` is passed in (never ``date.today()``) so results are reproducible.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

REFERENCE_DATE = "2026-07-04"

FAMILY_SKILLS: dict[str, set[str]] = {
    "energy": {"power", "rectifier", "battery", "genset", "fuse"},
    "environment": {"hvac", "thermal", "cooling", "water", "intrusion"},
    "rf": {"rf", "antenna", "feeder", "gps", "radio"},
    "transport": {"transport", "backhaul", "router", "fiber", "microwave"},
}

CODE_SKILLS: dict[str, set[str]] = {
    "PWR-DC-UV": {"power", "rectifier"}, "PWR-RECT-FAIL": {"power", "rectifier"},
    "PWR-GRID-LOSS": {"power", "rectifier"}, "PWR-BATT-DEGRADED": {"power", "battery"},
    "PWR-FUSE-BLOWN": {"power", "fuse"}, "ENV-HVAC-FAIL": {"hvac"},
    "ENV-THERMAL-SHUT": {"thermal", "hvac"}, "ENV-WATER": {"water"},
    "RF-VSWR-HIGH": {"rf", "feeder", "antenna"}, "RF-CELL-DOWN": {"rf", "radio"},
    "RF-GPS-LOSS": {"gps"}, "TRN-BACKHAUL-DOWN": {"backhaul", "fiber", "transport"},
    "TRN-DEGRADED": {"transport", "microwave"}, "TRN-ROUTER-FAIL": {"router", "transport"},
}

# How hard each fault is -> drives which experience level it should route to.
CODE_DIFFICULTY: dict[str, str] = {
    "PWR-FUSE-BLOWN": "simple", "TRN-ROUTER-FAIL": "simple", "RF-GPS-LOSS": "simple",
    "PWR-DC-UV": "medium", "PWR-BATT-DEGRADED": "medium", "ENV-HVAC-FAIL": "medium",
    "RF-CELL-DOWN": "medium", "TRN-DEGRADED": "medium", "ENV-WATER": "medium",
    "PWR-GRID-LOSS": "complex", "PWR-RECT-FAIL": "complex", "ENV-THERMAL-SHUT": "complex",
    "RF-VSWR-HIGH": "complex", "TRN-BACKHAUL-DOWN": "complex",
}
DIFFICULTY_TARGET = {"simple": 0.15, "medium": 0.5, "complex": 0.9}

SENIORITY_CAP_YEARS = 12.0
TASKS_CAP = 120


def required_skills(fault: dict[str, Any]) -> set[str]:
    code = str(fault.get("code") or "").upper()
    if code in CODE_SKILLS:
        return set(CODE_SKILLS[code])
    req: set[str] = set()
    if fault.get("equipment_class"):
        req.add(fault["equipment_class"])
    fam_skills = FAMILY_SKILLS.get(fault.get("family", ""))
    if fam_skills:
        req.add(sorted(fam_skills)[0])
    return req or ({fault["family"]} if fault.get("family") else set())


def fault_difficulty(fault: dict[str, Any]) -> str:
    if fault.get("difficulty") in DIFFICULTY_TARGET:
        return fault["difficulty"]
    return CODE_DIFFICULTY.get(str(fault.get("code") or "").upper(), "medium")


def _years(start: str, as_of: str) -> float:
    return max((_dt.date.fromisoformat(as_of) - _dt.date.fromisoformat(start)).days / 365.25, 0.0)


def employee_level(emp: dict[str, Any], *, as_of: str) -> float:
    """Experience level 0..1 from seniority + number of tasks completed."""
    seniority = min(_years(emp["seniority_start"], as_of) / SENIORITY_CAP_YEARS, 1.0)
    tasks = min(emp.get("tasks_completed", len(emp.get("resolved", []))) / TASKS_CAP, 1.0)
    return round(0.5 * seniority + 0.5 * tasks, 4)


def competence(emp: dict[str, Any], fault: dict[str, Any]) -> tuple[float, list[str], bool]:
    req = required_skills(fault)
    matched = sorted(req & set(emp.get("skills", [])))
    overlap = len(matched) / len(req) if req else 0.0
    family_match = fault.get("family") in emp.get("families", [])
    return round(0.6 * overlap + 0.4 * (1.0 if family_match else 0.0), 4), matched, family_match


def is_eligible(emp: dict[str, Any], fault: dict[str, Any]) -> bool:
    """Hard competence gate: must be in the fault's family or share a needed skill."""
    _comp, matched, family_match = competence(emp, fault)
    return family_match or bool(matched)


def score_candidate(emp: dict[str, Any], fault: dict[str, Any], *, as_of: str) -> dict[str, Any]:
    comp, matched, family_match = competence(emp, fault)
    level = employee_level(emp, as_of=as_of)
    difficulty = fault_difficulty(fault)
    target = DIFFICULTY_TARGET[difficulty]
    fit = round(1.0 - abs(level - target), 4)
    score = round(0.5 * comp + 0.5 * fit, 4)

    tier = "junior" if level < 0.3 else ("senior" if level >= 0.7 else "confirmé")
    reason = (
        f"tâche {difficulty} → profil {tier} (niveau {level:.2f}, fit {fit:.2f}); "
        f"compétence {comp:.2f} ({','.join(matched) or 'famille ' + str(fault.get('family'))}); "
        f"zone {emp.get('region')}"
    )
    return {
        "employee_id": emp["employee_id"], "name": emp["name"], "role": emp.get("role", ""),
        "region": emp.get("region"), "score": score, "competence": comp, "level": level,
        "difficulty": difficulty, "difficulty_fit": fit, "tier": tier,
        "matched_skills": matched, "reason": reason,
    }


def rank_candidates(employees: list[dict[str, Any]], fault: dict[str, Any], *, as_of: str) -> list[dict[str, Any]]:
    """All eligible, available candidates, best-first (deterministic ties)."""
    scored = [
        score_candidate(e, fault, as_of=as_of)
        for e in employees
        if e.get("status") == "available" and is_eligible(e, fault)
    ]
    target = DIFFICULTY_TARGET[fault_difficulty(fault)]
    scored.sort(key=lambda c: (-c["score"], -c["competence"], abs(c["level"] - target), c["employee_id"]))
    return scored


def match_responder(
    employees: list[dict[str, Any]],
    fault: dict[str, Any],
    *,
    as_of: str = REFERENCE_DATE,
) -> dict[str, Any] | None:
    """Pick the SINGLE responder to notify (zone-preferred, difficulty-routed).

    Returns the chosen candidate dict with ``out_of_zone`` set, or ``None`` when
    nobody eligible is available anywhere (escalate). ``fault['region']`` (the
    site's region) drives the zone preference; omit it for a region-agnostic pick.
    """
    ranked = rank_candidates(employees, fault, as_of=as_of)
    if not ranked:
        return None

    site_region = fault.get("region") or fault.get("site_region")
    if site_region:
        in_zone = [c for c in ranked if c["region"] == site_region]
        if in_zone:
            return {**in_zone[0], "out_of_zone": False}
        # incompatibility: nobody available in-zone -> best out-of-zone responder
        return {**ranked[0], "out_of_zone": True}
    return {**ranked[0], "out_of_zone": False}
