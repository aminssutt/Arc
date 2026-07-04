import Foundation

struct ValidationSubmission: Codable, Equatable {
    let incidentId: String
    let clientEventId: String
    let submittedAt: String
    let technician: Technician?
    let validations: [FailureValidation]
    let measurements: [FieldMeasurement]?

    enum CodingKeys: String, CodingKey {
        case incidentId = "incident_id"
        case clientEventId = "client_event_id"
        case submittedAt = "submitted_at"
        case technician
        case validations
        case measurements
    }
}

struct Technician: Codable, Equatable {
    let id: String?
    let name: String?
}

struct FailureValidation: Codable, Equatable, Identifiable {
    let failureId: String
    let verdict: ValidationVerdict
    let note: String?

    var id: String { failureId }

    enum CodingKeys: String, CodingKey {
        case failureId = "failure_id"
        case verdict
        case note
    }
}

enum ValidationVerdict: String, Codable, Equatable {
    case real
    case falseAlarm = "false"
}

struct FieldMeasurement: Codable, Equatable, Identifiable {
    let metric: String
    let point: String?
    let value: Double
    let unit: String

    var id: String { "\(metric)-\(point ?? "site")-\(unit)" }
}

extension ValidationSubmission {
    static func demoPayload(for incident: IncidentPushPayload, verdict: ValidationVerdict) -> ValidationSubmission {
        ValidationSubmission(
            incidentId: incident.incidentId,
            clientEventId: "ios-\(UUID().uuidString)",
            submittedAt: ISO8601DateFormatter().string(from: Date()),
            technician: Technician(id: "daniwavy5032", name: "daniwavy5032"),
            validations: incident.failures.map { failure in
                FailureValidation(failureId: failure.id, verdict: verdict, note: nil)
            },
            measurements: [
                FieldMeasurement(metric: "dc_plant_voltage_v", point: "busbar", value: 43.9, unit: "V")
            ]
        )
    }
}
