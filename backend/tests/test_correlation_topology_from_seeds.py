"""Regression: the Correlation adapter builds its topology from the loaded seeds,
so it localizes on the REAL (possibly renamed) demo site instead of drifting to a
stale bundled fixture. Offline (no Vultr) — deterministic localization.
"""
from contracts import AgentInput
from backend.app.correlation_adapter import CorrelationAgentAdapter


def _run(agent, site_id):
    ctx = {"failures": [{"id": "F1", "code": "alarmMajorRectifier", "alarm_code": "PWR-DC-UV",
                         "equipment": "rectifier", "value": -44.8}]}
    import asyncio
    return asyncio.run(agent.run(AgentInput(
        incident_id="INC-1", site_id=site_id, failure_family="energy", context=ctx)))


def test_localizes_on_real_seed_site(seeds):
    # PAR-021-NORD is the current (post-audit) demo site; the bundled fixture only
    # knows the OLD SITE-PAR-014 ids, so without seeds this would fail to localize.
    site_id = "PAR-021-NORD" if "PAR-021-NORD" in seeds.sites else next(iter(seeds.sites))
    agent = CorrelationAgentAdapter(seeds=seeds)   # offline, topology from seeds
    out = _run(agent, site_id)

    corr = out.payload["correlation"]
    assert corr["site_id"] == site_id
    assert corr["equipment"], "correlation failed to localize any equipment on the real site"
    # the localized equipment belongs to the real site's rectifier chain
    assert any(str(e).startswith("EQ-") for e in corr["equipment"])
    assert "Could not localize" not in out.summary


def test_falls_back_to_fixture_without_seeds():
    # Backwards compatible: no seeds -> bundled fixture (used by INT.1 tests).
    agent = CorrelationAgentAdapter()
    out = _run(agent, "SITE-PAR-014")
    assert out.payload["correlation"]["site_id"] == "SITE-PAR-014"
