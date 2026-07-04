import Foundation

protocol ValidationSubmitting {
    func submit(_ submission: ValidationSubmission) async throws -> ValidationResponse
}

struct ValidationResponse: Codable, Equatable {
    let status: String
    let incidentId: String
    let result: String

    enum CodingKeys: String, CodingKey {
        case status
        case incidentId = "incident_id"
        case result
    }
}

struct ValidationClient: ValidationSubmitting {
    let baseURL: URL
    var session: URLSession = .shared

    func submit(_ submission: ValidationSubmission) async throws -> ValidationResponse {
        let endpoint = baseURL.appending(path: "/api/validation")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(submission)

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw ValidationClientError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw ValidationClientError.server(statusCode: httpResponse.statusCode, body: String(data: data, encoding: .utf8))
        }

        return try JSONDecoder().decode(ValidationResponse.self, from: data)
    }
}

enum ValidationClientError: Error, Equatable {
    case invalidResponse
    case server(statusCode: Int, body: String?)
}
