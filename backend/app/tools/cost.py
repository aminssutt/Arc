"""Cost Engine tool (BE.7) — deterministic intervention cost + cost avoided.

Formula (documented + unit-tested; seeded USD decimal dollars, schema §6):
  repair_cost   = Σ part unit prices + labor_rate × LABOR_HOURS + truck_roll_flat
  cost avoided  = downtime_cost/min × restore_target_min × priority_weight
                  + sla_breach_penalty            (the breach the fix prevents)
Confirm-run cross-check (schema §6.1): 769.04 + 2×35.73 + 325.00 = 1165.50 USD.
"""
from contracts import CostQuery, CostReport

from backend.app.seeds import Seeds

LABOR_HOURS = 2.0  # standard field intervention block for the demo scenarios


class CostEngineTool:
    name = "cost_engine"
    input_schema = CostQuery.model_json_schema()

    def __init__(self, seeds: Seeds) -> None:
        self._seeds = seeds

    async def __call__(self, payload: CostQuery) -> CostReport:
        s = self._seeds
        parts_usd = sum(
            s.inventory[p]["unit_price_usd"] for p in payload.parts if p in s.inventory)
        labor_usd = round(s.cost_params["labor_rate"]["value_usd"] * LABOR_HOURS, 2)
        truck_usd = s.cost_params["truck_roll_flat"]["value_usd"]
        repair_usd = round(parts_usd + labor_usd + truck_usd, 2)

        site = s.sites.get(payload.site_id, {})
        sla = s.sla_params.get(site.get("sla_tier", ""), {"restore_target_min": 240, "priority_weight": 1.0})
        downtime_usd = round(
            s.cost_params["downtime_cost"]["value_usd"]
            * sla["restore_target_min"] * sla["priority_weight"], 2)
        avoided_usd = round(downtime_usd + s.cost_params["sla_breach_penalty"]["value_usd"], 2)

        return CostReport(
            incident_id=payload.incident_id,
            repair_cost=repair_usd,
            downtime_cost_avoided=avoided_usd,
            currency="USD",
            breakdown={
                "parts": round(parts_usd, 2),
                "labor": labor_usd,
                "truck_roll": truck_usd,
                "downtime_avoided": downtime_usd,
                "sla_penalty_avoided": s.cost_params["sla_breach_penalty"]["value_usd"],
            },
        )
