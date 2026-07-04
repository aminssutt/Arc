# /contracts/push_fixtures — exact demo push payloads (P0.8)

Payloads conform to `../push_payload.schema.json`. The iOS app is driven by these
with **zero backend**: swapping to the real push service changes nothing in the app.

## Send to the booted simulator (the demo path)

```bash
xcrun simctl push booted push_confirm.json   # Run 1 — CONFIRM (3 failures)
xcrun simctl push booted push_pivot.json     # Run 2 — PIVOT   (2 failures)
```

No bundle id argument needed: the `"Simulator Target Bundle"` key inside each file
targets the app. To target a specific simulator, replace `booted` with its UDID
(`xcrun simctl list devices`).

- Bundle id `com.arc.technician` is the standardized value — real-device signed &
  APNs-sandbox verified (daniwavy5032, 2026-07-04); if it ever changes, update the two
  fixtures + `push_payload.schema.json` example in the same PR (contract change process
  applies after freeze).
- `"Simulator Target Bundle"` is simctl-only; the real APNs path (INT.7, flag-gated)
  sends the same JSON minus that key.
