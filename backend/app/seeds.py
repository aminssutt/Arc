"""Seed-data loader (BE.10) — loads /data per data/schema.md, validates, fails loud.

Reads the CSV/JSON entities defined by aminssutt's shape contract. Until DEMO.2
lands the real volumes in /data, any file missing there falls back to
backend/seed_defaults/ (the schema's own sample rows, one coherent demo site).
Invalid seed data raises SeedError with the file and row — explicit errors are
an acceptance criterion.
"""
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FAMILIES = {"energy", "environment", "rf", "transport"}
THRESHOLD_OPS = {"lt", "lte", "gt", "gte", "eq", "neq"}

CSV_FILES = [
    "alarm_dictionary", "sites", "equipment", "power_plant",
    "inventory", "crew_schedule", "cost_params", "sla_params",
]


class SeedError(RuntimeError):
    pass


@dataclass
class Seeds:
    alarm_dictionary: dict[str, dict[str, Any]] = field(default_factory=dict)  # by alarm_code
    sites: dict[str, dict[str, Any]] = field(default_factory=dict)             # by site_id
    equipment: dict[str, dict[str, Any]] = field(default_factory=dict)         # by equipment_id
    power_plant: dict[str, dict[str, Any]] = field(default_factory=dict)       # by plant_id
    inventory: dict[str, dict[str, Any]] = field(default_factory=dict)         # by part_number
    crew_schedule: dict[str, dict[str, Any]] = field(default_factory=dict)     # by crew_id
    cost_params: dict[str, dict[str, Any]] = field(default_factory=dict)       # by param_key
    sla_params: dict[str, dict[str, Any]] = field(default_factory=dict)        # by sla_tier
    corpus_manifest: list[dict[str, Any]] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)                      # entity -> path loaded


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SeedError(f"{path}: empty seed file")
    return rows


def _num(row: dict, key: str, path: Path, cast=float):
    try:
        return cast(row[key])
    except (KeyError, ValueError) as exc:
        raise SeedError(f"{path}: bad numeric field '{key}' in row {row}") from exc


def _require(row: dict, keys: list[str], path: Path) -> None:
    missing = [k for k in keys if not row.get(k)]
    if missing:
        raise SeedError(f"{path}: row missing required fields {missing}: {row}")


def _pick(data_dir: Path, fallback_dir: Path, name: str, sources: dict[str, str]) -> Path:
    primary = data_dir / name
    if primary.exists():
        sources[name] = str(primary)
        return primary
    fallback = fallback_dir / name
    if fallback.exists():
        sources[name] = str(fallback) + " (fallback)"
        return fallback
    raise SeedError(f"seed file '{name}' found in neither {data_dir} nor {fallback_dir}")


def load_seeds(data_dir: Path, fallback_dir: Path) -> Seeds:
    s = Seeds()

    for row in _read_csv(_pick(data_dir, fallback_dir, "alarm_dictionary.csv", s.sources)):
        p = Path(s.sources["alarm_dictionary.csv"].split(" ")[0])
        _require(row, ["alarm_code", "family", "severity_default", "signal", "threshold_op"], p)
        if row["family"] not in FAMILIES:
            raise SeedError(f"{p}: unknown family '{row['family']}' for {row['alarm_code']}")
        if row["threshold_op"] not in THRESHOLD_OPS:
            raise SeedError(f"{p}: unknown threshold_op '{row['threshold_op']}' for {row['alarm_code']}")
        row["threshold_value"] = _num(row, "threshold_value", p)
        row["debounce_s"] = _num(row, "debounce_s", p, int)
        s.alarm_dictionary[row["alarm_code"]] = row

    for row in _read_csv(_pick(data_dir, fallback_dir, "sites.csv", s.sources)):
        p = Path(s.sources["sites.csv"].split(" ")[0])
        _require(row, ["site_id", "name", "lat", "lon", "sla_tier"], p)
        row["lat"], row["lon"] = _num(row, "lat", p), _num(row, "lon", p)
        s.sites[row["site_id"]] = row

    for row in _read_csv(_pick(data_dir, fallback_dir, "equipment.csv", s.sources)):
        p = Path(s.sources["equipment.csv"].split(" ")[0])
        _require(row, ["equipment_id", "site_id", "class"], p)
        s.equipment[row["equipment_id"]] = row

    for row in _read_csv(_pick(data_dir, fallback_dir, "power_plant.csv", s.sources)):
        s.power_plant[row["plant_id"]] = row

    for row in _read_csv(_pick(data_dir, fallback_dir, "inventory.csv", s.sources)):
        p = Path(s.sources["inventory.csv"].split(" ")[0])
        _require(row, ["part_number", "warehouse_id", "currency"], p)
        row["stock_qty"] = _num(row, "stock_qty", p, int)
        row["unit_price_cents"] = _num(row, "unit_price_cents", p, int)
        row["lead_time_h"] = _num(row, "lead_time_h", p, int)
        s.inventory[row["part_number"]] = row

    for row in _read_csv(_pick(data_dir, fallback_dir, "crew_schedule.csv", s.sources)):
        p = Path(s.sources["crew_schedule.csv"].split(" ")[0])
        _require(row, ["crew_id", "base_id", "region", "skills", "status"], p)
        row["eta_min"] = _num(row, "eta_min", p, int)
        row["skills_list"] = [x.strip() for x in row["skills"].split("|") if x.strip()]
        s.crew_schedule[row["crew_id"]] = row

    for row in _read_csv(_pick(data_dir, fallback_dir, "cost_params.csv", s.sources)):
        p = Path(s.sources["cost_params.csv"].split(" ")[0])
        row["value_cents"] = _num(row, "value_cents", p, int)
        s.cost_params[row["param_key"]] = row

    for row in _read_csv(_pick(data_dir, fallback_dir, "sla_params.csv", s.sources)):
        p = Path(s.sources["sla_params.csv"].split(" ")[0])
        row["response_target_min"] = _num(row, "response_target_min", p, int)
        row["restore_target_min"] = _num(row, "restore_target_min", p, int)
        row["priority_weight"] = _num(row, "priority_weight", p)
        s.sla_params[row["sla_tier"]] = row

    manifest_path = _pick(data_dir, fallback_dir, "corpus_manifest.json", s.sources)
    try:
        s.corpus_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SeedError(f"{manifest_path}: invalid JSON: {exc}") from exc
    if not isinstance(s.corpus_manifest, list):
        raise SeedError(f"{manifest_path}: corpus manifest must be a JSON array")

    _check_fks(s)
    return s


def _check_fks(s: Seeds) -> None:
    """Cross-entity keys per data/schema.md relationship map — fail loud."""
    for site_id, site in s.sites.items():
        if site.get("power_plant_id") and site["power_plant_id"] not in s.power_plant:
            raise SeedError(f"sites.csv: {site_id} power_plant_id '{site['power_plant_id']}' not in power_plant.csv")
        if site["sla_tier"] not in s.sla_params:
            raise SeedError(f"sites.csv: {site_id} sla_tier '{site['sla_tier']}' not in sla_params.csv")
    for eq_id, eq in s.equipment.items():
        if eq["site_id"] not in s.sites:
            raise SeedError(f"equipment.csv: {eq_id} site_id '{eq['site_id']}' not in sites.csv")
        if eq.get("parent_id") and eq["parent_id"] not in s.equipment:
            raise SeedError(f"equipment.csv: {eq_id} parent_id '{eq['parent_id']}' not in equipment.csv")
        if eq.get("part_number") and eq["part_number"] not in s.inventory:
            raise SeedError(f"equipment.csv: {eq_id} part_number '{eq['part_number']}' not in inventory.csv")
