import type {
  BackendEventEnvelope,
  HealthResponse,
  InjectFaultRequest,
  InjectFaultResponse,
  ResetResponse,
  ValidationResponse,
  ValidationSubmission,
} from "./contracts";

export class BackendClient {
  constructor(private readonly baseURL: string) {}

  health(): Promise<HealthResponse> {
    return this.send<HealthResponse>("/health", { method: "GET" });
  }

  injectFault(request: InjectFaultRequest): Promise<InjectFaultResponse> {
    return this.send<InjectFaultResponse>("/api/demo/inject-fault", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  reset(): Promise<ResetResponse> {
    return this.send<ResetResponse>("/api/demo/reset", { method: "POST" });
  }

  submitValidation(submission: ValidationSubmission): Promise<ValidationResponse> {
    return this.send<ValidationResponse>("/api/validation", {
      method: "POST",
      body: JSON.stringify(submission),
    });
  }

  streamEvents(
    onEvent: (event: BackendEventEnvelope) => void,
    signal: AbortSignal,
  ): Promise<void> {
    return streamSSE(`${this.baseURL}/api/stream`, onEvent, signal);
  }

  private async send<ResponseBody>(
    path: string,
    init: RequestInit,
  ): Promise<ResponseBody> {
    const response = await fetch(`${this.baseURL}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Backend ${response.status}: ${body}`);
    }

    return response.json() as Promise<ResponseBody>;
  }
}

async function streamSSE(
  url: string,
  onEvent: (event: BackendEventEnvelope) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch(url, {
    headers: { Accept: "text/event-stream" },
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`SSE failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (!signal.aborted) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let delimiterIndex = buffer.indexOf("\n\n");
    while (delimiterIndex >= 0) {
      const chunk = buffer.slice(0, delimiterIndex);
      buffer = buffer.slice(delimiterIndex + 2);
      emitSSEChunk(chunk, onEvent);
      delimiterIndex = buffer.indexOf("\n\n");
    }
  }
}

function emitSSEChunk(
  chunk: string,
  onEvent: (event: BackendEventEnvelope) => void,
): void {
  const data = chunk
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim())
    .join("\n");

  if (!data) return;
  onEvent(JSON.parse(data) as BackendEventEnvelope);
}
