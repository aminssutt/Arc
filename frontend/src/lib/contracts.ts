export type HealthResponse = {
  status: string;
  state: string;
  seeds: Record<string, string>;
};

export type DemoScenario = "confirm" | "pivot";

export type InjectFaultRequest = {
  scenario?: DemoScenario;
  alarm_code?: string;
  site_id?: string;
  equipment_id?: string;
};

export type InjectFaultResponse = {
  status: string;
  scenario: string;
  incident_id: string | null;
  state: string;
};

export type ResetResponse = {
  status: string;
};

export type FailureFamily = "energy" | "environment" | "rf" | "transport";

export type FailureSeverity =
  | "critical"
  | "major"
  | "minor"
  | "warning"
  | "indeterminate"
  | "cleared";

export type IncidentPushPayload = {
  incident_id: string;
  site: {
    id: string;
    name: string;
    lat: number;
    lon: number;
    address?: string;
  };
  family: FailureFamily;
  failures: Array<{
    id: string;
    code: string;
    severity: FailureSeverity;
    equipment: string;
  }>;
};

export type ValidationVerdict = "real" | "false";

export type ValidationSubmission = {
  incident_id: string;
  client_event_id: string;
  submitted_at: string;
  technician?: {
    id?: string;
    name?: string;
  };
  validations: Array<{
    failure_id: string;
    verdict: ValidationVerdict;
    note?: string;
  }>;
  measurements?: Array<{
    metric: string;
    point?: string;
    value: number;
    unit: string;
  }>;
};

export type ValidationResponse = {
  status: string;
  incident_id: string;
  result: string;
};

export type BackendEventEnvelope = {
  seq: number;
  id: string;
  ts: string;
  incident_id: string;
  type: string;
  data: Record<string, unknown>;
};

/** A field counter-measurement typed on the on-site phone. */
export type FieldMeasurement = { value: number; unit: string };

export function makeDemoValidation(
  incident: IncidentPushPayload,
  verdict: ValidationVerdict,
  measurement?: FieldMeasurement,
): ValidationSubmission {
  return {
    incident_id: incident.incident_id,
    client_event_id: `web-${crypto.randomUUID()}`,
    submitted_at: new Date().toISOString(),
    technician: {
      id: "daniwavy5032",
      name: "daniwavy5032",
    },
    validations: incident.failures.map((failure) => ({
      failure_id: failure.id,
      verdict,
    })),
    // The on-site phone can carry the exact value the technician measured — it
    // becomes the backend's ground truth (a value contradicting the diagnosis
    // drives the pivot). Absent an explicit reading, keep the demo default so
    // the existing one-tap "confirm" path is unchanged.
    measurements: [
      {
        metric: "dc_plant_voltage_v",
        point: "busbar",
        value: measurement?.value ?? 43.9,
        unit: measurement?.unit ?? "V",
      },
    ],
  };
}

export function extractPushPayload(event: BackendEventEnvelope): IncidentPushPayload | null {
  if (event.type !== "push_sent") return null;

  const payload = event.data.payload;
  if (!isRecord(payload)) return null;

  return {
    incident_id: String(payload.incident_id),
    site: payload.site as IncidentPushPayload["site"],
    family: payload.family as FailureFamily,
    failures: payload.failures as IncidentPushPayload["failures"],
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
