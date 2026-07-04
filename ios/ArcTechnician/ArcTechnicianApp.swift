import SwiftUI
import UserNotifications

@main
struct ArcTechnicianApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var pushRouter = PushNotificationRouter.shared

    init() {
        PushNotificationRouter.shared.requestAuthorization()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(pushRouter)
        }
    }
}
