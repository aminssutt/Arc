# Arc — Seed-data schema (telecom)

> **Owner:** aminssutt · **Reviewers:** simerugby (loader) + vgtray (corpus) ·
> **Phase 0, P0.** Schemas + sample rows for every entity the agents and the
> loader consume. This is the **shape contract** for `/data`; the actual seed
> volumes land in [DEMO.2 scenario seeds](https://github.com/aminssutt/Arc/issues/55)
> and [DEMO.1 corpus](https://github.com/aminssutt/Arc/issues/54).

All tabular entities are seeded as **CSV** (one file per entity, header row =
field names below). The corpus manifest is **JSON**. IDs are stable string keys.
Timestamps are ISO-8601 UTC. Money is integer **euro cents** (no floats) with a
`currency` field. The sample rows below form **one coherent demo site** so the
two scenario runs (confirm + pivot) are traceable end to end.

Demo anchor: site **`SITE-PAR-014`** — a macro cell site near Paris with a
`-48V` DC power plant. The pitch beat ("voltage appears twice") is seeded here:
a **DC plant undervoltage** (energy) and a **VSWR/return-loss** fault (RF) on the
same site.

---

## 1. Alarm dictionary (4-family taxonomy)

Canonical alarm definitions the Watchdog normalizes raw feed events against, and
the key the Validation agent matches a technician's real/false + measurement to.
File: `alarm_dictionary.csv`.

| Field | Type | Description |
|---|---|---|
| `alarm_code` | string (PK) | Stable code, e.g. `PWR-DC-UV`. |
| `family` | enum | `energy` \| `environment` \| `rf` \| `transport`. |
| `subfamily` | string | e.g. `dc_plant`, `rectifier`, `battery`, `hvac`, `vswr`, `backhaul`. |
| `label` | string | Human label. |
| `severity_default` | enum | `critical` \| `major` \| `minor` \| `warning`. |
| `signal` | string | Monitored quantity, e.g. `dc_plant_voltage_v`. |
| `unit` | string | `V`, `A`, `dB`, `degC`, `%`, `ms`, `bool`. |
| `threshold_op` | enum | `lt` \| `lte` \| `gt` \| `gte` \| `eq` \| `neq`. |
| `threshold_value` | number | Trigger threshold for `signal`. |
| `debounce_s` | int | Seconds the condition must hold before the Watchdog fires. |
| `expected_measurement` | string | What the field tech reports back (Validation compares to this). |

Sample rows:

| alarm_code | family | subfamily | label | severity_default | signal | unit | threshold_op | threshold_value | debounce_s | expected_measurement |
|---|---|---|---|---|---|---|---|---|---|---|
| PWR-GRID-LOSS | energy | grid | Mains/grid loss | critical | mains_present | bool | eq | 0 | 30 | mains_voltage_v |
| PWR-DC-UV | energy | dc_plant | -48V DC plant undervoltage | critical | dc_plant_voltage_v | V | lt | 45.0 | 60 | dc_plant_voltage_v |
| PWR-RECT-FAIL | energy | rectifier | Rectifier module failure | major | rectifier_ok | bool | eq | 0 | 30 | rectifier_output_a |
| PWR-BATT-DEGRADED | energy | battery | Backup battery degraded | major | battery_autonomy_min | min | lt | 30 | 120 | battery_voltage_v |
| ENV-HVAC-FAIL | environment | hvac | HVAC failure / thermal risk | major | cabinet_temp_c | degC | gt | 40.0 | 120 | cabinet_temp_c |
| ENV-THERMAL-SHUT | environment | hvac | Radio thermal shutdown | critical | radio_temp_c | degC | gt | 75.0 | 30 | radio_temp_c |
| RF-VSWR-HIGH | rf | vswr | High VSWR / return-loss fault | major | vswr_ratio | ratio | gt | 1.8 | 60 | vswr_ratio |
| RF-CELL-DOWN | rf | cell | Cell down / sleeping cell | critical | cell_active | bool | eq | 0 | 60 | cell_active |
| TRN-BACKHAUL-DOWN | transport | backhaul | Backhaul link down | critical | backhaul_up | bool | eq | 0 | 30 | backhaul_up |
| TRN-DEGRADED | transport | backhaul | Backhaul degradation | minor | backhaul_loss_pct | % | gt | 2.0 | 180 | backhaul_loss_pct |

---

## 2. Site / network topology

Sites, their equipment, and the parent/child links Correlation walks to localize
a fault. Two files: `sites.csv` and `equipment.csv`.

### 2.1 `sites.csv`

| Field | Type | Description |
|---|---|---|
| `site_id` | string (PK) | e.g. `SITE-PAR-014`. |
| `name` | string | Human name. |
| `type` | enum | `macro` \| `micro` \| `small_cell` \| `central_office`. |
| `lat` | number | Latitude (for the iOS push location). |
| `lon` | number | Longitude. |
| `address` | string | Street address for the field crew. |
| `region` | string | Ops region / cluster. |
| `power_plant_id` | string (FK) | → `power_plant.plant_id`. |
| `sla_tier` | enum (FK) | → `sla_params.sla_tier`. |

| site_id | name | type | lat | lon | address | region | power_plant_id | sla_tier |
|---|---|---|---|---|---|---|---|---|
| SITE-PAR-014 | Paris Nord 14 | macro | 48.8988 | 2.3554 | 12 Rue de la Chapelle, 75018 Paris | IDF-North | PP-PAR-014 | gold |
| SITE-PAR-021 | Paris Est 21 | macro | 48.8566 | 2.4051 | 5 Av. Gambetta, 75020 Paris | IDF-East | PP-PAR-021 | silver |

### 2.2 `equipment.csv`

| Field | Type | Description |
|---|---|---|
| `equipment_id` | string (PK) | e.g. `EQ-PAR-014-RECT-1`. |
| `site_id` | string (FK) | → `sites.site_id`. |
| `parent_id` | string (FK, nullable) | Topology parent (for correlation walk). |
| `class` | enum | `rectifier` \| `battery_string` \| `radio` \| `antenna` \| `feeder` \| `router` \| `hvac` \| `bbu`. |
| `vendor` | string | e.g. `Vertiv`, `Huawei`, `Nokia`. |
| `model` | string | Model string. |
| `part_number` | string (FK) | → `inventory.part_number` (for the matched spare). |
| `install_date` | date | Commissioning date. |

| equipment_id | site_id | parent_id | class | vendor | model | part_number | install_date |
|---|---|---|---|---|---|---|---|
| EQ-PAR-014-PP-1 | SITE-PAR-014 | | rectifier | Vertiv | NetSure-48 | PN-RECT-48-2000 | 2021-05-10 |
| EQ-PAR-014-RECT-1 | SITE-PAR-014 | EQ-PAR-014-PP-1 | rectifier | Vertiv | R48-2000e3 | PN-RECT-48-2000 | 2021-05-10 |
| EQ-PAR-014-BATT-1 | SITE-PAR-014 | EQ-PAR-014-PP-1 | battery_string | Northstar | NSB-190FT | PN-BATT-190 | 2021-05-10 |
| EQ-PAR-014-ANT-1 | SITE-PAR-014 | | antenna | Kathrein | 80010621 | PN-ANT-8001 | 2020-11-02 |
| EQ-PAR-014-FEED-1 | SITE-PAR-014 | EQ-PAR-014-ANT-1 | feeder | RFS | LCF78-50JA | PN-FEED-78 | 2020-11-02 |

---

## 3. -48V power plant points

The DC plant measurement points the energy alarms read. File: `power_plant.csv`.

| Field | Type | Description |
|---|---|---|
| `plant_id` | string (PK) | → `sites.power_plant_id`. |
| `site_id` | string (FK) | → `sites.site_id`. |
| `nominal_voltage_v` | number | Nominal DC bus voltage (negative bus, magnitude), e.g. `48.0`. |
| `low_voltage_alarm_v` | number | Undervoltage alarm threshold (see `PWR-DC-UV`). |
| `rectifier_count` | int | Rectifier modules in the shelf. |
| `rectifier_capacity_a` | number | Per-module rated output current. |
| `battery_string_count` | int | Backup strings. |
| `battery_ah` | number | Amp-hour rating per string. |
| `design_autonomy_min` | int | Design backup autonomy at full load. |

| plant_id | site_id | nominal_voltage_v | low_voltage_alarm_v | rectifier_count | rectifier_capacity_a | battery_string_count | battery_ah | design_autonomy_min |
|---|---|---|---|---|---|---|---|---|
| PP-PAR-014 | SITE-PAR-014 | 48.0 | 45.0 | 4 | 50 | 2 | 190 | 240 |
| PP-PAR-021 | SITE-PAR-021 | 48.0 | 45.0 | 3 | 50 | 1 | 150 | 180 |

---

## 4. Inventory (part / stock / location / price)

Spare-part catalog + stock the **Inventory Lookup** tool queries and the
Cost/Inventory/Dispatch agent matches a fix to. File: `inventory.csv`.

| Field | Type | Description |
|---|---|---|
| `part_number` | string (PK) | e.g. `PN-RECT-48-2000`. |
| `description` | string | Part description. |
| `equipment_class` | enum | Matches `equipment.class`. |
| `warehouse_id` | string (FK) | → `crew_schedule.base_id` / warehouse. |
| `location` | string | Warehouse + bin. |
| `stock_qty` | int | On-hand quantity. |
| `unit_price_cents` | int | Unit price in euro cents. |
| `currency` | string | `EUR`. |
| `lead_time_h` | int | Restock lead time if `stock_qty = 0`. |

| part_number | description | equipment_class | warehouse_id | location | stock_qty | unit_price_cents | currency | lead_time_h |
|---|---|---|---|---|---|---|---|---|
| PN-RECT-48-2000 | Rectifier module 48V/2000W | rectifier | WH-PAR-CENTRAL | Paris-Central / A12 | 6 | 42000 | EUR | 48 |
| PN-BATT-190 | VRLA battery block 12V/190Ah | battery_string | WH-PAR-CENTRAL | Paris-Central / B04 | 8 | 28500 | EUR | 72 |
| PN-ANT-8001 | Panel antenna 1710-2170MHz | antenna | WH-PAR-NORTH | Paris-North / C01 | 2 | 61000 | EUR | 120 |
| PN-FEED-78 | 7/8" feeder cable (per m) | feeder | WH-PAR-NORTH | Paris-North / C09 | 40 | 1800 | EUR | 24 |
| PN-FUSE-125 | DC fuse 125A NH00 | rectifier | WH-PAR-CENTRAL | Paris-Central / A02 | 25 | 900 | EUR | 24 |

---

## 5. Crew schedule

Field crews the **Crew Dispatch** tool books against. File: `crew_schedule.csv`.

| Field | Type | Description |
|---|---|---|
| `crew_id` | string (PK) | e.g. `CREW-IDF-3`. |
| `name` | string | Crew / lead name. |
| `base_id` | string | Home base / warehouse they draw parts from. |
| `region` | string | Coverage region (matches `sites.region` cluster). |
| `skills` | string | Pipe-separated, e.g. `power|rf|transport`. |
| `shift_start` | time | Local shift start (HH:MM). |
| `shift_end` | time | Local shift end. |
| `status` | enum | `available` \| `on_job` \| `off_shift`. |
| `eta_min` | int | Typical ETA to region sites, minutes. |

| crew_id | name | base_id | region | skills | shift_start | shift_end | status | eta_min |
|---|---|---|---|---|---|---|---|---|
| CREW-IDF-3 | Dupont / Mercier | WH-PAR-CENTRAL | IDF-North | power\|transport | 06:00 | 18:00 | available | 45 |
| CREW-IDF-5 | Nguyen / Laurent | WH-PAR-NORTH | IDF-North | rf\|power | 08:00 | 20:00 | on_job | 60 |
| CREW-IDF-7 | Bacar / Simon | WH-PAR-CENTRAL | IDF-East | power\|rf\|transport | 06:00 | 18:00 | available | 55 |

---

## 6. Cost + SLA params

Rates the **Cost Engine** tool uses to compute cost-avoided and the SLA clock the
prioritization reasons over. Two files: `cost_params.csv`, `sla_params.csv`.

### 6.1 `cost_params.csv`

| Field | Type | Description |
|---|---|---|
| `param_key` | string (PK) | e.g. `truck_roll_flat`. |
| `label` | string | Human label. |
| `value_cents` | int | Value in euro cents (or cents/unit). |
| `unit` | string | `per_dispatch` \| `per_hour` \| `per_min_downtime` \| `per_incident`. |
| `currency` | string | `EUR`. |

| param_key | label | value_cents | unit | currency |
|---|---|---|---|---|
| truck_roll_flat | Truck roll flat fee | 18000 | per_dispatch | EUR |
| labor_rate | Field labor rate | 8500 | per_hour | EUR |
| downtime_cost | Revenue loss while site down | 250 | per_min_downtime | EUR |
| sla_breach_penalty | SLA breach penalty | 500000 | per_incident | EUR |
| night_surcharge | Out-of-hours surcharge | 12000 | per_dispatch | EUR |

### 6.2 `sla_params.csv`

| Field | Type | Description |
|---|---|---|
| `sla_tier` | string (PK) | → `sites.sla_tier`. |
| `response_target_min` | int | Time-to-respond target. |
| `restore_target_min` | int | Time-to-restore target. |
| `priority_weight` | number | Multiplier the prioritizer applies. |

| sla_tier | response_target_min | restore_target_min | priority_weight |
|---|---|---|---|
| gold | 30 | 120 | 1.5 |
| silver | 60 | 240 | 1.0 |
| bronze | 120 | 480 | 0.7 |

---

## 7. Corpus manifest

Index of the grounding documents the retriever ingests; each row = one source
document with the metadata the Root-Cause and Remediation agents cite. File:
`corpus_manifest.json` (array of objects).

| Field | Type | Description |
|---|---|---|
| `doc_id` | string (PK) | e.g. `DOC-RAN-001`. |
| `type` | enum | `ran_manual` \| `power_spec` \| `alarm_dict` \| `vendor_sla` \| `maintenance_log` \| `outage_report` \| `incident_ticket`. |
| `title` | string | Document title. |
| `path` | string | Relative path under `/data/corpus/`. |
| `vendor` | string \| null | Related vendor, if any. |
| `equipment_class` | string \| null | Related equipment class, if any. |
| `site_id` | string \| null | Related site, if any. |
| `date` | date | Publication / incident date. |
| `tags` | string[] | Retrieval tags. |

Sample rows:

```json
[
  {
    "doc_id": "DOC-RAN-001",
    "type": "ran_manual",
    "title": "Vertiv NetSure-48 DC Power System — O&M Manual",
    "path": "corpus/ran_manuals/vertiv_netsure48_om.md",
    "vendor": "Vertiv",
    "equipment_class": "rectifier",
    "site_id": null,
    "date": "2022-03-01",
    "tags": ["dc_plant", "rectifier", "-48v", "safety"]
  },
  {
    "doc_id": "DOC-PWR-002",
    "type": "power_spec",
    "title": "-48V Plant Undervoltage — Diagnostic & Recovery Procedure",
    "path": "corpus/power_specs/dc_undervoltage_procedure.md",
    "vendor": null,
    "equipment_class": "rectifier",
    "site_id": null,
    "date": "2023-01-15",
    "tags": ["dc_plant", "undervoltage", "battery", "remediation"]
  },
  {
    "doc_id": "DOC-INC-114",
    "type": "incident_ticket",
    "title": "INC-114 SITE-PAR-014 DC plant undervoltage, rectifier tripped",
    "path": "corpus/incidents/inc_114.md",
    "vendor": "Vertiv",
    "equipment_class": "rectifier",
    "site_id": "SITE-PAR-014",
    "date": "2024-11-20",
    "tags": ["energy", "PWR-DC-UV", "historical", "confirm-scenario"]
  },
  {
    "doc_id": "DOC-OUT-045",
    "type": "outage_report",
    "title": "Outage OUT-045 — VSWR feeder fault mistaken for DC issue",
    "path": "corpus/outages/out_045.md",
    "vendor": "RFS",
    "equipment_class": "feeder",
    "site_id": "SITE-PAR-014",
    "date": "2024-06-08",
    "tags": ["rf", "RF-VSWR-HIGH", "pivot-scenario", "historical"]
  },
  {
    "doc_id": "DOC-SLA-003",
    "type": "vendor_sla",
    "title": "Vertiv Spares & Response SLA",
    "path": "corpus/slas/vertiv_sla.md",
    "vendor": "Vertiv",
    "equipment_class": null,
    "site_id": null,
    "date": "2023-09-01",
    "tags": ["sla", "spares", "response"]
  }
]
```

---

## Cross-entity keys (relationship map)

```
sites.power_plant_id      -> power_plant.plant_id
sites.sla_tier            -> sla_params.sla_tier
equipment.site_id         -> sites.site_id
equipment.parent_id       -> equipment.equipment_id   (topology walk, Correlation)
equipment.part_number     -> inventory.part_number    (matched spare)
alarm_dictionary.signal   -> power_plant.* / equipment telemetry (Watchdog)
inventory.warehouse_id    -> crew_schedule.base_id     (part drawn by crew)
cost_params.*             -> Cost Engine tool inputs
corpus_manifest.site_id   -> sites.site_id             (site-scoped grounding)
```

## Two demo scenarios seeded on `SITE-PAR-014`

- **Confirm run:** `PWR-DC-UV` fires → Correlation localizes to `EQ-PAR-014-RECT-1`
  → Root-Cause ranks rectifier failure (grounded by `DOC-INC-114`) → tech
  confirms low `dc_plant_voltage_v` → Remediation cites `DOC-PWR-002` →
  Cost/Inventory/Dispatch matches `PN-RECT-48-2000` (in stock) + books `CREW-IDF-3`.
- **Pivot run:** `PWR-DC-UV` appears but the field measurement contradicts it;
  Validation pivots (grounded by `DOC-OUT-045`) → phase 1 re-runs → the real
  fault is `RF-VSWR-HIGH` on `EQ-PAR-014-FEED-1` (voltage appears twice — the
  pitch beat).

> **Review checklist**
> - [ ] simerugby (loader): field names/types are loadable as-is (CSV + JSON), FKs resolve.
> - [ ] vgtray (corpus): `corpus_manifest` types/tags match the retriever's ingestion + citation needs.
