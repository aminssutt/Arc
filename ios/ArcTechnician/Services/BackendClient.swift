import Foundation

struct BackendClient {
    let baseURL: URL
    var session: URLSession = .shared

    func health() async throws -> HealthResponse {
        try await send(path: "/health", method: "GET", body: Optional<EmptyBody>.none)
    }

    func injectFault(_ request: InjectFaultRequest) async throws -> InjectFaultResponse {
        try await send(path: "/api/demo/inject-fault", method: "POST", body: request)
    }

    func reset() async throws -> ResetResponse {
        try await send(path: "/api/demo/reset", method: "POST", body: Optional<EmptyBody>.none)
    }

    func demoEvents() async throws -> DemoEventsResponse {
        try await send(path: "/api/demo/events", method: "GET", body: Optional<EmptyBody>.none)
    }

    func submitValidation(_ submission: ValidationSubmission) async throws -> ValidationResponse {
        try await send(path: "/api/validation", method: "POST", body: submission)
    }

    func eventStream(lastEventID: String? = nil) -> AsyncThrowingStream<BackendEventEnvelope, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    var request = URLRequest(url: baseURL.appending(path: "/api/stream"))
                    request.httpMethod = "GET"
                    request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
                    if let lastEventID {
                        request.setValue(lastEventID, forHTTPHeaderField: "Last-Event-ID")
                    }

                    let (bytes, response) = try await session.bytes(for: request)
                    guard let httpResponse = response as? HTTPURLResponse else {
                        throw BackendClientError.invalidResponse
                    }
                    guard (200..<300).contains(httpResponse.statusCode) else {
                        throw BackendClientError.server(statusCode: httpResponse.statusCode, body: nil)
                    }

                    var dataLines: [String] = []
                    for try await line in bytes.lines {
                        if Task.isCancelled { break }

                        if line.isEmpty {
                            try emitEvent(from: dataLines, continuation: continuation)
                            dataLines.removeAll(keepingCapacity: true)
                        } else if line.hasPrefix("data:") {
                            dataLines.append(String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces))
                        }
                    }

                    try emitEvent(from: dataLines, continuation: continuation)
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }

            continuation.onTermination = { _ in
                task.cancel()
            }
        }
    }

    private func send<RequestBody: Encodable, ResponseBody: Decodable>(
        path: String,
        method: String,
        body: RequestBody?
    ) async throws -> ResponseBody {
        var request = URLRequest(url: baseURL.appending(path: path))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendClientError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw BackendClientError.server(statusCode: httpResponse.statusCode, body: String(data: data, encoding: .utf8))
        }

        return try JSONDecoder().decode(ResponseBody.self, from: data)
    }

    private func emitEvent(
        from dataLines: [String],
        continuation: AsyncThrowingStream<BackendEventEnvelope, Error>.Continuation
    ) throws {
        guard !dataLines.isEmpty else { return }
        let data = Data(dataLines.joined(separator: "\n").utf8)
        let event = try JSONDecoder().decode(BackendEventEnvelope.self, from: data)
        continuation.yield(event)
    }
}

private struct EmptyBody: Encodable {}

enum BackendClientError: Error, Equatable {
    case invalidBaseURL
    case invalidResponse
    case server(statusCode: Int, body: String?)
}
