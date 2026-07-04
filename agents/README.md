# /agents

- **Owner:** vgtray + aminssutt (split below — the two agentic devs never edit the same file)
- **Goes here:** specialized agents, the shared Vultr/retriever clients (`common/`), and orchestration glue.
- **Does NOT go here:** FastAPI/runtime (`/backend`), retrieval corpus (`/data`), UI (`/frontend`, `/ios`).
- **Requires Python ≥ 3.12 — see root README / `.python-version`.**

## Split
- **vgtray:** `correlation/`, `root_cause/`, `common/vultr.py`, `common/retriever.py`
- **aminssutt:** `validation/`, `remediation/`, `cost_inventory/`, `orchestration/`
- `common/` base is defined in phase 0 and changed **only with a Discord heads-up**.
