import Foundation

struct IncidentPushPayload: Codable, Equatable, Identifiable {
    let incidentId: String
    let site: Site
    let family: FailureFamily
    let failures: [DetectedFailure]

    var id: String { incidentId }

    enum CodingKeys: String, CodingKey {
        case incidentId = "incident_id"
        case site
        case family
        case failures
    }
}

enum FailureFamily: String, Codable, Equatable {
    case energy
    case environment
    case rf
    case transport
}

struct Site: Codable, Equatable {
    let id: String
    let name: String
    let lat: Double
    let lon: Double
    let address: String?
}

struct DetectedFailure: Codable, Equatable, Identifiable {
    let id: String
    let code: String
    let severity: FailureSeverity
    let equipment: String
}

enum FailureSeverity: String, Codable, Equatable {
    case critical
    case major
    case minor
    case warning
    case indeterminate
    case cleared
}
