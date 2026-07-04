# agents/validation — Validation agent (confirm / PIVOT)

**Owner:** aminssutt · **Ticket:** AGA.1 (#28) · **Phase:** 1

Sits in the human loop between Phase 1 (Correlation → Root-Cause) and Phase 2
(Remediation → Cost/Inventory/Dispatch). It fuses the field technician's
per-failure real/false verdict + real measurement with the **top cause
signature** and decides:

- **`confirmed`** → diagnosis holds; orchestrator proceeds to Phase 2.
- **`contradicted`** → field disagrees; emits a **pivot request** so the
  orchestrator re-runs Root-Cause with the measurement pinned as ground truth
  (the "telemetry lied" demo beat, DEMO RUN 2).

## Decision rule (deterministic)

Physical measurement is the strongest signal. If a measurement matching the
signature (`metric` + `point`) exists, it decides via `abnormal_when` +
`threshold`; otherwise the technician `verdict` decides. A verdict that
disagrees with a present measurement is surfaced honestly and caps confidence.

No LLM call is needed — so this lane is demo-able standalone against fixtures and
does **not** depend on the shared Vultr client (#24).

## Contract

- Input: `contracts.AgentInput` — carries `context["top_cause"]` (load-bearing
  `failure_id`, `label`, numeric `signature`) and `context["validation_event"]`
  (frozen `validation_event.schema.json`: `validations[]` + `measurements[]`).
- Output: `contracts.AgentOutput` — `payload.decision`, `payload.rationale`,
  and `payload.pivot_request` when contradicted; the signature `citation` rides
  in `citations`. See `agent.py` for the full `context` slice.

## Run / test (from repo root)

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r contracts/requirements-dev.txt         # pydantic + pytest + pytest-asyncio
python -m agents.validation.agent                     # prints confirm + pivot AgentOutput
python -m pytest agents/validation/tests -q
```

Fixtures in `fixtures/` mirror the two demo runs
(`GROUND_TRUTH_SCENARIOS.md`, INC-DEMO-001 confirm / INC-DEMO-002 pivot).
