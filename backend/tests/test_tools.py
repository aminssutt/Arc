"""BE.7/8/9 acceptance: deterministic outputs for scenario inputs; no-stock and
no-crew cases handled and flagged; all callable through the frozen Tool protocol.
"""
from contracts import (CostQuery, DispatchRequest, InventoryQuery, Tool)


async def test_cost_engine_deterministic(tools):
    cost, _, _ = tools
    report = await cost(CostQuery(incident_id="I1", site_id="PAR-021-NORD",
                                  failure_family="energy", remediation="replace module",
                                  parts=["APR48-3G"]))
    # parts 769.04 + labor 2h x 35.73 + truck 325.00 = 1165.50 USD (schema cross-check)
    assert report.repair_cost == 1165.50
    # downtime 5.00/min x 240 min x 1.5 (gold) + 5000.00 penalty = 6800.00 USD
    assert report.downtime_cost_avoided == 6800.00
    assert report.currency == "USD"
    assert report.breakdown["parts"] == 769.04


async def test_inventory_stock_and_flags(tools):
    _, inventory, _ = tools
    match = await inventory(InventoryQuery(incident_id="I1", site_id="PAR-021-NORD",
                                           part_numbers=["APR48-3G", "PN-DOES-NOT-EXIST"]))
    found, unknown = match.matches
    assert found.in_stock and found.quantity == 3 and found.warehouse_id == "WH-PAR-EST"
    assert not unknown.in_stock and unknown.quantity == 0   # flagged, not dropped


async def test_dispatch_books_then_conflicts(tools):
    _, _, dispatch = tools
    req = DispatchRequest(incident_id="I1", site_id="PAR-021-NORD",
                          skill="power", priority="P1", parts=[])
    first = await dispatch(req)
    assert first.booked and first.crew_id == "PWR-2"        # only available dc_power crew in IDF-North
    second = await dispatch(req)                            # PWR-2 now on_job, PWR-5 seeded on_job
    assert not second.booked and second.crew_id == ""       # conflict case handled
    dispatch.release_all()
    third = await dispatch(req)
    assert third.booked                                     # reset restored only OUR booking


async def test_tools_satisfy_frozen_protocol(tools):
    for tool in tools:
        assert isinstance(tool, Tool)
        assert tool.name and isinstance(tool.input_schema, dict)
