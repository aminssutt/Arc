# /data/scenarios — deterministic demo-run signal timelines (DEMO.2, #55)

**Owner:** simerugby (announced per the one-owner-per-file rule).

One JSON object per line = one raw feed signal, replayed by
`POST /api/demo/inject-fault {"scenario": "confirm"|"pivot"}`:

```json
{"ts": ISO-8601, "site_id": "PAR-021-NORD", "signal": "<canonical metric §1.1>",
 "value": <signed number|0/1>, "equipment_id": "<equipment/point>", "trap": "<raw trap, optional>"}
```

- `signal`/`value` follow the canonical metric vocabulary (`data/schema.md` §1.1):
  `dc_voltage_v` is SIGNED (negative); the Watchdog compares magnitude to the
  alarm-dictionary threshold.
- `trap` is the raw feed code carried into `FaultEvent.failure.code` (frozen
  fixtures); the Watchdog maps it to the canonical `alarm_code` via
  `data/trap_map.csv` to index the alarm dictionary.
- Debounce runs on EVENT time (`ts`), so wall-clock replay speed is irrelevant:
  both timelines fire deterministically — `alarmMajorRectifier` after 31 s held,
  `DC_UNDERVOLTAGE` after 61 s held, one FaultEvent carrying both failures.
- **Confirm** run: sag reaches `-44.8 V` (abnormal, technician confirms) with a
  cabinet `temp_c` rise (below the HVAC threshold — ambient corroboration only).
- **Pivot** run: identical alarm opening, NO thermal corroboration; the
  difference plays out in the technician's answer (`-53.9 V` measured = normal
  float → sensing-card pivot). Values pinned to
  `validation/GROUND_TRUTH_SCENARIOS.md` / `data/schema.md` §"Two demo scenarios".
