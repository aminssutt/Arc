"""Evaluation of the difficulty-routed matcher (mirrors validation/EVAL_SPEC.md).

Not ML training (25 employees is far too small); this verifies the deterministic
routing on labeled scenarios and reports the honest top-1 accuracy, plus the
tier-routing and zone-fallback behaviors and the negative controls.

Metric: top-1 exact = the single notified employee equals the labeled expectation.
"""

import json
import pathlib

from agents.responder_matching import match_responder

ROOT = pathlib.Path(__file__).resolve().parents[3]
ROSTER = json.loads((ROOT / "data" / "employees.json").read_text(encoding="utf-8"))
EVAL = json.loads((pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "eval_faults.json").read_text(encoding="utf-8"))
AS_OF = EVAL["as_of"]
BY_ID = {e["employee_id"]: e for e in ROSTER}


def test_top1_exact_on_all_scenarios():
    misses = []
    for s in EVAL["scenarios"]:
        r = match_responder(ROSTER, s["fault"], as_of=AS_OF)
        got = r["employee_id"] if r else None
        if got != s["expect"]:
            misses.append(f"{s['id']}: expected {s['expect']}, got {got}")
    assert not misses, "top-1 misses: " + "; ".join(misses)


def test_scenario_tier_and_zone_flags():
    for s in EVAL["scenarios"]:
        r = match_responder(ROSTER, s["fault"], as_of=AS_OF)
        assert r is not None, s["id"]
        if "expect_tier" in s:
            assert r["tier"] == s["expect_tier"], f"{s['id']}: tier {r['tier']} != {s['expect_tier']}"
        assert r["out_of_zone"] == s["expect_out_of_zone"], f"{s['id']}: out_of_zone {r['out_of_zone']}"


def test_difficulty_routing_direction():
    # Simple scenarios must land a lower level than complex scenarios (on average).
    simple = [match_responder(ROSTER, s["fault"], as_of=AS_OF)["level"]
              for s in EVAL["scenarios"] if s["fault"].get("code", "").endswith(("FUSE-BLOWN", "ROUTER-FAIL"))]
    complex_ = [match_responder(ROSTER, s["fault"], as_of=AS_OF)["level"]
                for s in EVAL["scenarios"] if "GRID-LOSS" in s["fault"].get("code", "") or "BACKHAUL-DOWN" in s["fault"].get("code", "") or "VSWR" in s["fault"].get("code", "")]
    assert max(simple) < min(complex_), "a simple task routed to a higher level than a complex one"


def test_negative_controls():
    for nc in EVAL["negative_controls"]:
        r = match_responder(ROSTER, nc["fault"], as_of=AS_OF)
        if nc.get("expect_escalate"):
            assert r is None, f"{nc['id']}: expected escalate, got {r}"
        if nc.get("must_not_notify"):
            assert r is None or r["employee_id"] != nc["must_not_notify"], f"{nc['id']}: paged {nc['must_not_notify']}"


def test_every_expected_employee_is_real_and_available():
    for s in EVAL["scenarios"]:
        emp = BY_ID.get(s["expect"])
        assert emp is not None, f"{s['id']}: unknown {s['expect']}"
        assert emp["status"] == "available", f"{s['id']}: {s['expect']} not available"
