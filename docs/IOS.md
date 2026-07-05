# iOS — Arc operator app

The field-technician app lives in `ios/`. Native SwiftUI, two screens: it
receives an APNs diagnostic push, the technician **Validates** or **Refuses**
(with a counter-measurement), and it POSTs the verdict to the backend, which
then either confirms or pivots the diagnosis.

- Bundle id: `com.arc.operator` (`ios/project.yml`, `PRODUCT_BUNDLE_IDENTIFIER`)
- Development team: `AQD6GDJ33X` (Lakhdar Berache)
- Deployment target: iOS 18.0; built against the iOS 26.5 SDK (Xcode 26)
- Swift 5.0; portrait only; forced dark color scheme (`ArcApp.swift`)

## Architecture (SwiftUI, `ios/Arc/Sources/`)

| File | Responsibility |
|------|----------------|
| `ArcApp.swift` | `@main` `App`. Installs `AppDelegate` via `@UIApplicationDelegateAdaptor`, injects `AppModel.shared` into the environment, forces `.dark`. |
| `AppDelegate.swift` | Bridges UIKit push callbacks into the `@Observable` model. On launch requests push authorization; on `didRegisterForRemoteNotificationsWithDeviceToken` hex-encodes the token and forwards it; foreground push (`willPresent`) shows a banner **and** opens the card; a tapped push (`didReceive`) deep-links into Screen A. |
| `AppModel.swift` | `@MainActor @Observable` singleton. Owns routing, the current `Diagnostic`, the submission state machine, the persisted `baseURL`, and the push lifecycle. |
| `ArcAPI.swift` | Thin async client for the two backend endpoints (`/api/devices`, `/api/validation`). 15 s timeout; typed errors (`badURL`, `http(code, detail)`, `transport`). |
| `Models.swift` | The wire types: incoming `Diagnostic` (+ `PushSite` / `PushFailure` / `PushReading`) parsed from the APNs `userInfo`, and the outgoing `ValidationEvent` (frozen contract) with `confirm` / `reject` factories. |
| `RootView.swift` | `NavigationStack` that switches on `model.route`; hosts `AwaitingView` and the gear → `SettingsView`. |
| `DiagnosticViews.swift` | Screen A (`IncomingDiagnosticView`) and Screen B (`CounterMeasurementView`). |
| `ConfirmationView.swift` | The post-submit result screen (sending / sent / already-handled / errors). |
| `Theme.swift` | `ArcTheme` colors, wordmark, shared button/card labels. |

## The two screens and their states

`AppModel.Route` drives navigation: `awaiting → diagnostic (Screen A) →
counterMeasure (Screen B) → confirmation`.

- **Awaiting** (`AwaitingView`, `RootView.swift`) — the idle landing before a
  push. Shows the live `pushStatus` and a **Load sample incident** button that
  drives both screens by hand with no push (mirrors the pivot fixture; the
  reading is below the −47 V threshold).
- **Screen A — diagnostic card** (`IncomingDiagnosticView`) — the dispatch
  ticket: a `FIELD VALIDATION REQUESTED` banner, site location + severity badge,
  a **Reading** hero (the telemetry value in XXL mono when the push carries a
  `reading`, otherwise the alarm code), the **Probable cause** in one sentence
  (**no confidence score is ever shown** — deliberate, `Models.swift:66`), an
  "also detected" list, and incident meta. Action bar: **Refuse** → Screen B,
  **Validate** → submit.
- **Screen B — counter-measurement** (`CounterMeasurementView`) — a numeric
  value + unit field labelled `DC voltage · busbar`, with input validation
  (comma normalized to a dot, non-numeric rejected). **Send** submits the
  refusal with the measurement.
- **Confirmation** (`ConfirmationView`) renders `AppModel.Submission`:
  - `sending` — spinner.
  - `sent(result)` — "Sent — agent is finishing"; the caption reflects the
    backend `result` (`confirmed` → writing the action report; `pivot` → the
    agent is re-diagnosing live).
  - `alreadyHandled` — **HTTP 409**, treated as success, not an error: "Already
    handled … it was already closed." Offers "Back to awaiting".
  - `networkError` / `serverError` — offer **Retry** (re-sends the *same*
    `client_event_id`) or "Back to diagnostic".

## The push (APNs) flow

1. **Register.** On first launch `AppModel.requestPushAuthorization()` asks for
   `.alert/.sound/.badge`; on grant it calls
   `UIApplication.registerForRemoteNotifications()`.
2. **Token → backend.** `AppDelegate.didRegisterForRemoteNotifications…`
   hex-encodes the device token and `AppModel.registerDeviceToken` POSTs it to
   `POST /api/devices` (`{ device_token, platform: "ios", operator_id: null }`).
3. **Fault → push.** When the backend notifies the matched technician, APNs
   delivers the diagnostic payload (`contracts/push_payload.schema.json`:
   `aps.alert{title,body}`, `incident_id`, `site`, `family`, `failures[]`, and
   an optional `reading`).
4. **Tap → deep-link.** Tapping the notification (or receiving it in the
   foreground) builds a `Diagnostic` from the `userInfo` and routes to Screen A.
   The `Diagnostic(userInfo:)` initializer is defensive: extra keys such as
   simctl's `Simulator Target Bundle` are ignored, and a missing or malformed
   `reading` never breaks the card (it just leaves `reading == nil`).

## The validation payloads (frozen `validation_event.schema.json`)

The app always sends the full enforced contract, never a `{status}` shortcut
(that would 422). Confirm vs pivot is decided **by the backend** from the
verdicts plus the measurement — the app does not send a verdict keyword.

- **Validate** (`ValidationEvent.confirm`) — every detected failure gets
  `verdict: "real"`, and **no** measurement. → backend confirms.
- **Refuse** (`ValidationEvent.reject`) — the load-bearing failure (the DC
  undervoltage) gets `verdict: "false"`, all others `"real"`, plus one
  measurement `{ metric: "dc_voltage_v", point: "busbar", value, unit }`. A
  value below the −47 V threshold (e.g. **−53.9 V**) contradicts the diagnosis
  and drives the pivot.

Frozen shape (`Models.swift:145`):

```
{
  "incident_id":     "<from the push payload>",
  "client_event_id": "<per-submission UUID, reused verbatim on retry>",
  "submitted_at":    "<ISO 8601>",
  "technician":      { "id": "tech-ios", "name": "Field Technician" },
  "validations":     [ { "failure_id": "F1", "verdict": "real|false", "note": null } ],
  "measurements":    [ { "metric": "dc_voltage_v", "point": "busbar", "value": -53.9, "unit": "V" } ]
}
```

`client_event_id` is a fresh UUID per submission, **reused unchanged on retry**
so the backend can dedupe idempotently. The backend replies
`{ status, incident_id, result }` where `result` is `confirmed` or `pivot`.

## In-app configuration (base URL)

The backend base URL is user-configurable in-app via the gear → **Settings**
(`RootView.swift`). It is persisted in `UserDefaults` under `arc.baseURL` and
defaults to `http://192.168.1.10:8000`. Settings also surfaces the truncated
APNs token and the live push status.

> **Never `localhost`.** On a physical device `localhost` is the phone itself.
> Use the Mac's LAN IP and port 8000. Cleartext HTTP to the LAN works because
> `Info.plist` sets `NSAppTransportSecurity → NSAllowsLocalNetworking`.

## Build (XcodeGen)

The Xcode project is generated from `ios/project.yml` by XcodeGen — do not
hand-edit capabilities in Xcode. `project.yml` already declares
`DEVELOPMENT_TEAM = AQD6GDJ33X`, `CODE_SIGN_STYLE = Automatic`, the
`Arc.entitlements` (`aps-environment = development`), the `remote-notification`
background mode, and the local-networking ATS exception (both in `Info.plist`).

Regenerate only after editing `project.yml`:

```bash
cd ios
xcodegen generate     # rewrites Arc.xcodeproj from project.yml
```

### Device setup, step by step (from `ios/README.md`)

1. Open `ios/Arc.xcodeproj` in Xcode 26.
2. Target **Arc → Signing & Capabilities**: confirm Team = **Lakhdar Berache**
   (`AQD6GDJ33X`) and *Automatically manage signing* is on. Push Notifications
   and Background Modes → Remote notifications should already be listed — do not
   re-add.
3. Plug in the iPhone (same Wi-Fi as the Mac) and select it as the run
   destination.
4. Press **Run** (⌘R).
5. On the iPhone, if prompted, **Trust** the developer certificate
   (Settings → General → VPN & Device Management → Developer App → Trust).
6. On first launch tap **Allow** on the notifications prompt — the app registers
   and POSTs its token to `/api/devices`.
7. Gear → set **Backend** to the Mac's LAN IP (e.g. `http://192.168.1.10:8000`).

### Demo paths

- **Real device (stage path):** inject the fault on the backend → the APNs push
  lands → tap it → Screen A → Validate, or Refuse + `-53.9 V` → Send.
- **Simulator (offline UI test):** run on a booted simulator, then
  `xcrun simctl push booted contracts/push_fixtures/push_pivot.json`.
- **No push at all (fallback):** tap **Load sample incident** on the awaiting
  screen to drive both screens by hand.

## APNs sandbox vs production (why not TestFlight for the demo)

The entitlement pins `aps-environment = development`
(`ios/Arc/Arc.entitlements`), i.e. the **sandbox** APNs environment, and the
backend's push service targets the sandbox APNs host by default
(`backend/app/apns_client.py`, `use_sandbox: bool = True`). The push topic is
the bundle id, `com.arc.operator` (`apns-topic`), consistent with the backend
setting `ARC_PUSH_BUNDLE_ID` (default `com.arc.operator`).

A TestFlight build runs the **production** APNs environment
(`aps-environment = production`): the device tokens minted there are production
tokens that the sandbox APNs server will reject, so the backend would have to be
repointed at the production APNs host with production provisioning. For a 3-minute
stage demo that trade-off isn't worth it — the app is installed straight from
Xcode onto a plugged-in device, keeping the sandbox token ↔ sandbox APNs path
matched end to end. See `docs/BACKEND-API.md` for the server-side push service.
