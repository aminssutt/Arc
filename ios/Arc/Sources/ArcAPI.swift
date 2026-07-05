import Foundation

struct ValidationResponse: Decodable {
    let status: String?
    let incident_id: String?
    let result: String?         // "confirmed" | "pivot" (from the orchestrator)
}

enum APIError: LocalizedError {
    case badURL
    case http(Int, String)
    case transport(String)

    var errorDescription: String? {
        switch self {
        case .badURL:
            return "Invalid base URL — check the setting."
        case let .http(code, detail):
            let trimmed = detail.trimmingCharacters(in: .whitespacesAndNewlines)
            return "Server \(code)\(trimmed.isEmpty ? "" : ": \(trimmed.prefix(300))")"
        case let .transport(msg):
            return msg
        }
    }
}

/// Thin client for the two backend endpoints the technician app touches.
struct ArcAPI {
    /// POST /api/devices — register the APNs device token (contract frozen by chef).
    func registerDevice(token: String, baseURL: String) async throws {
        let body: [String: Any] = [
            "device_token": token,
            "platform": "ios",
            "operator_id": NSNull(),
        ]
        _ = try await post(path: "/api/devices", baseURL: baseURL, jsonObject: body)
    }

    /// POST /api/validation — the frozen validation event.
    @discardableResult
    func submitValidation(_ event: ValidationEvent, baseURL: String) async throws -> ValidationResponse {
        let data = try JSONEncoder().encode(event)
        let respData = try await post(path: "/api/validation", baseURL: baseURL, rawBody: data)
        return (try? JSONDecoder().decode(ValidationResponse.self, from: respData))
            ?? ValidationResponse(status: "accepted", incident_id: event.incident_id, result: nil)
    }

    @discardableResult
    private func post(path: String, baseURL: String,
                      jsonObject: [String: Any]? = nil, rawBody: Data? = nil) async throws -> Data {
        let base = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: base + path) else { throw APIError.badURL }

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 15
        if let rawBody {
            req.httpBody = rawBody
        } else if let jsonObject {
            req.httpBody = try JSONSerialization.data(withJSONObject: jsonObject)
        }

        do {
            let (data, resp) = try await URLSession.shared.data(for: req)
            guard let http = resp as? HTTPURLResponse else {
                throw APIError.transport("No HTTP response from server.")
            }
            guard (200..<300).contains(http.statusCode) else {
                throw APIError.http(http.statusCode, String(data: data, encoding: .utf8) ?? "")
            }
            return data
        } catch let error as APIError {
            throw error
        } catch {
            throw APIError.transport(error.localizedDescription)
        }
    }
}
