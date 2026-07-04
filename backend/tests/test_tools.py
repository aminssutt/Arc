"""BE.7/8/9 acceptance: deterministic outputs for scenario inputs; no-stock and
no-crew cases handled and flagged; all callable through the frozen Tool protocol.
"""
from contracts import (CostQuery, DispatchRequest, InventoryQuery, Tool)


async def test_cost_engine_deterministic(tools):
    cost, _, _ = tools
    report = await cost(CostQuery(incident_id="I1", site_id="SITE-PAR-014",
                                  failure_family="energy", remediation="replace module",
                                  parts=["PN-RECT-48-2000"]))
    # parts 420.00 + labor 2h x 85.00 + truck 180.00 = 770.00 EUR
    assert report.repair_cost == 770.00
    # downtime 2.50/min x 120 min x 1.5 (gold) + 5000.00 penalty = 5450.00 EUR
    assert report.downtime_cost_avoided == 5450.00
    assert report.currency == "EUR"
    assert report.breakdown["parts"] == 420.00


async def test_inventory_stock_and_flags(tools):
    _, inventory, _ = tools
    match = await inventory(InventoryQuery(incident_id="I1", site_id="SITE-PAR-014",
                                           part_numbers=["PN-RECT-48-2000", "PN-DOES-NOT-EXIST"]))
    found, unknown = match.matches
    assert found.in_stock and found.quantity == 6 and found.warehouse_id == "WH-PAR-CENTRAL"
    assert not unknown.in_stock and unknown.quantity == 0   # flagged, not dropped


async def test_dispatch_books_then_conflicts(tools):
    _, _, dispatch = tools
    req = DispatchRequest(incident_id="I1", site_id="SITE-PAR-014",
                          skill="power", priority="P1", parts=[])
    first = await dispatch(req)
    assert first.booked and first.crew_id == "CREW-IDF-3"   # lowest ETA available in IDF-North
    second = await dispatch(req)                            # CREW-IDF-3 now on_job, IDF-5 seeded on_job
    assert not second.booked and second.crew_id == ""       # conflict case handled
    dispatch.release_all()
    third = await dispatch(req)
    assert third.booked                                     # reset restored only OUR booking


async def test_tools_satisfy_frozen_protocol(tools):
    for tool in tools:
        assert isinstance(tool, Tool)
        assert tool.name and isinstance(tool.input_schema, dict)
