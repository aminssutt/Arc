"""BE.10 acceptance: all seeds loaded and validated; explicit errors on invalid
seed data (file + offending row in the message)."""
import pytest

from backend.app.seeds import SeedError, load_seeds
from backend.app.settings import Settings


def test_loads_all_entities_with_fallback():
    s = Settings()
    seeds = load_seeds(s.data_dir, s.seed_fallback_dir)
    assert seeds.alarm_dictionary and seeds.sites and seeds.equipment
    assert seeds.inventory and seeds.crew_schedule and seeds.cost_params and seeds.sla_params
    assert seeds.corpus_manifest
    assert all("fallback" in src for src in seeds.sources.values())  # /data has schema.md only today


def test_explicit_error_on_broken_fk(tmp_path):
    s = Settings()
    # copy defaults, then break a foreign key
    import shutil
    for f in s.seed_fallback_dir.iterdir():
        shutil.copy(f, tmp_path / f.name)
    sites = (tmp_path / "sites.csv").read_text(encoding="utf-8")
    (tmp_path / "sites.csv").write_text(sites.replace("PP-PAR-014", "PP-MISSING"), encoding="utf-8")

    with pytest.raises(SeedError) as exc:
        load_seeds(tmp_path, s.seed_fallback_dir)
    assert "PP-MISSING" in str(exc.value) and "sites.csv" in str(exc.value)


def test_explicit_error_on_missing_file(tmp_path):
    with pytest.raises(SeedError) as exc:
        load_seeds(tmp_path, tmp_path)  # nothing anywhere
    assert "alarm_dictionary.csv" in str(exc.value)
