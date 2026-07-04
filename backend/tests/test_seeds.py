"""BE.10 acceptance: all seeds loaded and validated; explicit errors on invalid
seed data (file + offending row in the message)."""
import pytest

from backend.app.seeds import SeedError, load_seeds
from backend.app.settings import Settings


def test_loads_all_entities_from_data_dir():
    s = Settings()
    seeds = load_seeds(s.data_dir, s.seed_fallback_dir)
    assert seeds.alarm_dictionary and seeds.sites and seeds.equipment
    assert seeds.inventory and seeds.crew_schedule and seeds.cost_params and seeds.sla_params
    assert seeds.corpus_manifest
    assert seeds.trap_map and seeds.scenarios["confirm"] and seeds.scenarios["pivot"]
    assert all("fallback" not in src for src in seeds.sources.values())  # DEMO.2: /data is primary now


def test_explicit_error_on_broken_fk(tmp_path):
    s = Settings()
    # copy defaults, then break a foreign key
    import shutil
    for f in s.seed_fallback_dir.iterdir():
        if f.is_dir():
            shutil.copytree(f, tmp_path / f.name)
        else:
            shutil.copy(f, tmp_path / f.name)
    sites = (tmp_path / "sites.csv").read_text(encoding="utf-8")
    (tmp_path / "sites.csv").write_text(sites.replace("PP-PAR-021-NORD", "PP-MISSING"), encoding="utf-8")

    with pytest.raises(SeedError) as exc:
        load_seeds(tmp_path, s.seed_fallback_dir)
    assert "PP-MISSING" in str(exc.value) and "sites.csv" in str(exc.value)


def test_explicit_error_on_missing_file(tmp_path):
    with pytest.raises(SeedError) as exc:
        load_seeds(tmp_path, tmp_path)  # nothing anywhere
    assert "alarm_dictionary.csv" in str(exc.value)
