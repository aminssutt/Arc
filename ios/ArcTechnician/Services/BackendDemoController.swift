import Foundation

@MainActor
final class BackendDemoController: ObservableObject {
    @Published var baseURLString: String {
        didSet {
            UserDefaults.standard.set(baseURLString, forKey: Self.baseURLDefaultsKey)
        }
    }
    @Published private(set) var statusText = "Backend not checked."
    @Published private(set) var isStreamConnected = false
    @Published private(set) var recentEvents: [BackendEventEnvelope] = []

    private var streamTask: Task<Void, Never>?

    private static let baseURLDefaultsKey = "ArcBackendBaseURL"
    private static let fallbackBaseURLString = "http://192.168.10.223:8000"

    init() {
        baseURLString = UserDefaults.standard.string(forKey: Self.baseURLDefaultsKey) ?? Self.fallbackBaseURLString
    }

    deinit {
        streamTask?.cancel()
    }

    func checkHealth() {
        run { client in
            let response = try await client.health()
            return "Health: \(response.status), state: \(response.state)"
        }
    }

    func inject(_ scenario: DemoScenario) {
        connectStream()
        run { client in
            let response = try await client.injectFault(InjectFaultRequest(scenario: scenario))
            return "Injected \(response.scenario): \(response.incidentId ?? "no incident"), state: \(response.state)"
        }
    }

    func reset() {
        run { client in
            let response = try await client.reset()
            return "Reset: \(response.status)"
        }
        recentEvents.removeAll()
    }

    func submitValidation(for incident: IncidentPushPayload?, verdict: ValidationVerdict) {
        guard let incident else {
            statusText = "No incident loaded."
            return
        }

        run { client in
            let response = try await client.submitValidation(.demoPayload(for: incident, verdict: verdict))
            return "Validation accepted: \(response.incidentId), result: \(response.result)"
        }
    }

    func connectStream() {
        guard streamTask == nil else { return }

        do {
            let client = try makeClient()
            isStreamConnected = true
            statusText = "Stream connected."

            streamTask = Task { [weak self] in
                guard let self else { return }

                do {
                    for try await event in client.eventStream() {
                        self.handle(event)
                    }
                } catch is CancellationError {
                    self.markStreamDisconnected(message: "Stream disconnected.")
                } catch {
                    self.markStreamDisconnected(message: "Stream error: \(error.localizedDescription)")
                }
            }
        } catch {
            statusText = "Backend URL error: \(error.localizedDescription)"
        }
    }

    func disconnectStream() {
        streamTask?.cancel()
        streamTask = nil
        isStreamConnected = false
        statusText = "Stream disconnected."
    }

    private func run(_ operation: @escaping (BackendClient) async throws -> String) {
        Task {
            do {
                let client = try makeClient()
                statusText = try await operation(client)
            } catch {
                statusText = "Backend error: \(error.localizedDescription)"
            }
        }
    }

    private func makeClient() throws -> BackendClient {
        guard let baseURL = URL(string: baseURLString) else {
            throw BackendClientError.invalidBaseURL
        }
        return BackendClient(baseURL: baseURL)
    }

    private func handle(_ event: BackendEventEnvelope) {
        recentEvents.insert(event, at: 0)
        recentEvents = Array(recentEvents.prefix(8))
        statusText = "Event: \(event.type)"

        guard event.type == "push_sent",
              let payload = event.data["payload"]?.jsonObject as? [String: Any] else {
            return
        }

        PushNotificationRouter.shared.handle(userInfo: payload)
    }

    private func markStreamDisconnected(message: String) {
        streamTask = nil
        isStreamConnected = false
        statusText = message
    }
}
