import Foundation

// MARK: - Incoming push payload (contracts/push_payload.schema.json)

struct PushSite: Codable, Hashable {
    let id: String
    let name: String
    let lat: Double
    let lon: Double
    let address: String?
}

struct PushFailure: Codable, Hashable, Identifiable {
    let id: String
    let code: String
    let severity: String
    let equipment: String

    /// Human form of the alarm code, e.g. "DC UNDERVOLTAGE".
    var label: String { code.replacingOccurrences(of: "_", with: " ") }
}

/// Optional telemetry reading carried by the push (additive field). When present,
/// Screen A shows the value as the hero; when absent, the alarm code is the hero.
struct PushReading: Codable, Hashable {
    let value: Double
    let unit: String
    let point: String?
    let metric: String?

    /// "-44.8 V" — trims a trailing ".0" ("-48.0" -> "-48").
    var display: String {
        let v = value == value.rounded() ? String(Int(value)) : String(value)
        return "\(v) \(unit)"
    }
}

/// The dispatch ticket the operator sees, parsed from the APNs payload.
struct Diagnostic: Hashable, Identifiable {
    var id: String { incidentID }
    let incidentID: String
    let site: PushSite
    let family: String
    let failures: [PushFailure]
    let title: String
    let body: String
    let receivedAt: Date
    let reading: PushReading?          // optional; nil when the push omits it

    /// Load-bearing failure for the top cause (DC undervoltage in the demo).
    var primaryFailure: PushFailure? {
        failures.first { $0.code.uppercased().contains("UNDERVOLTAGE") } ?? failures.first
    }

    /// Hero reading fallback — the primary alarm code (used when `reading` is nil).
    var heroValue: String {
        (primaryFailure?.label ?? family).uppercased()
    }

    /// Subtitle beneath the value hero: measurement point + alarm code.
    var readingSubtitle: String {
        let loc = reading?.point ?? primaryFailure?.equipment
        return [loc, heroValue].compactMap { $0 }.joined(separator: " · ")
    }

    /// Probable cause, in clear words. No confidence score is ever shown.
    var probableCause: String {
        if failures.contains(where: { $0.code.uppercased().contains("UNDERVOLTAGE") }) {
            return "DC undervoltage on the –48 V plant"
        }
        return primaryFailure?.label.capitalized ?? family.capitalized
    }

    /// Failures other than the load-bearing one, for the "also detected" list.
    var secondaryFailures: [PushFailure] {
        guard let p = primaryFailure else { return failures }
        return failures.filter { $0.id != p.id }
    }
}

extension Diagnostic {
    /// Build from a raw APNs userInfo dictionary. Extra keys (e.g. the simctl
    /// "Simulator Target Bundle") are ignored; nil on a non-conforming payload.
    /// `reading` is decoded best-effort: a missing OR malformed reading never
    /// breaks the card — it simply leaves `reading == nil`.
    init?(userInfo: [AnyHashable: Any]) {
        guard JSONSerialization.isValidJSONObject(userInfo),
              let data = try? JSONSerialization.data(withJSONObject: userInfo),
              let raw = try? JSONDecoder().decode(RawPush.self, from: data)
        else { return nil }
        let reading = (try? JSONDecoder().decode(ReadingEnvelope.self, from: data))?.reading
        self.init(
            incidentID: raw.incident_id,
            site: raw.site,
            family: raw.family,
            failures: raw.failures,
            title: raw.aps.alert.title,
            body: raw.aps.alert.body,
            receivedAt: Date(),
            reading: reading
        )
    }
}

private struct RawPush: Decodable {
    struct APS: Decodable {
        struct Alert: Decodable { let title: String; let body: String }
        let alert: Alert
    }
    let aps: APS
    let incident_id: String
    let site: PushSite
    let family: String
    let failures: [PushFailure]
}

/// Best-effort second pass for the additive, optional `reading` field, decoded
/// separately so a malformed reading can't fail the required-fields decode above.
private struct ReadingEnvelope: Decodable {
    let reading: PushReading?
}

// MARK: - Outgoing validation event (contracts/validation_event.schema.json)
// UNCHANGED wire contract — do not alter shapes (backend enforces 422 otherwise).

struct Technician: Codable, Hashable {
    let id: String
    let name: String
}

struct FailureVerdict: Codable {
    let failure_id: String
    let verdict: String        // "real" | "false"
    let note: String?
}

struct Measurement: Codable {
    let metric: String
    let point: String?
    let value: Double
    let unit: String
}

/// POST /api/validation body — the frozen contract the backend enforces.
struct ValidationEvent: Encodable {
    let incident_id: String
    let client_event_id: String
    let submitted_at: String
    let technician: Technician?
    let validations: [FailureVerdict]
    let measurements: [Measurement]?

    /// Validate: every detected failure verdict "real", no measurement.
    static func confirm(diagnostic: Diagnostic, technician: Technician?) -> ValidationEvent {
        ValidationEvent(
            incident_id: diagnostic.incidentID,
            client_event_id: UUID().uuidString,
            submitted_at: ISO8601DateFormatter().string(from: Date()),
            technician: technician,
            validations: diagnostic.failures.map {
                FailureVerdict(failure_id: $0.id, verdict: "real", note: nil)
            },
            measurements: nil
        )
    }

    /// Refuse: the load-bearing failure verdict "false" + the field counter-measurement.
    /// The measurement (metric dc_voltage_v @ busbar) is the backend's ground truth:
    /// a value below the -47 V threshold contradicts the diagnosis and drives the pivot.
    static func reject(diagnostic: Diagnostic, value: Double, unit: String,
                       technician: Technician?) -> ValidationEvent {
        let uv = diagnostic.primaryFailure
        let validations = diagnostic.failures.map {
            FailureVerdict(failure_id: $0.id,
                           verdict: $0.id == uv?.id ? "false" : "real",
                           note: nil)
        }
        return ValidationEvent(
            incident_id: diagnostic.incidentID,
            client_event_id: UUID().uuidString,
            submitted_at: ISO8601DateFormatter().string(from: Date()),
            technician: technician,
            validations: validations,
            measurements: [Measurement(metric: "dc_voltage_v", point: "busbar",
                                       value: value, unit: unit)]
        )
    }
}
