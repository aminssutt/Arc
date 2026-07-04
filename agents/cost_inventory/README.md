# agents/cost_inventory — Cost, Inventory & Dispatch agent

**Owner:** aminssutt · **Ticket:** AGA.3 (#30) · **Phase:** 2

Last step of Phase 2. Registers as **`cost_inventory_dispatch`** and drops into
the backend orchestrator registry in place of the stand-in. Calls the **three
real backend tools** via the frozen `contracts.Tool` protocol and emits the
**prioritized action report** with a citation trail.

## What it does
1. **Inventory Lookup** → match each part to a real seeded stock line (warehouse, qty, lead time).
2. **Cost Engine** → repair cost + **downtime cost avoided** (report priority driver).
3. **Crew Dispatch** → book a crew with the right skill/priority; flag conflicts.

The agent reasons; the tools compute. It never fabricates a price, stock line,
ETA, or crew id — every such value comes from a tool result. Cost figures are
**echoed** from the Cost Engine (never re-derived); `payload.totals_consistent`
verifies the report matches the engine's own breakdown.

## Contract
- Input `context` (as the backend orchestrator passes it): `parts` (`[{part_no}]`),
  `remediation_title`, `top_priority`. Also accepts the agents-lane shape
  (`findings.remediation.parts_needed`).
- Output `payload`: `cost` / `inventory` / `dispatch` (consumed by the backend
  `_assemble_report`) **plus** `tool_calls` (all 3 visible in events),
  `action_report` (diagnosis, actions, cost, part, crew, citations, honesty_notes),
  and `totals_consistent`.

## Tests (from repo root)
```bash
pip install -r contracts/requirements-dev.txt
python -m pytest agents/cost_inventory/tests -q
```
Unit tests use fake tools (offline); the integration test drives the **real**
`CostEngineTool`/`InventoryLookupTool`/`CrewDispatchTool` over the committed
seeds (`PN-RECT-48-2000` → 6 in stock @ WH-PAR-CENTRAL; repair 770 €, avoided 5450 €).
