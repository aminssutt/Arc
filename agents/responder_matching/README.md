# agents/responder_matching — Employee ↔ fault matching + notification

**Owner:** aminssutt · **Feature:** employee-matching

When a fault is **diagnosed** (after Root-Cause: `failure_family` + equipment +
cause), this component ranks the workforce and returns the **top 2–3 available
employees** best placed to fix it, each with an explainable reason, plus the
**notification decision** (`payload.notify` = employee ids to push to).

## Pieces
| File | What |
|---|---|
| `matcher.py` | Pure deterministic scoring (`score_employee`, `match_responders`). No LLM, no network. |
| `agent.py` | `ResponderMatchingAgent` — conforms to `contracts.Agent`; reads the fault from the envelope, matches, returns responders + `notify`. Optional semantic re-rank hook. |
| `fixtures/eval_faults.json` | Labeled `fault → correct responder(s)`: calibration + held-out split + negative controls. |
| `data/employees.json` | The roster (25 employees) — lives in `/data`, schema in `data/schema.md`. |

## Score
```
score = 0.55 · skill_score        # skill/family fit for THIS fault (alarm code → required skills)
      + 0.15 · seniority_score    # years since seniority_start, capped at 12y (as_of is passed in)
      + 0.30 · history_score      # count of prior resolved faults of the same family/equipment/code
```
Only `status == "available"` employees are eligible. A **confidence floor**
(`min_score = 0.25`) means an off-domain senior is **not** paged, and a family
nobody available covers returns **empty → escalate** (never a wrong page).

## Evaluation (mirrors `validation/EVAL_SPEC.md` — not ML training)
25 employees, 13 calibration faults + 3 held-out + 2 negative controls. Metric =
top-k hit (a correct employee in the top-k).

| Split | top-2 | top-3 |
|---|---|---|
| Calibration | 0.92 | **1.00** |
| Held-out (unseen) | 1.00 | **1.00** |

Negative controls pass: a high-seniority multi-domain lead with no RF skill is
not paged for an RF fault; unavailable specialists are never notified.

## Where it plugs in (proposed, not yet wired)
- Runs **after Root-Cause** (needs the diagnosed family/equipment/cause).
- Conforms to `contracts.Agent`, so it drops into the orchestrator registry like
  the other agents; its `payload` rides the existing `agent_completed` event —
  **no change to the frozen event contract**.
- **Notification hookup (backend follow-up, coordinate with simerugby):** extend
  `PushService` to push to `payload.notify` (cap 3) and, if wanted, add a
  `responders_notified` event — that touches the frozen event schema, so it's a
  contract change to agree on, kept OUT of this feature.

## Optional semantic re-rank
Inject `semantic_scorer` (async `(fault_text, [employee_text]) -> [0..1]`, e.g.
Vultr embeddings over the employees' free-text `resolved` history) to blend a
similarity signal. Default `None` → fully deterministic and offline.

## Test (from repo root)
```bash
pip install -r contracts/requirements-dev.txt
python -m pytest agents/responder_matching/tests -q
```
