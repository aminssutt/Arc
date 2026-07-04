# GROUND-TRUTH SCENARIOS — the 2 demo runs + 16-case eval matrix + 2 negative controls

> **Pin-pass complete (waves 1–2):** every load-bearing value now carries its
> DATA_MANIFEST source ID. Values marked *(synth)* are honest syntheses from real curves —
> label them as such if quoted. Site model: macro cell site "PAR-021-NORD", -48V DC plant
> (4 × 2 kW rectifier modules, 2 × 24-cell VRLA strings), 3-sector RAN, fiber backhaul,
> HVAC, genset.

## Signal format (pre-contract, mapping-ready)

One JSONL event per line; converts to the frozen FaultEvent contract with a thin mapper.

```json
{"ts":"2026-07-05T09:00:00Z","site":"PAR-021-NORD","source":"dc_plant","equipment":"rectifier-2","metric":"module_status","value":"fail","alarm":{"name":"alarmMajorRectifier","severity":"major","probable_cause":"rectifierFailure"}}
{"ts":"2026-07-05T09:00:30Z","site":"PAR-021-NORD","source":"dc_plant","equipment":"busbar","metric":"dc_voltage_v","value":-53.8,"alarm":null}
```

- Severities: X.733's five event types / six severities (**S3**).
- Alarm names: real Eltek SNMP trap set — `alarmMajorRectifier`, `alarmMajorLowBattVolt`,
  `alarmLVD1open`, `alarmACmains`, `alarmDistributionBreakerOpen` (**V6/V7**, MIBs via
  LibreNMS; value encodings e.g. divisor-100 per **V8**, committable GPL).
- Normal -48V input range at equipment: **−40.5 to −57.0 VDC** (**S1**, ETSI EN 300 132-2
  — THE citable envelope; anything outside = abnormal by standard).
- Float reference: ~−54.4 V (2.27 V/cell × 24) per stationary-battery float criteria
  (**UFC 3-520-05**, wave-2 PD manuals; corroborated by **FIST 3-6** Table 1, p.14).

---

## DEMO RUN 1 — "CONFIRM" (rectifier failure → DC undervoltage → thermal risk)

**Story:** one rectifier module dies under summer load; the plant sags onto batteries;
temperature climbs. Technician's physical measurement CONFIRMS. Agent ships the full
action report.

| t | Event | Value | Source |
|---|---|---|---|
| 09:00:00 | `alarmMajorRectifier`, rectifier-2 | module_status=fail | trap name **V6**; fail signatures & clearing procedure **V4** (NetSure "Rectifier Lost") |
| 09:00:30 | Plant voltage sag begins | −54.4 → −53.8 V | float ref **UFC 3-520-05 / FIST 3-6 Table 1** |
| 09:02:00 | Load redistribution | 3 modules at 97% capacity | site load ~5.6 kW (scenario constant) |
| 09:04:00 | `BATTERY_DISCHARGE` warning | current −18 A | monitoring points per **S2** (ES 202 336-2) |
| 09:12:00 | Undervoltage minor | −47.0 V | controller-configured limit — semantics per **V2** (Smartpack2 alarm-limit table) + **FIST 3-6 §8.4** (undervoltage) |
| 09:20:00 | Undervoltage major — **Watchdog triggers Orchestrator** (debounced) | −45.0 V | same basis; still inside S1's envelope → "degraded, on batteries", not yet out-of-standard |
| 09:22:00 | Cabinet temp rising | 38 °C, ~0.8 °C/min | ramp shape from NAB real thermal-anomaly stream (**wave-2 datasets**, MIT, labeled) |
| 09:30:00 | `HIGH_TEMP` warning | 43 °C → approaching class limit | **EN 300 019 class 3.1 environmental envelope (S4)** — the citable basis; read the exact class ceiling from the fetched PDF at build. ⚠️ Do NOT cite V9 (Nokia draft carries "confidential" footers — background only, critic-flagged) |

**Grid sensor stays NORMAL throughout** (`alarmACmains` never fires) — the discriminator:
root cause is rectifier module failure, NOT grid loss. Cross-check pattern: no concurrent
county-level outage in EAGLE-I-style feed → site-local fault (**wave-2 datasets**).

**Expected agent behavior (ground truth):**
- Correlation: PAR-021-NORD, dc_plant/rectifier-2 + busbar; blast radius all sectors.
- Root-Cause (multi-retrieve): #1 rectifier module failure — cites **V4** (alarm
  signature) + **S1** (voltage envelope) + **TM 5-693 Tables 4-1..4-7** (symptom→fix
  matrix); #2 grid loss REJECTED (mains OK); #3 battery degradation watch-flag.
  Confidence gate: retrieves discharge behavior before committing time-to-LVD.
- Time-to-LVD: batteries hold ~3–5 h at this load before LVD at ~−42 to −44 V *(synth:
  NASA capacity-fade curves scaled to a -48V string per **FIST 3-6** Table 1 — labeled
  synthesis)*; LVD event names per **V1/V2** (NCU LVD settings, `alarmLVD1open`).
- Push to technician: site, equipment, family=Energy, detected list = [alarmMajorRectifier,
  DC_UNDERVOLTAGE, HIGH_TEMP].
- **Technician measures busbar: −44.8 V → CONFIRMS.** Validation checklist mirrors real
  PMCS practice (**TM 9-6140-200-14**, verbatim safety warnings committable; **O2/FIST
  3-6 §3.5.7** battery troubles).
- Remediation: replace module per **V4** procedure + **TM 5-693 Table 4-x** row; cited
  safety steps from **UFC 3-540-07 / FIST 3-6** (PD, committable).
- Cost/Inventory/Dispatch: real part prices — Flatpack2 HE 48V/2000W **$1,329.79**
  (wave-2 vein 6, link-only) or Eaton APR48-3G **$769.04** (**O5**); truck-roll
  **$150–500 direct / >$1,000 loaded** (link-only, labeled vendor figure); labor
  **$35.73/hr median** (O*NET SOC 49-9052, CC-BY attribute); SLA clocks + credits per
  **O1/O6** (Lumen: Critical notify 15 min, TTR High <4 h).
- Report: prioritized actions, every claim carrying a citation that resolves; priority
  driven by computed time-to-LVD, not vibes.

---

## DEMO RUN 2 — "PIVOT" (same opening, telemetry lies, agent re-diagnoses live)

**Story:** identical alarm opening. Technician measures the busbar: **−53.9 V — NORMAL.**
The monitoring/BMS sensing card is the fault. Agent pivots on camera.

Deltas vs Run 1: cabinet temperature stays normal (planted inconsistency a good system
should weigh); the −45 V reading arrives ONLY via the supervision-card channel (single
sensing path — **S2**'s monitoring model makes this articulable: the measurement point,
not the plant, can fail).

**Expected agent behavior (ground truth):**
- Same Phase-1 opening, but Root-Cause notes missing thermal correlation → caps
  confidence on "real undervoltage"; explicitly requests physical verification.
- Technician: −53.9 V, flags DC_UNDERVOLTAGE = FALSE, alarmMajorRectifier = REAL
  (module LED dark) — mixed validation, harder than all-false.
- Validation agent: measurement contradicts telemetry → **pivot**: re-diagnose with the
  measurement as ground truth. New #1: supervision/sensing card fault; failed rectifier
  demoted to planned maintenance (n+1 redundancy holds, plant healthy).
- Actions REVISED on screen: cancel emergency battery intervention; sensing-card
  replacement + scheduled module swap; P1 → P3; cost-avoided beat = the unnecessary
  emergency truck-roll just prevented (**$150–500/>$1,000** figure, labeled).
- Report states the contradiction honestly — the honesty line judges remember.

---

## EVAL MATRIX — 16 fault scenarios + 2 negative controls

Weighted to demo families. Each row: injected signature → ground-truth root cause
(top-1) with ≥1 resolving citation.

| # | Family | Injected signature | Ground-truth root cause | Trap it tests |
|---|---|---|---|---|
| E1 | Energy | Run 1 exactly | Rectifier module failure | baseline determinism |
| E2 | Energy | `alarmACmains` + all rectifiers off + voltage decay | Grid loss (genset failed to start — **S7** genset monitoring points, **TM 5-685** diesel tables) | vs E1 discriminator |
| E3 | Energy | Voltage sag only under load test, normal float | Degraded battery string (fade profile *(synth from NASA curves)*; troubles per **FIST 3-6 §3.5.7**) | needs discharge-curve retrieval |
| E4 | Energy | Single distribution branch dead, plant normal | Blown fuse/tripped breaker (`alarmDistributionBreakerOpen`, **V6**) | correlation granularity — **UNSEEN holdout** |
| E5 | Energy | Overvoltage −57.5 V | Rectifier float/controller fault — outside S1's **−57.0 V** upper limit (**S1**; **FIST 3-6 §8.4**) | opposite-direction anomaly |
| E6 | Energy | Run 2 exactly | Sensing/BMS card fault | pivot correctness |
| V1 | Environment | Temp ramp (NAB shape) + HVAC current zero | HVAC compressor failure | cross-domain (power vs env) |
| V2 | Environment | Temp ramp + HVAC normal + door alarm | Door open / intrusion heat load (X.733 probable causes verbatim, **S3**) | alarm fusion |
| V3 | Environment | Humidity + water sensor after storm | Water intrusion (**S4** out-of-class conditions; storm chain **I5**) | urgency escalation |
| V4 | Environment | Radio thermal shutdown, cabinet normal | Radio fan/unit-level failure — thermal envelope per **S4** (EN 300 019 class 3.1); V9 is background-only, never cite | site-vs-unit scoping |
| R1 | RF | Sector KPIs to zero, unit powered, no alarms | Sleeping cell (method citation arXiv:1501.03935, link-only; traffic realism via Milan CDR, ODbL) | absence-of-alarm reasoning |
| R2 | RF | VSWR 1.9:1 one sector | Feeder/antenna fault — pass criterion **VSWR 1.40 / 15.5 dB RL** (Anritsu S331L guide, fetch-at-build); fault signatures (lightning/corrosion/pinch) same source | the "two voltages" pitch beat |
| R3 | RF | GPS holdover alarm, timing drift | GNSS antenna/receiver loss — countdown from **G.8272** PRTC classes + quartz holdover **<750 ns/24 h only 90%** (Microsemi WP, fetch-at-build, never commit) | time-bounded urgency |
| T1 | Transport | Site unreachable, RAN alarms cease mid-stream | Backhaul fiber cut — BFD Down semantics (**RFC 5880**, committable); repair expectation **mean 13.8 h / median 8.0 h** (AFL/Bellcore) | last-gasp event ordering |
| T2 | Transport | Loss 2% / jitter 9 ms sustained | Microwave degradation — breaches **jitter <3 ms, PDR 99.95%** POP-POP targets (Lumen SLA) / **≤1 ms US** (Verizon SLA, link-only) | degradation ≠ outage |
| T3 | Transport | All services down, site power normal, router unresponsive | Site router failure | power-family false lead |
| N1 | Control | `alarmMajorRectifier` DURING scheduled maintenance window (work order in seeded data) | **No dispatch** — planned work, acknowledge only | false-positive resistance |
| N2 | Control | Dip to −50.2 V for 90 s, self-recovers | **No action** — inside S1's normal −40.5…−57.0 V envelope (**S1**) | threshold discipline |

**Negative controls (N1, N2) scored inversely:** correct output = low-priority
acknowledgment, NO crew dispatch, NO P1. A system that dispatches on everything is an
alarm repeater, not an agent — 2/2 here is the Q&A armor for "what about false positives?"

**Severity/escalation semantics for the Orchestrator:** FCC reportable-outage thresholds
(≥900,000 user-minutes AND ≥30 min…) + NORS escalation timers as the severity ladder
(**47 CFR 4.9**, committable regulation text); 5-level/15-min NOC escalation structure
(CENIC, link-only, anonymize).

**Pitch framing (honest):** demo runs live = E1 + E6. Matrix = measured offline coverage.
"X/16 real-world-derived scenarios top-1, every claim cited" — said out loud. RF/transport
framed as coverage-by-architecture per the taxonomy doc. The foil: Rogers 2022 took
**14 hours to find root cause** (**I4**); Arc's E1 report lands in ~90 seconds, cited.

## Fault-injection notes

- Injector = replay of these JSONL timelines at 10–30× (`--speed` flag); Watchdog
  debounces on event time, not wall time. Optionally hosted on the Pi site rig
  (team-internal rig plan, on Discord) with the REAL CPU-temp channel replacing the NAB-shaped ramp.
- **E4 stays UNSEEN during all tuning** — run once fresh Sunday 09:00 as the overfit check.
- Remaining unpinned values: none load-bearing. Scenario constants (site load 5.6 kW,
  ramp 0.8 °C/min, −18 A discharge) are demo parameters, not sourced claims — never quote
  them as facts.
