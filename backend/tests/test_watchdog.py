"""BE.2 acceptance: threshold + debounce unit-tested (no duplicate within the
window); one injected fault => exactly ONE FaultEvent with the correct family;
zero LLM calls (the module imports nothing but seeds + stdlib — by construction).
"""
import pytest

from backend.app.seeds import load_seeds
from backend.app.settings import Settings
from backend.app.watchdog import Watchdog


def _sig(ts, signal="dc_plant_voltage_v", value=44.0, site="SITE-PAR-014", eq="EQ-PAR-014-RECT-1"):
    return {"ts": ts, "site_id": site, "signal": signal, "value": value, "equipment_id": eq}


@pytest.fixture()
def capture():
    class Capture:
        faults: list = []
        additions: list = []

        async def on_fault(self, site, family, failures, trigger):
            self.faults.append({"site": site, "family": family, "failures": failures, "trigger": trigger})

        async def on_add(self, site, failures):
            self.additions.append({"site": site, "failures": failures})

    return Capture()


@pytest.fixture()
def wd(capture):
    s = Settings()
    seeds = load_seeds(s.data_dir, s.seed_fallback_dir)
    return Watchdog(seeds, capture.on_fault, capture.on_add)


async def test_debounce_holds_then_fires_exactly_once(wd, capture):
    # PWR-DC-UV: lt 45.0, debounce 60 s (event time)
    await wd.ingest(_sig("2026-07-05T09:00:00Z"))          # breach starts, no fire
    assert capture.faults == []
    await wd.ingest(_sig("2026-07-05T09:00:30Z"))          # inside window, still no fire
    assert capture.faults == []
    await wd.ingest(_sig("2026-07-05T09:01:01Z"))          # 61 s held -> fires
    assert len(capture.faults) == 1
    fault = capture.faults[0]
    assert fault["family"] == "energy"
    assert fault["failures"][0]["code"] == "PWR-DC-UV"
    assert fault["trigger"]["rule"] == "PWR-DC-UV"


async def test_no_duplicate_fault_event_within_episode(wd, capture):
    for ts in ("2026-07-05T09:00:00Z", "2026-07-05T09:01:01Z",
               "2026-07-05T09:02:00Z", "2026-07-05T09:03:00Z"):
        await wd.ingest(_sig(ts))
    assert len(capture.faults) == 1                        # fired once, then suppressed
    assert capture.additions == []                         # same alarm episode, no re-fire


async def test_recovery_clears_debounce(wd, capture):
    await wd.ingest(_sig("2026-07-05T09:00:00Z"))          # breach
    await wd.ingest(_sig("2026-07-05T09:00:30Z", value=47.5))  # recovered -> state cleared
    await wd.ingest(_sig("2026-07-05T09:02:00Z"))          # new breach episode t0
    await wd.ingest(_sig("2026-07-05T09:02:30Z"))          # only 30 s held
    assert capture.faults == []                            # debounce restarted, correctly


async def test_additional_failure_attaches_to_active_incident(wd, capture):
    await wd.ingest(_sig("2026-07-05T09:00:00Z"))
    await wd.ingest(_sig("2026-07-05T09:01:01Z"))          # incident opens
    # different alarm on the same site while incident active -> attach, no 2nd FaultEvent
    await wd.ingest(_sig("2026-07-05T09:05:00Z", signal="cabinet_temp_c", value=42.0, eq="EQ-HVAC"))
    await wd.ingest(_sig("2026-07-05T09:07:01Z", signal="cabinet_temp_c", value=42.0, eq="EQ-HVAC"))
    assert len(capture.faults) == 1
    assert len(capture.additions) == 1
    assert capture.additions[0]["failures"][0]["code"] == "ENV-HVAC-FAIL"


async def test_families_correct_per_dictionary(wd, capture):
    await wd.ingest(_sig("2026-07-05T10:00:00Z", signal="vswr_ratio", value=1.9, site="SITE-PAR-021", eq="ANT"))
    await wd.ingest(_sig("2026-07-05T10:01:01Z", signal="vswr_ratio", value=1.9, site="SITE-PAR-021", eq="ANT"))
    assert capture.faults[-1]["family"] == "rf"
    assert capture.faults[-1]["failures"][0]["code"] == "RF-VSWR-HIGH"


async def test_bool_style_signal(wd, capture):
    await wd.ingest(_sig("2026-07-05T11:00:00Z", signal="backhaul_up", value=0, site="SITE-PAR-021", eq="RTR"))
    await wd.ingest(_sig("2026-07-05T11:00:31Z", signal="backhaul_up", value=0, site="SITE-PAR-021", eq="RTR"))
    assert capture.faults[-1]["family"] == "transport"
