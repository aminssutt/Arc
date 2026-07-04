"""Cost Engine tool (BE.7) — deterministic intervention cost + cost avoided.

Formula (documented + unit-tested; all inputs are seeded euro-cent integers):
  repair_cost   = Σ part unit prices + labor_rate × LABOR_HOURS + truck_roll_flat
  cost avoided  = downtime_cost/min × restore_target_min × priority_weight
                  + sla_breach_penalty            (the breach the fix prevents)
Outputs are euros (cents / 100), currency EUR.
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
        parts_cents = sum(
            s.inventory[p]["unit_price_cents"] for p in payload.parts if p in s.inventory)
        labor_cents = int(s.cost_params["labor_rate"]["value_cents"] * LABOR_HOURS)
        truck_cents = s.cost_params["truck_roll_flat"]["value_cents"]
        repair_cents = parts_cents + labor_cents + truck_cents

        site = s.sites.get(payload.site_id, {})
        sla = s.sla_params.get(site.get("sla_tier", ""), {"restore_target_min": 240, "priority_weight": 1.0})
        downtime_cents = int(
            s.cost_params["downtime_cost"]["value_cents"]
            * sla["restore_target_min"] * sla["priority_weight"])
        avoided_cents = downtime_cents + s.cost_params["sla_breach_penalty"]["value_cents"]

        return CostReport(
            incident_id=payload.incident_id,
            repair_cost=repair_cents / 100,
            downtime_cost_avoided=avoided_cents / 100,
            currency="EUR",
            breakdown={
                "parts": parts_cents / 100,
                "labor": labor_cents / 100,
                "truck_roll": truck_cents / 100,
                "downtime_avoided": downtime_cents / 100,
                "sla_penalty_avoided": s.cost_params["sla_breach_penalty"]["value_cents"] / 100,
            },
        )
