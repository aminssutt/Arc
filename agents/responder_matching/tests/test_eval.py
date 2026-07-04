"""Evaluation of the matcher (mirrors validation/EVAL_SPEC.md).

Not an ML training (6->25 employees is far too small); this tunes/verifies the
deterministic weights and reports honest top-k hit rates over a labeled set, with
a held-out split and negative controls.

Metrics: top-k hit = at least one CORRECT employee appears in the top-k match.
"""

import json
import pathlib

from agents.responder_matching import match_responders

ROOT = pathlib.Path(__file__).resolve().parents[3]
ROSTER = json.loads((ROOT / "data" / "employees.json").read_text(encoding="utf-8"))
EVAL = json.loads((pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "eval_faults.json").read_text(encoding="utf-8"))
AS_OF = EVAL["as_of"]
BY_ID = {e["employee_id"]: e for e in ROSTER}


def _hit_rate(cases, k):
    hits = 0
    for case in cases:
        got = {r["employee_id"] for r in match_responders(ROSTER, case["fault"], as_of=AS_OF, top_k=k)}
        if got & set(case["correct"]):
            hits += 1
    return hits / len(cases)


def test_calibration_top3_perfect():
    assert _hit_rate(EVAL["calibration"], k=3) == 1.0


def test_calibration_top2_strong():
    assert _hit_rate(EVAL["calibration"], k=2) >= 0.85


def test_holdout_top3_generalizes():
    # The honest, unseen number — must still land the right responder in the top-3.
    assert _hit_rate(EVAL["holdout"], k=3) >= 0.66


def test_negative_control_no_wrong_page():
    for nc in EVAL["negative_controls"]:
        got = {r["employee_id"] for r in match_responders(ROSTER, nc["fault"], as_of=AS_OF, top_k=3)}
        for banned in nc.get("must_not_notify", []):
            assert banned not in got, f"{nc['id']}: {banned} wrongly notified"
        for r in match_responders(ROSTER, nc["fault"], as_of=AS_OF, top_k=3):
            assert r["status"] == "available"          # unavailable never paged


def test_every_eval_label_is_a_real_available_employee():
    for case in EVAL["calibration"] + EVAL["holdout"]:
        for emp_id in case["correct"]:
            assert emp_id in BY_ID, f"{case['id']}: unknown employee {emp_id}"
            assert BY_ID[emp_id]["status"] == "available", f"{case['id']}: {emp_id} not available"
