"""Inventory Lookup tool (BE.8) — part reference -> real stock row.

No-stock and unknown-part cases are handled and flagged (in_stock=False,
eta_hours = restock lead time when known) — acceptance criterion.
"""
from contracts import InventoryLine, InventoryMatch, InventoryQuery

from backend.app.seeds import Seeds


class InventoryLookupTool:
    name = "inventory_lookup"
    input_schema = InventoryQuery.model_json_schema()

    def __init__(self, seeds: Seeds) -> None:
        self._seeds = seeds

    async def __call__(self, payload: InventoryQuery) -> InventoryMatch:
        lines: list[InventoryLine] = []
        for part in payload.part_numbers:
            row = self._seeds.inventory.get(part)
            if row is None:  # unknown part — flagged, never silently dropped
                lines.append(InventoryLine(part_number=part, in_stock=False, quantity=0,
                                           warehouse_id=None, eta_hours=None))
                continue
            in_stock = row["stock_qty"] > 0
            lines.append(InventoryLine(
                part_number=part,
                in_stock=in_stock,
                quantity=row["stock_qty"],
                warehouse_id=row["warehouse_id"],  # unit_price_usd stays on the seed row
                eta_hours=None if in_stock else float(row["lead_time_h"]),
            ))
        return InventoryMatch(incident_id=payload.incident_id, matches=lines)
