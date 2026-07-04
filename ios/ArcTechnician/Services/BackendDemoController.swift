import Foundation
import CoreGraphics

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
    @Published private(set) var buildingMarkers: [BuildingEvidenceMarker] = []
    /// Live agent timeline derived from stream events — mirrors the web flow rail.
    @Published private(set) var activityEntries: [AgentActivityEntry] = []
    /// True between awaiting_field_validation and a successful submission.
    @Published private(set) var awaitingValidation = false
    @Published private(set) var validationSubmitted = false
    @Published private(set) var caseResolved = false

    private var streamTask: Task<Void, Never>?
    private var pollTask: Task<Void, Never>?
    private var reconnectTask: Task<Void, Never>?
    private var userDisconnected = false
    private var handledEventIDs = Set<String>()

    private static let baseURLDefaultsKey = "ArcBackendBaseURL"
    /// LAN URLs the app previously shipped with — a stored value matching one
    /// of these is stale and must be replaced by the current fallback.
    private static let retiredBaseURLs = ["http://192.168.10.223:8000"]
    #if targetEnvironment(simulator)
    private static let fallbackBaseURLString = "http://127.0.0.1:8000"
    #else
    // The demo Mac's current LAN address — the device must reach the backend
    // over Wi-Fi. Update here (or via UserDefaults) when the network changes.
    private static let fallbackBaseURLString = "http://10.1.244.211:8000"
    #endif

    init() {
        let storedURL = UserDefaults.standard.string(forKey: Self.baseURLDefaultsKey)
        #if targetEnvironment(simulator)
        baseURLString = storedURL ?? Self.fallbackBaseURLString
        #else
        if let storedURL,
           !storedURL.contains("127.0.0.1"),
           !storedURL.contains("localhost"),
           !Self.retiredBaseURLs.contains(storedURL) {
            baseURLString = storedURL
        } else {
            baseURLString = Self.fallbackBaseURLString
            UserDefaults.standard.set(baseURLString, forKey: Self.baseURLDefaultsKey)
        }
        #endif
    }

    deinit {
        streamTask?.cancel()
        pollTask?.cancel()
        reconnectTask?.cancel()
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

    func startScenario(_ scenario: DemoScenario) {
        disconnectStream()
        clearEventState()

        Task {
            do {
                let client = try makeClient()
                statusText = "Resetting demo..."
                _ = try await client.reset()
                clearEventState()
                connectStream()

                let response = try await client.injectFault(InjectFaultRequest(scenario: scenario))
                statusText = "Injected \(response.scenario): \(response.incidentId ?? "no incident"), state: \(response.state)"
                try await refreshEvents(using: client)
            } catch {
                statusText = "Backend error: \(error.localizedDescription)"
            }
        }
    }

    func reset() {
        disconnectStream()
        clearEventState()
        statusText = "Resetting demo..."

        Task {
            do {
                let response = try await makeClient().reset()
                clearEventState()
                statusText = "Reset: \(response.status)"
            } catch {
                statusText = "Backend error: \(error.localizedDescription)"
            }
        }
    }

    func submitValidation(
        for incident: IncidentPushPayload?,
        verdict: ValidationVerdict,
        measuredVoltage: Double? = nil,
        completion: (@MainActor (Bool) -> Void)? = nil
    ) {
        guard let incident else {
            statusText = "No incident loaded."
            completion?(false)
            return
        }

        Task {
            do {
                let client = try makeClient()
                let response = try await client.submitValidation(
                    .demoPayload(for: incident, verdict: verdict, measuredVoltage: measuredVoltage)
                )
                statusText = "Validation accepted: \(response.incidentId), result: \(response.result)"
                validationSubmitted = true
                awaitingValidation = false
                completion?(true)
            } catch {
                statusText = "Backend error: \(error.localizedDescription)"
                completion?(false)
            }
        }
    }

    func connectStream() {
        userDisconnected = false
        do {
            let client = try makeClient()
            startEventPolling()
            guard streamTask == nil else { return }

            isStreamConnected = true
            statusText = "Stream connected: \(baseURLString)"

            streamTask = Task { [weak self] in
                guard let self else { return }

                do {
                    for try await event in client.eventStream() {
                        self.handle(event)
                    }
                    self.markStreamDisconnected(message: "Stream ended.")
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
        userDisconnected = true
        streamTask?.cancel()
        pollTask?.cancel()
        reconnectTask?.cancel()
        streamTask = nil
        pollTask = nil
        reconnectTask = nil
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
        guard handledEventIDs.insert(event.id).inserted else { return }

        recentEvents.insert(event, at: 0)
        recentEvents = Array(recentEvents.prefix(8))
        statusText = "Event: \(event.type)"
        applyBuildingMarker(for: event)
        applyLifecycle(for: event)
        appendActivity(for: event)

        guard event.type == "push_sent",
              let payload = event.data["payload"]?.jsonObject as? [String: Any] else {
            return
        }

        PushNotificationRouter.shared.handle(userInfo: payload)
    }

    /// Tracks the validation window and case lifecycle from the frozen
    /// contract events (contracts/EVENTS.md).
    private func applyLifecycle(for event: BackendEventEnvelope) {
        switch event.type {
        case "fault_detected":
            awaitingValidation = false
            validationSubmitted = false
            caseResolved = false
        case "awaiting_field_validation":
            if !validationSubmitted {
                awaitingValidation = true
            }
        case "validation_received":
            // Also covers replayed history after an app restart: the case was
            // already answered (by anyone), so never reopen the modal for it.
            awaitingValidation = false
            validationSubmitted = true
        case "incident_resolved":
            awaitingValidation = false
            caseResolved = true
        default:
            break
        }
    }

    /// One timeline row per meaningful event — the same beats the web's
    /// Investigation Flow renders, so both screens play the same story.
    private func appendActivity(for event: BackendEventEnvelope) {
        let time = Self.clockTime(from: event.ts)

        let entry: AgentActivityEntry?
        switch event.type {
        case "fault_detected":
            activityEntries.removeAll()
            let failures = event.data["failures"]?.jsonObject as? [[String: Any]]
            let code = string(failures?.first?["code"]) ?? "anomaly"
            entry = AgentActivityEntry(title: "Detected \(code.arcActivityTitle)", time: time, tone: .normal)
        case "agent_started":
            let agent = string(event.data["agent"]?.jsonObject) ?? "sub-agent"
            entry = AgentActivityEntry(title: "Delegated to \(agent.arcActivityTitle)", time: time, tone: .normal)
        case "retrieval_performed":
            let results = event.data["results"]?.jsonObject as? [[String: Any]]
            let doc = string(results?.first?["title"]) ?? string(results?.first?["doc_id"]) ?? "documents"
            entry = AgentActivityEntry(title: "Retrieved \(doc)", time: time, tone: .normal)
        case "diagnostic_ready":
            entry = AgentActivityEntry(title: "Diagnosis ready", time: time, tone: .normal)
        case "push_sent":
            entry = AgentActivityEntry(title: "Asked human for field test", time: time, tone: .warning)
        case "validation_received":
            entry = AgentActivityEntry(title: "Field data received", time: time, tone: .normal)
        case "validation_result":
            let result = string(event.data["result"]?.jsonObject) ?? "processed"
            entry = AgentActivityEntry(
                title: "Validation \(result)",
                time: time,
                tone: result == "pivot" ? .warning : .normal
            )
        case "remediation_ready":
            entry = AgentActivityEntry(title: "Remediation procedure ready", time: time, tone: .normal)
        case "action_report_ready":
            entry = AgentActivityEntry(title: "Action report ready", time: time, tone: .resolved)
        case "incident_resolved":
            entry = AgentActivityEntry(title: "Incident resolved", time: time, tone: .resolved)
        default:
            entry = nil
        }

        guard let entry else { return }
        activityEntries.append(entry)
        activityEntries = Array(activityEntries.suffix(10))
    }

    private static func clockTime(from ts: String) -> String {
        let start = ts.index(ts.startIndex, offsetBy: 11, limitedBy: ts.endIndex)
        guard let start, let end = ts.index(start, offsetBy: 8, limitedBy: ts.endIndex) else { return ts }
        return String(ts[start..<end])
    }

    private func applyBuildingMarker(for event: BackendEventEnvelope) {
        switch event.type {
        case "fault_detected":
            buildingMarkers.removeAll()
            PushNotificationRouter.shared.clearIncident()
            let failures = event.data["failures"]?.jsonObject as? [[String: Any]]
            let first = failures?.first
            appendMarker(
                BuildingEvidenceMarker(
                    id: "S-\(event.seq)",
                    title: string(first?["code"]) ?? "Sensor anomaly",
                    meta: string(first?["equipment"]) ?? event.type,
                    tone: .primary,
                    x: 55,
                    y: 62
                )
            )

        case "retrieval_performed":
            guard let results = event.data["results"]?.jsonObject as? [[String: Any]],
                  let top = results.first else {
                return
            }
            appendMarker(
                BuildingEvidenceMarker(
                    id: "D-\(event.seq)",
                    title: string(top["title"]) ?? string(top["doc_id"]) ?? "Document",
                    meta: "retrieval pass \(string(event.data["pass"]?.jsonObject) ?? "1")",
                    tone: .primarySubtle,
                    x: 42,
                    y: 48
                )
            )

        case "push_sent":
            appendMarker(
                BuildingEvidenceMarker(
                    id: "H-\(event.seq)",
                    title: "Human handoff",
                    meta: "push sent",
                    tone: .warning,
                    x: 55,
                    y: 74
                )
            )

        default:
            return
        }
    }

    private func appendMarker(_ marker: BuildingEvidenceMarker) {
        guard !buildingMarkers.contains(where: { $0.id == marker.id }) else { return }
        buildingMarkers.append(marker)
        buildingMarkers = Array(buildingMarkers.suffix(8))
    }

    private func clearEventState() {
        handledEventIDs.removeAll()
        recentEvents.removeAll()
        buildingMarkers.removeAll()
        activityEntries.removeAll()
        awaitingValidation = false
        validationSubmitted = false
        caseResolved = false
        PushNotificationRouter.shared.clearIncident()
    }

    private func startEventPolling() {
        guard pollTask == nil else { return }

        pollTask = Task { [weak self] in
            guard let self else { return }

            while !Task.isCancelled {
                do {
                    try await self.refreshEvents()
                } catch {
                    if self.streamTask == nil {
                        self.statusText = "Backend poll error: \(error.localizedDescription)"
                    }
                }

                try? await Task.sleep(nanoseconds: 1_000_000_000)
            }
        }
    }

    private func refreshEvents(using existingClient: BackendClient? = nil) async throws {
        let client: BackendClient
        if let existingClient {
            client = existingClient
        } else {
            client = try makeClient()
        }

        let response = try await client.demoEvents()
        for event in response.events {
            handle(event)
        }
    }

    private func string(_ value: Any?) -> String? {
        switch value {
        case let value as String:
            return value
        case let value as CustomStringConvertible:
            return value.description
        default:
            return nil
        }
    }

    private func markStreamDisconnected(message: String) {
        streamTask = nil
        isStreamConnected = false
        if pollTask == nil {
            statusText = message
        }
        scheduleReconnect()
    }

    /// Keeps the stream alive across backend restarts: retry every 3 s until
    /// the user explicitly disconnects. Reconnecting from scratch is safe —
    /// the backend replays full event history and `handledEventIDs` dedupes.
    private func scheduleReconnect() {
        guard !userDisconnected, reconnectTask == nil else { return }

        reconnectTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            guard let self, !Task.isCancelled else { return }
            self.reconnectTask = nil
            if !self.userDisconnected, self.streamTask == nil {
                self.connectStream()
            }
        }
    }
}

struct AgentActivityEntry: Identifiable, Equatable {
    enum Tone: Equatable {
        case normal
        case warning
        case resolved
    }

    let id = UUID()
    let title: String
    let time: String
    let tone: Tone
}

extension String {
    /// "root_cause" → "Root Cause", "PWR-VOLT-DEV" → "Pwr Volt Dev" — display
    /// casing for wire identifiers in the activity feed.
    var arcActivityTitle: String {
        split(whereSeparator: { $0 == "_" || $0 == "-" })
            .map { $0.prefix(1).uppercased() + $0.dropFirst().lowercased() }
            .joined(separator: " ")
    }
}

struct BuildingEvidenceMarker: Identifiable, Equatable {
    let id: String
    let title: String
    let meta: String
    let tone: BuildingEvidenceTone
    let x: CGFloat
    let y: CGFloat
}

enum BuildingEvidenceTone: Equatable {
    case primary
    case primarySubtle
    case warning
    case secondary
}
