# Arc — Seed-data schema (telecom)

> **Owner:** aminssutt · **Reviewers:** simerugby (loader) + vgtray (corpus) ·
> **Phase 0, P0.** Schemas + sample rows for every entity the agents and the
> loader consume. This is the **shape contract** for `/data`; the actual seed
> volumes land in [DEMO.2 scenario seeds](https://github.com/aminssutt/Arc/issues/55)
> and [DEMO.1 corpus](https://github.com/aminssutt/Arc/issues/54).

All tabular entities are seeded as **CSV** (one file per entity, header row =
field names below). The corpus manifest is **JSON**. IDs are stable string keys.
Timestamps are ISO-8601 UTC. Money is **USD** with a `currency` field, expressed
as decimal dollars (number, e.g. `769.04`) to match the frozen mock fixtures
(`contracts/mock_stream/`) and the `float` money fields on the Cost tool contract
(`CostReport`, `InventoryLine`). The sample rows below form **one coherent demo
site** so the two scenario runs (confirm + pivot) are traceable end to end.

Demo anchor: site **`PAR-021-NORD`** — "Paris Nord macro site", a macro cell
site with a `-48V` DC power plant (4 × 2 kW rectifier modules, 2 × 24-cell VRLA
strings, 3-sector RAN, fiber backhaul, HVAC, genset). Both demo runs are in the
**energy** family: a **confirm** run (rectifier failure → DC undervoltage, the
field measurement confirms) and a **pivot** run (same alarm opening, but the
field measurement exposes a **supervision/sensing-card** fault, not a real
undervoltage). The RF "second voltage" (VSWR) is **not seeded live** — it is
covered offline by eval case **R2** (see `validation/GROUND_TRUTH_SCENARIOS.md`
and the fault-taxonomy note in `docs/ROADMAP.md`).

---

## 1. Alarm dictionary (4-family taxonomy)

Canonical alarm definitions the Watchdog normalizes raw feed events against, and
the key the Validation agent matches a technician's real/false + measurement to.
The `alarm_code` values (`PWR-*`, `ENV-*`, `RF-*`, `TRN-*`) are the **canonical
taxonomy** — raw feed traps map onto them via §1.1. File: `alarm_dictionary.csv`.

| Field | Type | Description |
|---|---|---|
| `alarm_code` | string (PK) | Stable canonical code, e.g. `PWR-DC-UV`. |
| `family` | enum | `energy` \| `environment` \| `rf` \| `transport`. |
| `subfamily` | string | e.g. `dc_plant`, `rectifier`, `battery`, `hvac`, `vswr`, `backhaul`. |
| `label` | string | Human label. |
| `severity_default` | enum | `critical` \| `major` \| `minor` \| `warning`. |
| `signal` | string | Canonical monitored metric, e.g. `dc_voltage_v` (see §1.1 vocabulary). |
| `unit` | string | `V`, `A`, `dB`, `degC`, `%`, `ms`, `bool`, `ratio`. |
| `threshold_op` | enum | `lt` \| `lte` \| `gt` \| `gte` \| `eq` \| `neq`. |
| `threshold_value` | number | Trigger threshold for `signal` (magnitude for signed metrics). |
| `debounce_s` | int | Seconds the condition must hold before the Watchdog fires. |
| `expected_measurement` | string | Canonical metric the field tech reports back (Validation compares to this). |

Sample rows:

| alarm_code | family | subfamily | label | severity_default | signal | unit | threshold_op | threshold_value | debounce_s | expected_measurement |
|---|---|---|---|---|---|---|---|---|---|---|
| PWR-GRID-LOSS | energy | grid | Mains/grid loss | critical | mains_present | bool | eq | 0 | 30 | mains_present |
| PWR-DC-UV | energy | dc_plant | -48V DC plant undervoltage | critical | dc_voltage_v | V | lt | 45.0 | 60 | dc_voltage_v |
| PWR-RECT-FAIL | energy | rectifier | Rectifier module failure | major | module_status | bool | eq | 0 | 30 | module_status |
| PWR-BATT-DEGRADED | energy | battery | Backup battery degraded | major | battery_autonomy_min | min | lt | 30 | 120 | battery_voltage_v |
| ENV-HVAC-FAIL | environment | hvac | HVAC failure / thermal risk | major | temp_c | degC | gt | 40.0 | 120 | temp_c |
| ENV-THERMAL-SHUT | environment | hvac | Radio thermal shutdown | critical | radio_temp_c | degC | gt | 75.0 | 30 | radio_temp_c |
| RF-VSWR-HIGH | rf | vswr | High VSWR / return-loss fault | major | vswr_ratio | ratio | gt | 1.8 | 60 | vswr_ratio |
| RF-CELL-DOWN | rf | cell | Cell down / sleeping cell | critical | cell_active | bool | eq | 0 | 60 | cell_active |
| TRN-BACKHAUL-DOWN | transport | backhaul | Backhaul link down | critical | backhaul_up | bool | eq | 0 | 30 | backhaul_up |
| TRN-DEGRADED | transport | backhaul | Backhaul degradation | minor | backhaul_loss_pct | % | gt | 2.0 | 180 | backhaul_loss_pct |

---

## 1.1 Canonical measurement chain (metric vocabulary + trap → alarm_code)

The chain the Validation agent walks: **raw feed trap → canonical `alarm_code`
→ `alarm_dictionary` row → `expected_measurement` (canonical metric) → compare
to the technician's reported metric by exact name.** The frozen fixtures pin the
metric names and the raw trap codes, so both tables below are reconciled toward
them.

### Canonical metric vocabulary

The metric names the FaultEvent feed, the field measurements, and
`expected_measurement` all use. These names are the contract — Validation matches
by exact metric name, so a rename anywhere breaks the match.

| metric | unit | convention | used by (alarm_code / point) | demo value(s) |
|---|---|---|---|---|
| `dc_voltage_v` | V | signed bus voltage, negative (e.g. `-45.0`); Watchdog compares magnitude to `threshold_value` | `PWR-DC-UV`; busbar field measurement | `-45.0` major trigger · `-44.8` confirm · `-53.9` pivot (normal) |
| `module_status` | bool | `1`=ok / `0`=fail | `PWR-RECT-FAIL`; rectifier module | `fail` (0) |
| `temp_c` | degC | positive | `ENV-HVAC-FAIL`; cabinet | `38.5` |
| `battery_voltage_v` | V | signed, negative | `PWR-BATT-DEGRADED`; battery string | `-54.4` float ref |
| `mains_present` | bool | `1`=present / `0`=lost | `PWR-GRID-LOSS`; AC input | `1` (normal throughout demo) |
| `radio_temp_c` | degC | positive | `ENV-THERMAL-SHUT`; radio unit | offline (eval V4) |
| `vswr_ratio` | ratio | `≥1.0` | `RF-VSWR-HIGH` | offline only (eval R2), e.g. `1.9` |
| `backhaul_up` | bool | `1`=up / `0`=down | `TRN-BACKHAUL-DOWN` | offline (eval T1) |

### Trap → alarm_code normalization table

Raw feed trap codes (real Eltek SNMP trap set per `V6`/`V7`, plus the fixtures'
codes) and the canonical `alarm_code` the Watchdog maps them to.

| raw trap (`FaultEvent.failure.code`) | canonical `alarm_code` | family | note |
|---|---|---|---|
| `alarmMajorRectifier` | `PWR-RECT-FAIL` | energy | rectifier module lost/failed (`V4`, `V6`) |
| `DC_UNDERVOLTAGE` | `PWR-DC-UV` | energy | plant sag below alarm threshold |
| `alarmMajorLowBattVolt` | `PWR-BATT-DEGRADED` | energy | low battery voltage (`V6`) |
| `alarmLVD1open` | `PWR-DC-UV` | energy | low-voltage disconnect — deep-undervoltage end state (`V1`/`V2`) |
| `alarmACmains` | `PWR-GRID-LOSS` | energy | mains input lost (`V6`) |
| `HIGH_TEMP` | `ENV-HVAC-FAIL` | environment | cabinet over-temperature |
| `alarmGeneratorTrap` | — | energy | genset fault (`V7`) — **no canonical code yet** (add `PWR-GENSET-FAIL` when genset run is seeded) |
| `alarmDistributionBreakerOpen` | — | energy | blown fuse / tripped breaker (`V6`) — **no canonical code yet** (eval `E4` holdout) |

**How the Watchdog uses this.** Per the frozen fixtures, `FaultEvent.failure.code`
carries the **raw trap** (e.g. `DC_UNDERVOLTAGE`, `alarmMajorRectifier`) for feed
fidelity; the Watchdog uses the mapped **`alarm_code`** (e.g. `PWR-DC-UV`) to index
`alarm_dictionary`, from which `expected_measurement` resolves the canonical metric
the Validation agent compares the technician's reading against. Rows mapping to
`—` are taxonomy gaps flagged for follow-up, not silent drops. **Currency is `USD`
everywhere in this schema.**

---

## 2. Site / network topology

Sites, their equipment, and the parent/child links Correlation walks to localize
a fault. Two files: `sites.csv` and `equipment.csv`.

### 2.1 `sites.csv`

| Field | Type | Description |
|---|---|---|
| `site_id` | string (PK) | e.g. `PAR-021-NORD`. |
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
| PAR-021-NORD | Paris Nord macro site | macro | 48.8969 | 2.3383 | Rue de la Chapelle, 75018 Paris | IDF-North | PP-PAR-021-NORD | gold |
| PAR-014-EST | Paris Est macro site | macro | 48.8566 | 2.4051 | 5 Av. Gambetta, 75020 Paris | IDF-East | PP-PAR-014-EST | silver |

### 2.2 `equipment.csv`

| Field | Type | Description |
|---|---|---|
| `equipment_id` | string (PK) | e.g. `EQ-PAR-021N-RECT-2`. |
| `site_id` | string (FK) | → `sites.site_id`. |
| `parent_id` | string (FK, nullable) | Topology parent (for correlation walk). |
| `class` | enum | `rectifier` \| `battery_string` \| `radio` \| `antenna` \| `feeder` \| `router` \| `hvac` \| `bbu`. |
| `vendor` | string | e.g. `Eaton`, `CSB`, `Nokia`. |
| `model` | string | Model string. |
| `part_number` | string (FK) | → `inventory.part_number` (for the matched spare). |
| `install_date` | date | Commissioning date. |

The demo's field points `busbar` (the `-48V` bus read by `dc_voltage_v`) and
`cabinet` (read by `temp_c`) are measurement points on the power plant (§3) and
the HVAC unit respectively, not spare-bearing equipment rows.

| equipment_id | site_id | parent_id | class | vendor | model | part_number | install_date |
|---|---|---|---|---|---|---|---|
| EQ-PAR-021N-PP-1 | PAR-021-NORD | | rectifier | Eaton | Flatpack2 -48V shelf | APR48-3G | 2021-05-10 |
| EQ-PAR-021N-RECT-2 | PAR-021-NORD | EQ-PAR-021N-PP-1 | rectifier | Eaton | APR48-3G | APR48-3G | 2021-05-10 |
| EQ-PAR-021N-BATT-A | PAR-021-NORD | EQ-PAR-021N-PP-1 | battery_string | CSB | TPL121000 | TPL121000 | 2021-05-10 |
| EQ-PAR-021N-HVAC-1 | PAR-021-NORD | | hvac | Stulz | Mini-Space | PN-HVAC-STULZ | 2020-11-02 |
| EQ-PAR-021N-ANT-1 | PAR-021-NORD | | antenna | Kathrein | 80010621 | PN-ANT-8001 | 2020-11-02 |
| EQ-PAR-021N-FEED-1 | PAR-021-NORD | EQ-PAR-021N-ANT-1 | feeder | RFS | LCF78-50JA | PN-FEED-78 | 2020-11-02 |

---

## 3. -48V power plant points

The DC plant measurement points the energy alarms read. File: `power_plant.csv`.

| Field | Type | Description |
|---|---|---|
| `plant_id` | string (PK) | → `sites.power_plant_id`. |
| `site_id` | string (FK) | → `sites.site_id`. |
| `nominal_voltage_v` | number | Nominal DC bus voltage (negative bus, magnitude), e.g. `48.0`. |
| `low_voltage_alarm_v` | number | Undervoltage alarm threshold magnitude (see `PWR-DC-UV`). |
| `rectifier_count` | int | Rectifier modules in the shelf. |
| `rectifier_capacity_a` | number | Per-module rated output current. |
| `battery_string_count` | int | Backup strings. |
| `battery_ah` | number | Amp-hour rating per string. |
| `design_autonomy_min` | int | Design backup autonomy at full load. |

| plant_id | site_id | nominal_voltage_v | low_voltage_alarm_v | rectifier_count | rectifier_capacity_a | battery_string_count | battery_ah | design_autonomy_min |
|---|---|---|---|---|---|---|---|---|
| PP-PAR-021-NORD | PAR-021-NORD | 48.0 | 45.0 | 4 | 42 | 2 | 100 | 210 |
| PP-PAR-014-EST | PAR-014-EST | 48.0 | 45.0 | 3 | 42 | 1 | 100 | 180 |

---

## 4. Inventory (part / stock / location / price)

Spare-part catalog + stock the **Inventory Lookup** tool queries and the
Cost/Inventory/Dispatch agent matches a fix to. Prices are **USD** decimal
dollars. File: `inventory.csv`.

| Field | Type | Description |
|---|---|---|
| `part_number` | string (PK) | e.g. `APR48-3G`. |
| `description` | string | Part description. |
| `equipment_class` | enum | Matches `equipment.class`. |
| `warehouse_id` | string (FK) | → `crew_schedule.base_id` / warehouse. |
| `location` | string | Warehouse + bin. |
| `stock_qty` | int | On-hand quantity. |
| `unit_price_usd` | number | Unit price in USD (decimal dollars). |
| `currency` | string | `USD`. |
| `lead_time_h` | int | Restock lead time if `stock_qty = 0`. |

| part_number | description | equipment_class | warehouse_id | location | stock_qty | unit_price_usd | currency | lead_time_h |
|---|---|---|---|---|---|---|---|---|
| APR48-3G | Eaton 48V/2000W rectifier module | rectifier | WH-PAR-EST | Paris-Est depot / A12 | 3 | 769.04 | USD | 48 |
| TPL121000 | CSB 12V/100Ah VRLA battery block | battery_string | WH-PAR-EST | Paris-Est depot / B04 | 8 | 314.95 | USD | 72 |
| PN-HVAC-STULZ | Stulz Mini-Space cabinet cooling unit | hvac | WH-PAR-EST | Paris-Est depot / D01 | 1 | 4200.00 | USD | 120 |
| PN-ANT-8001 | Panel antenna 1710-2170MHz | antenna | WH-PAR-NORD | Paris-Nord / C01 | 2 | 610.00 | USD | 120 |
| PN-FEED-78 | 7/8" feeder cable (per m) | feeder | WH-PAR-NORD | Paris-Nord / C09 | 40 | 18.00 | USD | 24 |
| PN-FUSE-125 | DC fuse 125A NH00 | rectifier | WH-PAR-EST | Paris-Est depot / A02 | 25 | 9.00 | USD | 24 |

---

## 5. Crew schedule

Field crews the **Crew Dispatch** tool books against. File: `crew_schedule.csv`.

| Field | Type | Description |
|---|---|---|
| `crew_id` | string (PK) | e.g. `PWR-2`. |
| `name` | string | Crew / lead name. |
| `base_id` | string | Home base / warehouse they draw parts from. |
| `region` | string | Coverage region (matches `sites.region` cluster). |
| `skills` | string | Pipe-separated, e.g. `dc_power\|rf\|transport`. |
| `shift_start` | time | Local shift start (HH:MM). |
| `shift_end` | time | Local shift end. |
| `status` | enum | `available` \| `on_job` \| `off_shift`. |
| `eta_min` | int | Typical ETA to region sites, minutes. |

| crew_id | name | base_id | region | skills | shift_start | shift_end | status | eta_min |
|---|---|---|---|---|---|---|---|---|
| PWR-2 | Bacar / Simon | WH-PAR-EST | IDF-North | dc_power\|transport | 06:00 | 18:00 | available | 120 |
| PWR-5 | Nguyen / Laurent | WH-PAR-NORD | IDF-North | rf\|dc_power | 08:00 | 20:00 | on_job | 60 |
| PWR-7 | Dupont / Mercier | WH-PAR-EST | IDF-East | dc_power\|rf\|transport | 06:00 | 18:00 | available | 55 |

---

## 6. Cost + SLA params

Rates the **Cost Engine** tool uses to compute cost-avoided and the SLA clock the
prioritization reasons over. Values are **USD** decimal dollars. Two files:
`cost_params.csv`, `sla_params.csv`.

### 6.1 `cost_params.csv`

| Field | Type | Description |
|---|---|---|
| `param_key` | string (PK) | e.g. `truck_roll_flat`. |
| `label` | string | Human label. |
| `value_usd` | number | Value in USD (per the `unit` below). |
| `unit` | string | `per_dispatch` \| `per_hour` \| `per_min_downtime` \| `per_incident`. |
| `currency` | string | `USD`. |

| param_key | label | value_usd | unit | currency |
|---|---|---|---|---|
| truck_roll_flat | Truck roll flat fee | 325.00 | per_dispatch | USD |
| labor_rate | Field labor rate (O*NET SOC 49-9052) | 35.73 | per_hour | USD |
| downtime_cost | Revenue loss while site down | 5.00 | per_min_downtime | USD |
| sla_breach_penalty | SLA breach penalty | 5000.00 | per_incident | USD |
| night_surcharge | Out-of-hours surcharge | 200.00 | per_dispatch | USD |

> Confirm-run cross-check: intervention `1165.50` = part `769.04` + 2 h labor
> `@35.73` (`71.46`) + truck roll `325.00`, matching
> `contracts/mock_stream/run_confirm.ndjson`.

### 6.2 `sla_params.csv`

Targets grounded in the Lumen SLA (`O1`): notify Critical 15 min; TTR High < 4 h
(240 min), Medium < 12 h (720 min), Low < 24 h (1440 min).

| Field | Type | Description |
|---|---|---|
| `sla_tier` | string (PK) | → `sites.sla_tier`. |
| `response_target_min` | int | Time-to-respond target. |
| `restore_target_min` | int | Time-to-restore target. |
| `priority_weight` | number | Multiplier the prioritizer applies. |

| sla_tier | response_target_min | restore_target_min | priority_weight |
|---|---|---|---|
| gold | 15 | 240 | 1.5 |
| silver | 30 | 720 | 1.0 |
| bronze | 60 | 1440 | 0.7 |

---

## 7. Corpus manifest

Index of the grounding documents the retriever ingests; each row = one source
document with the metadata the Root-Cause and Remediation agents cite. The
`doc_id` PK is the **`S`/`V`/`O`/`I` source ID from `validation/DATA_MANIFEST.md`**
— the same namespace the frozen event fixtures cite (`V4`, `S1`, `FIST-3-6`,
`O5`…) and that `contracts/events.schema.json` declares (`doc_id` keys into
`validation/DATA_MANIFEST.md` source IDs), so citations resolve to a real source.
File: `corpus_manifest.json` (array of objects).

| Field | Type | Description |
|---|---|---|
| `doc_id` | string (PK) | Source ID from `DATA_MANIFEST`, e.g. `V4`, `S1`, `O5`. |
| `type` | enum | `ran_manual` \| `power_spec` \| `alarm_dict` \| `vendor_sla` \| `maintenance_log` \| `outage_report` \| `incident_ticket`. |
| `title` | string | Document title. |
| `path` | string \| null | Relative path under `/data/corpus/`; `null` for link-only sources (cite by URL). |
| `vendor` | string \| null | Related vendor, if any. |
| `equipment_class` | string \| null | Related equipment class, if any. |
| `site_id` | string \| null | Related site, if any. |
| `date` | date | Publication / incident date. |
| `tags` | string[] | Retrieval tags. |

> The retriever (`agents/common/retriever.py`) ingests at **chunk** granularity
> (`{doc_id, title, section, path_or_text}`, citation key `(doc_id, section)`).
> A builder explodes each document-level row below into per-section chunks under
> the same `doc_id`; the `doc_id` is the shared key across schema, corpus,
> retriever citations, and `DATA_MANIFEST`.

Sample rows (a demo-cited subset; the full 35-source set lives in `DATA_MANIFEST`):

```json
[
  {
    "doc_id": "V4",
    "type": "ran_manual",
    "title": "Vertiv NetSure 2100 -48VDC manual",
    "path": "corpus/vendor/v4_netsure2100.pdf",
    "vendor": "Vertiv",
    "equipment_class": "rectifier",
    "site_id": null,
    "date": "2019-01-01",
    "tags": ["dc_plant", "rectifier", "-48v", "alarm-signature", "confirm-scenario"]
  },
  {
    "doc_id": "S1",
    "type": "power_spec",
    "title": "ETSI EN 300 132-2 — -48V DC power interface",
    "path": "corpus/standards/s1_en300132-2.pdf",
    "vendor": null,
    "equipment_class": null,
    "site_id": null,
    "date": "2021-01-01",
    "tags": ["dc_plant", "voltage-envelope", "standard", "-40.5..-57.0"]
  },
  {
    "doc_id": "V6",
    "type": "alarm_dict",
    "title": "ELTEK-DISTRIBUTED-MIB (SNMP trap OIDs)",
    "path": "corpus/vendor/v6_eltek_distributed_mib.txt",
    "vendor": "Eltek",
    "equipment_class": "rectifier",
    "site_id": null,
    "date": "2020-01-01",
    "tags": ["snmp", "trap", "alarm-code", "detection"]
  },
  {
    "doc_id": "FIST-3-6",
    "type": "maintenance_log",
    "title": "FIST 3-6 Storage Battery Maintenance",
    "path": "corpus/manuals/fist3-6.pdf",
    "vendor": null,
    "equipment_class": "battery_string",
    "site_id": null,
    "date": "1991-01-01",
    "tags": ["battery", "float", "discharge", "time-to-lvd", "confirm-scenario"]
  },
  {
    "doc_id": "TM-5-693",
    "type": "maintenance_log",
    "title": "TM 5-693 UPS Selection/Maintenance — symptom/fix matrices",
    "path": "corpus/manuals/tm5-693.pdf",
    "vendor": null,
    "equipment_class": "rectifier",
    "site_id": null,
    "date": "2006-01-01",
    "tags": ["symptom-fix", "rectifier", "battery", "remediation"]
  },
  {
    "doc_id": "UFC-3-540-07",
    "type": "power_spec",
    "title": "UFC 3-540-07 Generator O&M / electrical safety",
    "path": "corpus/manuals/ufc3-540-07.pdf",
    "vendor": null,
    "equipment_class": null,
    "site_id": null,
    "date": "2019-01-01",
    "tags": ["safety", "dc-plant", "lockout", "remediation"]
  },
  {
    "doc_id": "O1",
    "type": "vendor_sla",
    "title": "Lumen Service Level Agreement",
    "path": "corpus/slas/o1_lumen_sla.pdf",
    "vendor": "Lumen",
    "equipment_class": null,
    "site_id": null,
    "date": "2023-01-01",
    "tags": ["sla", "ttr", "credits", "cost"]
  },
  {
    "doc_id": "O5",
    "type": "vendor_sla",
    "title": "TelExpress Eaton APR48-3G listing (spare price)",
    "path": null,
    "vendor": "Eaton",
    "equipment_class": "rectifier",
    "site_id": null,
    "date": "2026-07-04",
    "tags": ["cost", "spares", "price", "link-only", "APR48-3G"]
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
alarm_dictionary.signal   -> canonical metric vocabulary (§1.1) -> power_plant.* / equipment telemetry (Watchdog)
FaultEvent.failure.code   -> trap->alarm_code table (§1.1) -> alarm_dictionary.alarm_code -> expected_measurement (Validation)
inventory.warehouse_id    -> crew_schedule.base_id     (part drawn by crew)
cost_params.*             -> Cost Engine tool inputs   (USD)
corpus_manifest.doc_id    -> DATA_MANIFEST source ID   (citation resolves to a real source)
corpus_manifest.site_id   -> sites.site_id             (site-scoped grounding)
```

## Two demo scenarios seeded on `PAR-021-NORD`

Both runs are **energy** family and traceable end to end to
`contracts/mock_stream/run_confirm.ndjson` / `run_pivot.ndjson`.

- **Confirm run:** feed traps `alarmMajorRectifier` + `DC_UNDERVOLTAGE` map to
  `PWR-RECT-FAIL` + `PWR-DC-UV` (§1.1) → Correlation localizes to
  `EQ-PAR-021N-RECT-2` + busbar → Root-Cause ranks rectifier module failure
  (grounded by `V4` alarm signature + `S1` voltage envelope + `TM-5-693`
  symptom/fix, multi-pass incl. `FIST-3-6` discharge / time-to-LVD) → tech
  confirms low `dc_voltage_v` (`-44.8 V`) → Remediation cites `V4` procedure +
  `UFC-3-540-07` safety, installs `APR48-3G` → Cost/Inventory/Dispatch matches
  `APR48-3G` (in stock, Paris-Est depot, `$769.04`, `O5`) + books crew `PWR-2`
  (`BK-2107`). Cost: intervention `$1,165.50`, avoided `$4,180.00`.
- **Pivot run:** same `PWR-DC-UV` opening, but the field measurement
  `dc_voltage_v = -53.9 V` is **NORMAL** (inside `S1`'s `-40.5 … -57.0 V`
  envelope) and cabinet `temp_c` stays normal → the `-45 V` reading arrived only
  via the supervision-card channel → Validation **pivots**: the real fault is a
  **supervision/sensing (BMS) card** feeding a false undervoltage (a single
  sensing path can fail, articulable via `S2`'s monitoring model), and the
  flagged rectifier is demoted to planned maintenance (N+1 redundancy holds,
  plant healthy). Actions revised on screen: cancel the emergency battery
  intervention; sensing-card replacement + scheduled module swap; `P1 → P3`. The
  cost-avoided beat is the unnecessary emergency truck-roll just prevented.

> The RF "second voltage" (VSWR / `RF-VSWR-HIGH` on a feeder) is **not seeded
> live**. It is covered offline by eval case **R2**
> (`validation/GROUND_TRUTH_SCENARIOS.md`) and framed at pitch as coverage-by-
> architecture — see the fault-taxonomy note in `docs/ROADMAP.md`.

> **Review checklist**
> - [ ] simerugby (loader): field names/types are loadable as-is (CSV + JSON), FKs resolve, money is USD decimal.
> - [ ] simerugby (watchdog): `FaultEvent.failure.code` emits the raw trap (fixtures), maps to `alarm_code` via §1.1.
> - [ ] vgtray (corpus): `corpus_manifest` `doc_id` uses `DATA_MANIFEST` S/V/O/I IDs; types/tags match the retriever's ingestion + citation needs.
