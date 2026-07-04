# agents/orchestration — Orchestration glue (registry · plan · personas · harness)

**Owner:** aminssutt · **Ticket:** AGA.4 (#31) · **Phase:** 1

The agent-side glue the orchestrator runs on. It holds **no state** and does
**no diagnosis** — the backend runtime (#15, simerugby) owns the state machine
and plugs real agents into the same registry + plan.

## Pieces
| Module | What |
|---|---|
| `registry.py` | `AgentRegistry` — name → `contracts.Agent` lookup, validated at register time. |
| `plan.py` | `Phase` + `PHASE_PLAN` — the declarative agent sequence per phase. |
| `harness.py` | `run_phase` / `run_plan` — run a phase (or the plan) **offline**, threading each agent's `payload` into `context["findings"]`. |
| `personas.py` + `personas/*.md` | one reviewable system prompt per agent. |

## Phase plan
```
PHASE1     : correlation -> root_cause
HUMAN_LOOP : validation            (confirm | PIVOT back to PHASE1)
PHASE2     : remediation -> cost_inventory_dispatch
```

## Context threading contract
Each agent's `AgentOutput.payload` is stored under
`context["findings"][<agent name>]` and passed forward, so downstream agents see
all upstream findings (the accumulation slot the `AgentInput` contract reserves).

## Run / test (from repo root)
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r contracts/requirements-dev.txt
python -m agents.orchestration.harness                # PHASE1 offline with stub agents
python -m pytest agents/orchestration/tests -q
```

## Status / handoff
- Phase-1 chain runs **end-to-end offline** via the harness against stub agents
  (real `correlation` / `root_cause` are vgtray's lane; they drop into the
  registry unchanged when they land). The shipped `ValidationAgent` already runs
  through the harness in the HUMAN_LOOP step.
- **Personas for every planned agent** are drafted here for **vgtray review**
  (esp. `correlation.md`, `root_cause.md`). The full pivot loop + live wiring is
  INT.1/INT.3 (#47/#49).
