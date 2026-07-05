import SwiftUI
import UIKit
import UserNotifications

@MainActor
@Observable
final class AppModel {
    static let shared = AppModel()

    enum Route {
        case awaiting        // no diagnostic yet — waiting for a push
        case diagnostic      // Screen A
        case counterMeasure  // Screen B
        case confirmation    // sending / sent / errors
    }

    /// Post-submit states. `recap` is a one-line summary of what was sent.
    enum Submission: Equatable {
        case idle
        case sending
        case sent(result: String?, recap: String)
        case alreadyHandled(recap: String, detail: String)   // HTTP 409
        case networkError(recap: String, message: String)    // transport failure
        case serverError(recap: String, message: String)     // other 4xx/5xx
    }

    // Routing + data
    var route: Route = .awaiting
    var diagnostic: Diagnostic?
    var submission: Submission = .idle

    // Push / device
    var deviceTokenHex: String?
    var pushStatus: String = "Listening for dispatch."

    // Settings (persisted)
    var baseURL: String {
        didSet { UserDefaults.standard.set(baseURL, forKey: Self.baseURLKey) }
    }
    let technician = Technician(id: "tech-ios", name: "Field Technician")

    private static let baseURLKey = "arc.baseURL"
    private static let defaultBaseURL = "http://192.168.1.10:8000"

    private let api = ArcAPI()
    private var pendingEvent: ValidationEvent?   // retried verbatim (same client_event_id)
    private var pendingRecap: String?

    private init() {
        baseURL = UserDefaults.standard.string(forKey: Self.baseURLKey) ?? Self.defaultBaseURL
    }

    // MARK: - Push lifecycle  (UNCHANGED behaviour)

    func requestPushAuthorization() async {
        let center = UNUserNotificationCenter.current()
        do {
            let granted = try await center.requestAuthorization(options: [.alert, .sound, .badge])
            if granted {
                UIApplication.shared.registerForRemoteNotifications()
                pushStatus = "Listening for dispatch."
            } else {
                pushStatus = "Notifications are off — enable them in iOS Settings."
            }
        } catch {
            pushStatus = "Notification permission error: \(error.localizedDescription)"
        }
    }

    func registerDeviceToken(_ hex: String) async {
        deviceTokenHex = hex
        do {
            try await api.registerDevice(token: hex, baseURL: baseURL)
            pushStatus = "Registered — listening for dispatch."
        } catch {
            pushStatus = "Token not delivered to backend: \(error.localizedDescription)"
        }
    }

    func pushRegistrationFailed(_ message: String) {
        pushStatus = "APNs registration failed: \(message)"
    }

    /// A push arrived (tapped or in foreground): show Screen A.
    func present(diagnostic: Diagnostic) {
        self.diagnostic = diagnostic
        self.submission = .idle
        self.pendingEvent = nil
        self.pendingRecap = nil
        self.route = .diagnostic
    }

    // MARK: - Validation actions  (payloads UNCHANGED)

    func validate() async {
        guard let d = diagnostic else { return }
        let n = d.failures.count
        let recap = "Validated · \(n) failure\(n == 1 ? "" : "s") confirmed real"
        await submit(.confirm(diagnostic: d, technician: technician), recap: recap)
    }

    func refuse(value: Double, unit: String) async {
        guard let d = diagnostic else { return }
        let recap = "Refused · busbar \(Self.trim(value)) \(unit)"
        await submit(.reject(diagnostic: d, value: value, unit: unit, technician: technician), recap: recap)
    }

    func retry() async {
        if let e = pendingEvent, let r = pendingRecap {
            await submit(e, recap: r)
        }
    }

    private func submit(_ event: ValidationEvent, recap: String) async {
        pendingEvent = event
        pendingRecap = recap
        submission = .sending
        route = .confirmation
        do {
            let resp = try await api.submitValidation(event, baseURL: baseURL)
            submission = .sent(result: resp.result, recap: recap)
            pendingEvent = nil
            pendingRecap = nil
        } catch APIError.http(let code, let detail) where code == 409 {
            // Not an error: the incident is no longer awaiting validation.
            submission = .alreadyHandled(recap: recap, detail: Self.shortServer(detail))
            pendingEvent = nil
            pendingRecap = nil
        } catch APIError.http(let code, let detail) {
            submission = .serverError(recap: recap, message: "Rejected (\(code)) · \(Self.shortServer(detail))")
        } catch APIError.transport(let message) {
            submission = .networkError(recap: recap, message: message)
        } catch {
            submission = .networkError(recap: recap, message: error.localizedDescription)
        }
    }

    // MARK: - Navigation helpers

    func goToCounterMeasure() { route = .counterMeasure }
    func backToDiagnostic() { route = .diagnostic; submission = .idle }

    func reset() {
        route = .awaiting
        diagnostic = nil
        submission = .idle
        pendingEvent = nil
        pendingRecap = nil
    }

    /// Demo fallback: a sample incident so both screens are showable without a
    /// live push (mirrors the pivot fixture — a value below -47 V triggers the pivot).
    func loadSampleIncident() {
        present(diagnostic: Diagnostic(
            incidentID: "INC-DEMO-002",
            site: PushSite(id: "PAR-021-NORD", name: "Paris Nord macro site",
                           lat: 48.8969, lon: 2.3383,
                           address: "Rue de la Chapelle, 75018 Paris"),
            family: "energy",
            failures: [
                PushFailure(id: "F1", code: "alarmMajorRectifier", severity: "major", equipment: "rectifier-2"),
                PushFailure(id: "F2", code: "DC_UNDERVOLTAGE", severity: "major", equipment: "busbar"),
            ],
            title: "Arc — PAR-021-NORD: energy fault",
            body: "2 detected failures await field validation",
            receivedAt: Date(),
            reading: PushReading(value: -44.8, unit: "V", point: "busbar", metric: "dc_voltage_v")
        ))
    }

    // MARK: - Helpers

    /// Trim a trailing ".0" so "-53.9" stays "-53.9" and "-48.0" reads "-48".
    static func trim(_ value: Double) -> String {
        value == value.rounded() ? String(Int(value)) : String(value)
    }

    /// Pull the human message out of a FastAPI `{"detail": ...}` error body.
    static func shortServer(_ raw: String) -> String {
        let s = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if let data = s.data(using: .utf8),
           let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let detail = obj["detail"] {
            if let str = detail as? String { return str }
            if let arr = detail as? [Any] { return arr.map { "\($0)" }.joined(separator: "; ") }
        }
        return s.isEmpty ? "no detail" : String(s.prefix(200))
    }
}
