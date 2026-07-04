import Foundation
import UIKit
import UserNotifications

@MainActor
final class PushNotificationRouter: ObservableObject {
    static let shared = PushNotificationRouter()

    @Published private(set) var currentIncident: IncidentPushPayload?
    @Published private(set) var lastError: String?
    @Published private(set) var deviceToken: String?
    @Published private(set) var registrationError: String?

    private let decoder: JSONDecoder

    private init(decoder: JSONDecoder = JSONDecoder()) {
        self.decoder = decoder
    }

    func requestAuthorization() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, error in
            Task { @MainActor in
                if let error {
                    self.registrationError = error.localizedDescription
                    return
                }

                guard granted else {
                    self.registrationError = "Notification permission was not granted."
                    return
                }

                UIApplication.shared.registerForRemoteNotifications()
            }
        }
    }

    func setDeviceToken(_ token: String) {
        deviceToken = token
        registrationError = nil
    }

    func setRegistrationError(_ message: String) {
        registrationError = message
    }

    func loadSampleIncident() {
        currentIncident = SampleIncidentFactory.payload()
        lastError = nil
    }

    func clearIncident() {
        currentIncident = nil
        lastError = nil
    }

    func sendLocalTestNotification() {
        let content = UNMutableNotificationContent()
        content.title = "Arc field validation"
        content.body = "Battery Plant 3 needs physical validation at Paris-North Tower."
        content.sound = .default
        content.userInfo = SampleIncidentFactory.userInfo()

        let request = UNNotificationRequest(
            identifier: "arc-local-test-\(UUID().uuidString)",
            content: content,
            trigger: UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
        )

        UNUserNotificationCenter.current().add(request)
    }

    func handle(userInfo: [AnyHashable: Any]) {
        do {
            let payload = try Self.decodePayload(from: userInfo, decoder: decoder)
            currentIncident = payload
            lastError = nil
        } catch {
            lastError = "Push payload could not be parsed: \(error.localizedDescription)"
        }
    }

    static func decodePayload(from userInfo: [AnyHashable: Any], decoder: JSONDecoder = JSONDecoder()) throws -> IncidentPushPayload {
        let normalized = normalizeDictionary(userInfo)
        let appPayload = normalized.filter { key, _ in
            key != "aps" && key != "Simulator Target Bundle"
        }
        let data = try JSONSerialization.data(withJSONObject: appPayload, options: [])
        return try decoder.decode(IncidentPushPayload.self, from: data)
    }

    private static func normalizeDictionary(_ dictionary: [AnyHashable: Any]) -> [String: Any] {
        dictionary.reduce(into: [String: Any]()) { result, pair in
            guard let key = pair.key as? String else { return }
            result[key] = normalizeValue(pair.value)
        }
    }

    private static func normalizeValue(_ value: Any) -> Any {
        if let dictionary = value as? [AnyHashable: Any] {
            return normalizeDictionary(dictionary)
        }

        if let array = value as? [Any] {
            return array.map(normalizeValue)
        }

        return value
    }
}
