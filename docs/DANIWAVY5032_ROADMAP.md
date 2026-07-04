# daniwavy5032 - Personal Roadmap

Source: open GitHub issues in `aminssutt/Arc`, checked on 2026-07-04.

Owner scope:
- `/frontend`: Next.js control-room web for the NOC engineer.
- `/ios`: SwiftUI field technician app and simulator push flow.

Primary demo responsibility: make the human validation loop visible and reliable:
`diagnostic_ready -> push -> iOS validation -> backend intake -> action report -> web`.

## Current Todo

| Issue | Phase | Priority | Workstream | Task | Depends on |
|---|---:|---|---|---|---|
| [#10](https://github.com/aminssutt/Arc/issues/10) | 0 | P0 | iOS | iOS push pipeline via `simctl` | #6, #8 |
| [#11](https://github.com/aminssutt/Arc/issues/11) | 0 | P0 | iOS | iOS scaffold + push handling | #10 |
| [#32](https://github.com/aminssutt/Arc/issues/32) | 1 | P0 | frontend | Next.js scaffold + SSE client on mock replay | #6, #8 |
| [#33](https://github.com/aminssutt/Arc/issues/33) | 1 | P0 | frontend | Event renderer registry | #32 |
| [#38](https://github.com/aminssutt/Arc/issues/38) | 1 | P0 | iOS | Detected-failures list view | #11, #8, #45 |
| [#39](https://github.com/aminssutt/Arc/issues/39) | 1 | P0 | iOS | Validation flow | #38 |
| [#34](https://github.com/aminssutt/Arc/issues/34) | 1 | P1 | frontend | Control-room NOC view | #33, #44 |
| [#35](https://github.com/aminssutt/Arc/issues/35) | 1 | P1 | frontend | Citations UI + diagnostic/prescription cards | #33, #43 |
| [#36](https://github.com/aminssutt/Arc/issues/36) | 1 | P1 | frontend | Prioritized action report view | #35 |
| [#40](https://github.com/aminssutt/Arc/issues/40) | 1 | P1 | iOS | Push-to-screen routing | #38 |
| [#37](https://github.com/aminssutt/Arc/issues/37) | 1 | P2 | frontend | Schematic lights-up-on-citation | #35, #46 |
| [#48](https://github.com/aminssutt/Arc/issues/48) | 2 | P0 | iOS | Push + validation round-trip live | #17, #18, #39, #28 |
| [#50](https://github.com/aminssutt/Arc/issues/50) | 2 | P0 | frontend | Control-room web on the real stream | #34, #36, #16, #23 |
| [#53](https://github.com/aminssutt/Arc/issues/53) | 2 | P1 | iOS | Real APNs wiring with Apple license | #17, #39 |

## Execution Order

1. Unblock iOS demo path:
   - #10: deliver a contract push fixture through `xcrun simctl push`.
   - #11: build the SwiftUI shell and display the simulated push in-app.

2. Build the web mock path in parallel:
   - #32: scaffold Next.js and consume mock SSE replay.
   - #33: add an event renderer registry so each contract event has a single UI entry point.

3. Complete the iOS human loop:
   - #38: render the detected failures from the push payload.
   - #39: implement real/false validation, measurement entry, and submit payload.
   - #40: route notification taps to the correct incident screen.

4. Complete the NOC-facing web experience:
   - #34: build the incident narrative view.
   - #35: show citations and confidence for diagnostic/prescription cards.
   - #36: render the final prioritized action report.

5. Integrate live:
   - #48: prove push -> validation -> intake -> Validation agent handoff on both fixtures.
   - #50: flip the web app from mock SSE to real `/api/stream`.

6. Stretch only after the core path is stable:
   - #37: schematic citation highlights. This is the first trim candidate.
   - #53: real APNs on a physical device. `simctl` remains the demo fallback.

## Critical Path

The minimum demo-critical path for this owner is:

`#10 -> #11 -> #38 -> #39 -> #48`

The minimum web-critical path is:

`#32 -> #33 -> #34 -> #35 -> #36 -> #50`

Do not spend time on #37 before #39 and #36 are working. The iOS validation flow is never trimmed because it is the demo's human loop.

## Acceptance Checklist

Before Phase 1 sync:
- iOS app receives and displays a contract push fixture in the simulator.
- Web app can replay both mock scenarios from the contract fixtures.
- Raw event log exists for debugging unknown event types.
- Both iOS and web parse payloads from the frozen contracts, not local-only shapes.

Before Phase 2 integration:
- iOS can submit confirm and pivot validation payloads.
- Web can render diagnostic, citation, and action-report events.
- Mock-vs-real stream selection is behind a flag.
- Simulator push remains the default path; real APNs is isolated behind a flag.

Before demo lock:
- Confirm run and pivot run both work live.
- Web and iOS can be reset quickly for retakes.
- The fallback plan is tested: simulator push works even if Apple license/APNs is unavailable.

## Coordination Notes

- Wait for #6 and #8 before relying on final event or push payload shapes.
- Coordinate with `designspear-epic` on #45 before finalizing iOS screens.
- Coordinate with `simerugby` on #17, #18, #16, and #23 before Phase 2 live integration.
- Keep `/frontend` and `/ios` changes separated enough that one can be trimmed or debugged without blocking the other.

---

# daniwavy5032 - 개인 로드맵

출처: 2026-07-04 기준 `aminssutt/Arc`의 open GitHub issues.

담당 범위:
- `/frontend`: NOC 엔지니어용 Next.js control-room web.
- `/ios`: 현장 기술자용 SwiftUI 앱과 simulator push flow.

핵심 데모 책임: human validation loop가 눈에 보이고 안정적으로 동작하게 만드는 것.

`diagnostic_ready -> push -> iOS validation -> backend intake -> action report -> web`

## 현재 Todo

| Issue | Phase | Priority | Workstream | Task | Depends on |
|---|---:|---|---|---|---|
| [#10](https://github.com/aminssutt/Arc/issues/10) | 0 | P0 | iOS | `simctl` 기반 iOS push pipeline | #6, #8 |
| [#11](https://github.com/aminssutt/Arc/issues/11) | 0 | P0 | iOS | iOS scaffold + push handling | #10 |
| [#32](https://github.com/aminssutt/Arc/issues/32) | 1 | P0 | frontend | Next.js scaffold + mock SSE client | #6, #8 |
| [#33](https://github.com/aminssutt/Arc/issues/33) | 1 | P0 | frontend | Event renderer registry | #32 |
| [#38](https://github.com/aminssutt/Arc/issues/38) | 1 | P0 | iOS | Detected-failures list view | #11, #8, #45 |
| [#39](https://github.com/aminssutt/Arc/issues/39) | 1 | P0 | iOS | Validation flow | #38 |
| [#34](https://github.com/aminssutt/Arc/issues/34) | 1 | P1 | frontend | Control-room NOC view | #33, #44 |
| [#35](https://github.com/aminssutt/Arc/issues/35) | 1 | P1 | frontend | Citations UI + diagnostic/prescription cards | #33, #43 |
| [#36](https://github.com/aminssutt/Arc/issues/36) | 1 | P1 | frontend | Prioritized action report view | #35 |
| [#40](https://github.com/aminssutt/Arc/issues/40) | 1 | P1 | iOS | Push-to-screen routing | #38 |
| [#37](https://github.com/aminssutt/Arc/issues/37) | 1 | P2 | frontend | Citation 기반 schematic highlight | #35, #46 |
| [#48](https://github.com/aminssutt/Arc/issues/48) | 2 | P0 | iOS | Live push + validation round-trip | #17, #18, #39, #28 |
| [#50](https://github.com/aminssutt/Arc/issues/50) | 2 | P0 | frontend | Real stream 기반 control-room web | #34, #36, #16, #23 |
| [#53](https://github.com/aminssutt/Arc/issues/53) | 2 | P1 | iOS | Apple license 기반 real APNs wiring | #17, #39 |

## 실행 순서

1. iOS 데모 경로 먼저 뚫기:
   - #10: contract push fixture를 `xcrun simctl push`로 simulator에 전달.
   - #11: SwiftUI shell을 만들고 simulated push를 앱에서 표시.

2. Web mock 경로를 병렬로 구축:
   - #32: Next.js scaffold를 만들고 mock SSE replay를 소비.
   - #33: contract event마다 하나의 UI 진입점을 갖도록 event renderer registry 추가.

3. iOS human loop 완성:
   - #38: push payload 기반 detected failures 목록 렌더링.
   - #39: real/false validation, measurement 입력, submit payload 구현.
   - #40: notification tap 시 올바른 incident 화면으로 routing.

4. NOC용 web 경험 완성:
   - #34: incident narrative view 구축.
   - #35: diagnostic/prescription card에 citation과 confidence 표시.
   - #36: 최종 prioritized action report 렌더링.

5. Live 통합:
   - #48: push -> validation -> intake -> Validation agent handoff를 두 fixture에서 검증.
   - #50: web app을 mock SSE에서 실제 `/api/stream`으로 전환.

6. Core path 안정화 이후 stretch:
   - #37: schematic citation highlight. 시간 부족 시 첫 번째 trim 후보.
   - #53: physical device real APNs. `simctl`은 계속 데모 fallback으로 유지.

## Critical Path

이 담당자의 최소 데모 critical path:

`#10 -> #11 -> #38 -> #39 -> #48`

Web 최소 critical path:

`#32 -> #33 -> #34 -> #35 -> #36 -> #50`

#37은 #39와 #36이 동작하기 전에는 하지 않는다. iOS validation flow는 데모의 human loop라서 trim 대상이 아니다.

## Acceptance Checklist

Phase 1 sync 전:
- iOS app이 simulator에서 contract push fixture를 수신하고 표시한다.
- Web app이 contract fixtures의 mock scenario 두 개를 replay할 수 있다.
- unknown event type 디버깅을 위한 raw event log가 있다.
- iOS와 web 모두 local-only shape가 아니라 frozen contracts payload를 parse한다.

Phase 2 integration 전:
- iOS가 confirm/pivot validation payload를 submit할 수 있다.
- Web이 diagnostic, citation, action-report event를 렌더링할 수 있다.
- mock-vs-real stream 선택이 flag 뒤에 있다.
- simulator push가 default path이고, real APNs는 flag 뒤에 격리돼 있다.

Demo lock 전:
- Confirm run과 pivot run이 모두 live로 동작한다.
- Web과 iOS를 retake용으로 빠르게 reset할 수 있다.
- Apple license/APNs가 없어도 simulator push fallback이 동작한다.

## Coordination Notes

- 최종 event/push payload shape에 의존하기 전에 #6과 #8을 기다린다.
- iOS 화면 확정 전 `designspear-epic`과 #45를 맞춘다.
- Phase 2 live integration 전 `simerugby`와 #17, #18, #16, #23을 맞춘다.
- `/frontend`와 `/ios` 변경은 서로 디버깅/trim 가능한 수준으로 분리해서 진행한다.
