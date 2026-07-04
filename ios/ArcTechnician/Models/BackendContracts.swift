import Foundation

struct HealthResponse: Codable, Equatable {
    let status: String
    let state: String
    let seeds: [String: String]
}

enum DemoScenario: String, Codable, CaseIterable, Identifiable {
    case confirm
    case pivot

    var id: String { rawValue }
}

struct InjectFaultRequest: Codable, Equatable {
    let scenario: DemoScenario?
    let alarmCode: String?
    let siteId: String?
    let equipmentId: String?

    init(
        scenario: DemoScenario? = nil,
        alarmCode: String? = nil,
        siteId: String? = nil,
        equipmentId: String? = nil
    ) {
        self.scenario = scenario
        self.alarmCode = alarmCode
        self.siteId = siteId
        self.equipmentId = equipmentId
    }

    enum CodingKeys: String, CodingKey {
        case scenario
        case alarmCode = "alarm_code"
        case siteId = "site_id"
        case equipmentId = "equipment_id"
    }
}

struct InjectFaultResponse: Codable, Equatable {
    let status: String
    let scenario: String
    let incidentId: String?
    let state: String

    enum CodingKeys: String, CodingKey {
        case status
        case scenario
        case incidentId = "incident_id"
        case state
    }
}

struct ResetResponse: Codable, Equatable {
    let status: String
}

struct BackendEventEnvelope: Codable, Equatable, Identifiable {
    let seq: Int
    let id: String
    let ts: String
    let incidentId: String
    let type: String
    let data: [String: JSONValue]

    enum CodingKeys: String, CodingKey {
        case seq
        case id
        case ts
        case incidentId = "incident_id"
        case type
        case data
    }
}

enum JSONValue: Codable, Equatable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([String: JSONValue].self) {
            self = .object(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Unsupported JSON value")
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()

        switch self {
        case .string(let value):
            try container.encode(value)
        case .number(let value):
            try container.encode(value)
        case .bool(let value):
            try container.encode(value)
        case .object(let value):
            try container.encode(value)
        case .array(let value):
            try container.encode(value)
        case .null:
            try container.encodeNil()
        }
    }

    var jsonObject: Any {
        switch self {
        case .string(let value):
            return value
        case .number(let value):
            return value
        case .bool(let value):
            return value
        case .object(let value):
            return value.mapValues { $0.jsonObject }
        case .array(let value):
            return value.map { $0.jsonObject }
        case .null:
            return NSNull()
        }
    }
}
