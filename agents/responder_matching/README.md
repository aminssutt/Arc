# agents/responder_matching — Employee ↔ fault matching + notification

**Owner:** aminssutt · **Feature:** employee-matching

When a fault is **diagnosed** (after Root-Cause: `failure_family` + equipment +
cause + difficulty), this component picks the **single** best employee to notify,
**routed by task difficulty** and respecting the **zone** workflow.

## Routing rules
- **Difficulty → level.** Each fault has a difficulty (`simple` / `medium` /
  `complex`, from `code` or explicit). Difficulty routes to an experience level:
  - **simple → junior/newcomer** (they gain experience),
  - **complex → most experienced / best-adapted**,
  - **medium → mid-level (confirmé)**.
- **Competence is a hard gate.** Only employees in the fault's family or with a
  required skill are eligible — a junior gets a *simple* task **in their domain**,
  never a random one.
- **Zone preserved, with fallback.** The responder in the site's own `region`
  wins; **except** when nobody eligible is available in-zone → the best
  out-of-zone responder is picked and flagged `out_of_zone` (the senior-in-zone-B
  case).
- **Only `available`** employees; if nobody eligible anywhere → **escalate**.

## Score (among eligible)
```
level = 0.5·min(seniority_years/12, 1) + 0.5·min(tasks_completed/120, 1)
score = 0.5·competence + 0.5·difficulty_fit      # difficulty_fit = 1 - |level - target|
                                                 # target: simple 0.15 / medium 0.5 / complex 0.9
```
Every pick carries an explainable `reason` (difficulty, tier, level, competence, zone).

## Data
`data/employees.json` (25 employees) adds to the roster: `region`,
`tasks_completed` (experience volume), on top of `role`, `skills`, `families`,
`seniority_start`, `resolved` history, `status`. Schema in `data/schema.md §8`.

## Evaluation (mirrors `validation/EVAL_SPEC.md` — not ML training)
8 labeled difficulty/zone scenarios + 2 negative controls. **top-1 exact = 8/8**;
tier + zone flags correct; simple tasks route strictly below complex tasks;
negative controls pass (off-domain lead never paged, unknown family → escalate).

| Scenario | route |
|---|---|
| simple energy in-zone | **junior** EMP-004 |
| complex energy in-zone | **senior** EMP-003 |
| complex energy, none in-zone | **senior out-of-zone** EMP-002 |
| medium energy in-zone | **mid-level** EMP-006 |

## Where it plugs in (proposed, not yet wired)
- Runs **after Root-Cause**; conforms to `contracts.Agent` → drops into the
  orchestrator registry; its `payload` (`notify` = the one employee id, plus
  `responder`, `difficulty`, `out_of_zone`, `alternatives`) rides the existing
  `agent_completed` event — **no change to the frozen event contract**.
- **Notification hookup (backend follow-up, coordinate with simerugby):** extend
  `PushService` to push to `payload.notify` (a single recipient), optionally a
  `responder_notified` event — that touches the frozen event schema, so kept out.

## Test (from repo root)
```bash
pip install -r contracts/requirements-dev.txt
python -m pytest agents/responder_matching/tests -q
```
