# Arc — iOS operator app

Native SwiftUI, 2 screens. Receives an APNs diagnostic push, the operator
Validates or Refuses with a counter-measurement, and posts to the backend.

- Bundle id: `com.arc.operator` (registered Apple App ID)
- Team: `AQD6GDJ33X` (Lakhdar Berache)
- Deployment target: iOS 18.0 · built against the iOS 26.5 SDK (Xcode 26.6)

## Regenerate the project (only if you edit `project.yml`)

```bash
cd ios
xcodegen generate            # rewrites Arc.xcodeproj from project.yml
```

`project.yml` already declares: DEVELOPMENT_TEAM, the `aps-environment=development`
entitlement, Push Notifications + Background Modes (remote-notification), and
`NSAppTransportSecurity → NSAllowsLocalNetworking` (for the local HTTP backend).
You do **not** add any of these by hand in Xcode.

## Xcode UI checklist (what's left for the human)

Everything about capabilities/entitlements/ATS is already wired by `project.yml`.
Remaining clicks, in order:

1. Open `ios/Arc.xcodeproj` in Xcode 26.
2. Target **Arc → Signing & Capabilities**: confirm Team = **Lakhdar Berache**
   (`AQD6GDJ33X`) and "Automatically manage signing" is on. Push Notifications
   and Background Modes → Remote notifications should already be listed — do not re-add.
3. Plug in the iPhone (same Wi-Fi as the Mac). Select it as the run destination
   (top device picker).
4. Press **Run** (⌘R).
5. On the iPhone: if prompted, **Trust** the developer certificate
   (Settings → General → VPN & Device Management → Developer App → Trust).
6. On first launch, tap **Allow** on the notifications permission prompt.
   The app registers for remote notifications and POSTs its token to `/api/devices`.
7. Tap the gear (top-right) → set **Backend** to the Mac's LAN IP, e.g.
   `http://192.168.1.10:8000` (never `localhost`). It persists.

## Demo paths

- **Real device (stage path):** inject the fault on the backend → APNs push lands →
  tap it → Screen A → Validate, or Refuse + `-53.9` V → Send.
- **Simulator (offline UI test):** run on a booted simulator, then
  `xcrun simctl push booted contracts/push_fixtures/push_pivot.json`.
- **No push at all (fallback):** tap "Load sample incident" on the awaiting screen
  to drive both screens by hand.

## The two validation payloads (frozen `validation_event.schema.json`)

The app sends the **enforced backend contract** (not a `{status}` shortcut — that
would 422). Confirm/pivot is decided by the backend from the verdicts + measurement:

- **Validate** → every failure `verdict: "real"`, no measurement → agent **confirms**.
- **Refuse** → the DC-undervoltage failure `verdict: "false"` + measurement
  `{metric: "dc_voltage_v", point: "busbar", value, unit}`. A value below the
  −47 V threshold (e.g. **−53.9 V**) contradicts the diagnosis → agent **pivots**.

`incident_id` comes from the push payload; `client_event_id` is a per-submission
UUID reused on retry (backend idempotency).
