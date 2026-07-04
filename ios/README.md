# Arc Technician iOS

SwiftUI field technician app for Arc's human validation loop.

Current scope:
- Receive a simulator push payload with `xcrun simctl push` or a sandbox APNs push.
- Parse the incident id, site, failure family, and detected failures.
- Display the push content in-app.
- Keep iOS models aligned with the backend branch contracts.

Bundle id:

```sh
com.arc.technician
```

## Requirements

Use the local Xcode beta. You can either export `DEVELOPER_DIR` per shell:

```sh
export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer
```

Or prefix individual commands:

```sh
DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer xcodebuild -version
```

## Run

Open the project:

```sh
open ios/ArcTechnician.xcodeproj
```

Run the `ArcTechnician` scheme on an iOS simulator.

CLI build example:

```sh
DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer \
  xcodebuild \
  -project ios/ArcTechnician.xcodeproj \
  -scheme ArcTechnician \
  -destination 'platform=iOS Simulator,name=iPhone 17,OS=27.0' \
  build
```

Real device build example:

```sh
DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer \
  xcodebuild \
  -project ios/ArcTechnician.xcodeproj \
  -scheme ArcTechnician \
  -destination 'platform=iOS,id=00008120-000679442650C01E' \
  -allowProvisioningUpdates \
  build
```

Install and launch on the connected iPhone:

```sh
DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer \
  xcrun devicectl device install app \
  --device 00008120-000679442650C01E \
  ~/Library/Developer/Xcode/DerivedData/ArcTechnician-*/Build/Products/Debug-iphoneos/ArcTechnician.app

DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer \
  xcrun devicectl device process launch \
  --device 00008120-000679442650C01E \
  com.arc.technician
```

## Push Fixture

With the app installed on the simulator, send the sample push:

```sh
DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer \
  xcrun simctl push booted com.arc.technician ios/Fixtures/sample_fault_push.apns
```

The app should show the incident, site, failure family, and detected failures.

The current fixture mirrors the backend contract branch payload shape:
- `incident_id`
- `site.id`, `site.name`, `site.lat`, `site.lon`, `site.address`
- `family`
- `failures[].id`, `failures[].code`, `failures[].severity`, `failures[].equipment`

The canonical demo bundle id and APNs topic is `com.arc.technician`. Backend push settings, simulator fixtures, and local APNs sends should all use that value.

## Real Device Push Notes

`simctl push` is simulator-only. On a physical iPhone, remote push requires APNs credentials, a registered device token, and a server-side APNs send path.

Until APNs is wired, use the in-app local test notification button. It sends the same incident-shaped payload through `UNUserNotificationCenter`, so the notification handler and incident UI can be validated on the real device without APNs.

For APNs from localhost:

1. Run the app on the iPhone.
2. Copy the APNs device token shown on the first screen.
3. Create `.env` at the repo root:

```sh
APNS_KEY_ID=34X28TZMSS
APNS_TEAM_ID=LN5K5N2ANY
APNS_BUNDLE_ID=com.arc.technician
APNS_DEVICE_TOKEN=<token from app>
APNS_AUTH_KEY_PATH=/Users/ohyeon-u/Desktop/Arc/ios/AuthKey_34X28TZMSS.p8
APNS_ENV=sandbox
```

4. Send the demo push:

```sh
python3 scripts/send_apns_push.py
```

## Backend Contract Alignment

The backend contract branch currently exposes:
- `GET /health`
- `POST /api/demo/inject-fault`
- `GET /api/stream`
- `POST /api/validation`
- `POST /api/demo/reset`

iOS model coverage:
- `IncidentPushPayload` decodes the APNs incident payload.
- `BackendClient` calls `GET /health`, `POST /api/demo/inject-fault`, `GET /api/stream`, `POST /api/validation`, and `POST /api/demo/reset`.
- `BackendEventEnvelope` decodes SSE envelopes from `/api/stream`.
- `ValidationSubmission` encodes the `POST /api/validation` body.
- `ValidationClient` posts validation results to `/api/validation` and decodes `{status, incident_id, result}`.

## Local Backend Demo

Run the backend branch from a separate checkout:

```sh
cd /tmp/arc-backend-check
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
ARC_PUSH_MODE=file \
ARC_PUSH_BUNDLE_ID=com.arc.technician \
ARC_PUSH_OUT_DIR=/tmp/arc-push-out \
  .venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

The current Mac LAN URL is:

```sh
http://192.168.10.223:8000
```

The in-app backend panel uses that URL by default. On a physical iPhone, do not use `localhost`; use the Mac LAN IP because `localhost` points to the phone.

Backend panel flow:

1. Tap `Health`.
2. Tap `Start Stream`.
3. Tap `Inject Confirm` or `Inject Pivot`.
4. When the `push_sent` SSE event arrives, the app loads the incident payload from the event.
5. Tap `Submit Real` or `Submit False`.
6. Tap `Reset Backend` before another run.

Validation submission body shape:

```json
{
  "incident_id": "INC-LIVE-001",
  "client_event_id": "ios-demo-1",
  "submitted_at": "2026-07-05T09:33:00Z",
  "technician": {"id": "daniwavy5032", "name": "daniwavy5032"},
  "validations": [{"failure_id": "F1", "verdict": "real"}],
  "measurements": [{"metric": "dc_plant_voltage_v", "point": "busbar", "value": 43.9, "unit": "V"}]
}
```

## Design Integration Notes

Design-facing code is intentionally separated:
- `ArcTechnician/Design/DesignTokens.swift`: color, spacing, type, and corner radius tokens.
- `ArcTechnician/Views`: reusable SwiftUI surfaces.
- `ArcTechnician/Models`: payload and domain types.
- `ArcTechnician/Services`: push routing and notification handling.

When DS.5 lands, update tokens and view composition without changing push parsing or routing.
