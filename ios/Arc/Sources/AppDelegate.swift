import UIKit
import UserNotifications

/// Bridges UIKit's push callbacks into the SwiftUI @Observable AppModel.
final class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        Task { @MainActor in
            await AppModel.shared.requestPushAuthorization()
        }
        return true
    }

    func application(_ application: UIApplication,
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        let hex = deviceToken.map { String(format: "%02x", $0) }.joined()
        Task { @MainActor in
            await AppModel.shared.registerDeviceToken(hex)
        }
    }

    func application(_ application: UIApplication,
                     didFailToRegisterForRemoteNotificationsWithError error: Error) {
        Task { @MainActor in
            AppModel.shared.pushRegistrationFailed(error.localizedDescription)
        }
    }

    // Foreground push: show a banner AND open the diagnostic card.
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                willPresent notification: UNNotification) async
        -> UNNotificationPresentationOptions {
        if let diagnostic = Diagnostic(userInfo: notification.request.content.userInfo) {
            await MainActor.run { AppModel.shared.present(diagnostic: diagnostic) }
        }
        return [.banner, .sound, .list]
    }

    // Tap on the notification: deep-link into Screen A with the payload.
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                didReceive response: UNNotificationResponse) async {
        if let diagnostic = Diagnostic(userInfo: response.notification.request.content.userInfo) {
            await MainActor.run { AppModel.shared.present(diagnostic: diagnostic) }
        }
    }
}
