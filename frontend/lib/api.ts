export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

async function post(path: string, body?: unknown): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
}

/** Trigger a demo incident (replays the seeded confirm/pivot signal timeline). */
export function injectFault(scenario: "confirm" | "pivot"): Promise<Response> {
  return post("/api/demo/inject-fault", { scenario });
}

/** Clear the current incident so a new run can start. */
export function resetDemo(): Promise<Response> {
  return post("/api/demo/reset");
}

export interface ValidationBody {
  incident_id: string;
  client_event_id: string;
  submitted_at: string;
  validations: { failure_id: string; verdict: "real" | "false" }[];
  measurements: { metric: string; point: string; value: number; unit: string }[];
}

/** Submit the field technician's per-failure verdict + measurement (human loop). */
export function submitValidation(body: ValidationBody): Promise<Response> {
  return post("/api/validation", body);
}
