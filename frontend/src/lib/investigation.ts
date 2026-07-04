import type { BackendEventEnvelope, DemoScenario } from "./contracts";
import { extractPushPayload } from "./contracts";

// Investigation state machine backing the control-room screen
// (Figma "01 Arc Investigation Concept", nodes 133:276 / 133:589).
// Drives both the local scenario replay and the live SSE stream.
//
// Graph nodes mirror the real backend architecture (contracts/EVENTS.md,
// backend/app/orchestrator.py): a deterministic orchestrator sequences
// phase-1 agents (correlation, root_cause), the human validation loop, and
// phase-2 agents (remediation, cost_inventory_dispatch). HVAC/Fire/Security
// are domain watchers on the signal side — visible but dormant in the demo.

export type AgentId =
  | "main"
  | "correlation"
  | "rootCause"
  | "hvac"
  | "fire"
  | "security"
  | "validation"
  | "remediation"
  | "dispatch";

export type AgentStatus = "monitoring" | "standby" | "active" | "done";

export type CaseStatus = "monitoring" | "investigating" | "awaiting-validation" | "resolved";

export type EvidenceTone = "primary" | "primarySubtle" | "warning" | "secondary";

export type EvidenceItem = {
  id: string;
  title: string;
  meta: string;
  tone: EvidenceTone;
  /** Marker position on the floor plan, in % of the viewport. */
  marker?: { x: number; y: number };
};

export type FlowTone = "primary" | "warning" | "neutral" | "secondary";

export type FlowStep = {
  id: string;
  index: string;
  title: string;
  body: string;
  timestamp: string;
  source: string;
  tone: FlowTone;
};

export type AgentInfo = {
  id: AgentId;
  name: string;
  role: string;
};

export const AGENTS: Record<AgentId, AgentInfo> = {
  main: {
    id: "main",
    name: "Main Agent",
    role: "Incident commander. Sequences every sub-agent and never diagnoses on its own.",
  },
  correlation: {
    id: "correlation",
    name: "Correlation",
    role: "Phase 1 — walks the site topology to scope equipment and blast radius.",
  },
  rootCause: {
    id: "rootCause",
    name: "Root Cause",
    role: "Phase 1 — confidence-gated retrieval over schematics and history to rank causes.",
  },
  hvac: { id: "hvac", name: "HVAC", role: "Domain watcher — cooling and environment signals." },
  fire: { id: "fire", name: "Fire", role: "Domain watcher — fire detection and suppression signals." },
  security: { id: "security", name: "Security", role: "Domain watcher — access control and intrusion signals." },
  validation: {
    id: "validation",
    name: "Validation",
    role: "Human loop — turns the technician's field verdict into confirmed or pivot.",
  },
  remediation: {
    id: "remediation",
    name: "Remediation",
    role: "Phase 2 — cited repair procedure with safety notes.",
  },
  dispatch: {
    id: "dispatch",
    name: "Dispatch",
    role: "Phase 2 — cost, inventory, and crew booking for the action report.",
  },
};

export type InvestigationState = {
  caseStatus: CaseStatus;
  caseId: string;
  startedAt: string;
  agents: Record<AgentId, AgentStatus>;
  decisionLabel: string;
  decisionCopy: string;
  evidence: EvidenceItem[];
  flow: FlowStep[];
};

const IDLE_AGENTS: Record<AgentId, AgentStatus> = {
  main: "monitoring",
  correlation: "standby",
  rootCause: "standby",
  hvac: "standby",
  fire: "standby",
  security: "standby",
  validation: "standby",
  remediation: "standby",
  dispatch: "standby",
};

export const initialInvestigationState: InvestigationState = {
  caseStatus: "monitoring",
  caseId: "—",
  startedAt: "—",
  agents: IDLE_AGENTS,
  decisionLabel: "MAIN AGENT",
  decisionCopy: "All feeds nominal. Sub-agents stay dormant until the main agent calls them.",
  evidence: [],
  flow: [],
};

export type InvestigationAction =
  | { type: "apply"; patch: Partial<InvestigationState>; evidence?: EvidenceItem[]; flow?: FlowStep[] }
  | { type: "reset" };

export function investigationReducer(
  state: InvestigationState,
  action: InvestigationAction,
): InvestigationState {
  switch (action.type) {
    case "reset":
      return initialInvestigationState;
    case "apply": {
      const next = { ...state, ...action.patch };
      if (action.patch.agents) {
        next.agents = { ...state.agents, ...action.patch.agents };
      }
      if (action.evidence) {
        const known = new Set(state.evidence.map((item) => item.id));
        next.evidence = [...state.evidence, ...action.evidence.filter((item) => !known.has(item.id))];
      }
      if (action.flow) {
        const known = new Set(state.flow.map((step) => step.id));
        next.flow = [...state.flow, ...action.flow.filter((step) => !known.has(step.id))];
      }
      return next;
    }
  }
}

type AgentPatch = Partial<Record<AgentId, AgentStatus>>;

function agents(patch: AgentPatch): InvestigationState["agents"] {
  return patch as InvestigationState["agents"];
}

export type ScenarioBeat = {
  delayMs: number;
  action: InvestigationAction;
};

// Mirrors the real orchestrator sequence: fault_detected → phase 1
// (correlation, root_cause) → push / awaiting_field_validation → validation
// verdict → phase 2 (remediation, dispatch) → incident_resolved.
export function scenarioBeats(scenario: DemoScenario): ScenarioBeat[] {
  const detect: ScenarioBeat = {
    delayMs: 400,
    action: {
      type: "apply",
      patch: {
        caseStatus: "investigating",
        caseId: "INC-2026-0704-0314",
        startedAt: "03:14:02",
        decisionLabel: "MAIN AGENT",
        decisionCopy: "Watchdog triggered on Power Feed 1 voltage. Starting phase 1 diagnosis.",
      },
      evidence: [
        {
          id: "S1",
          title: "Sensor anomaly",
          meta: "confidence 84%",
          tone: "primary",
          marker: { x: 55, y: 62 },
        },
      ],
      flow: [
        {
          id: "detect",
          index: "01",
          title: "Detect",
          body: "Main Agent identifies abnormal voltage pattern from live sensor feed.",
          timestamp: "03:14:02",
          source: "Sensor Feed",
          tone: "primary",
        },
      ],
    },
  };

  const delegate: ScenarioBeat = {
    delayMs: 2000,
    action: {
      type: "apply",
      patch: {
        agents: agents({ correlation: "active" }),
        decisionLabel: "MAIN AGENT DECISION",
        decisionCopy:
          "Correlation agent activated to scope the blast radius. Domain watchers stay dormant until evidence requires them.",
      },
      flow: [
        {
          id: "delegate",
          index: "02",
          title: "Delegate",
          body: "Correlation agent is called because the anomaly maps to Power Feed 1.",
          timestamp: "03:15:07",
          source: "Agent Activation",
          tone: "warning",
        },
      ],
    },
  };

  const retrieve: ScenarioBeat = {
    delayMs: 2000,
    action: {
      type: "apply",
      patch: {
        agents: agents({ correlation: "done", rootCause: "active" }),
        decisionLabel: "PHASE 1",
        decisionCopy: "Root-Cause agent ranking causes against schematics and incident history.",
      },
      evidence: [
        {
          id: "D1",
          title: "Schematic match",
          meta: "Floor-Plan-B5.pdf",
          tone: "primarySubtle",
          marker: { x: 42, y: 48 },
        },
      ],
      flow: [
        {
          id: "retrieve",
          index: "03",
          title: "Retrieve",
          body: "Relevant schematics, SOP, and incident history are pulled into context.",
          timestamp: "03:16:24",
          source: "Knowledge Retrieval",
          tone: "neutral",
        },
      ],
    },
  };

  const handoff: ScenarioBeat = {
    delayMs: 2000,
    action: {
      type: "apply",
      patch: {
        caseStatus: "awaiting-validation",
        agents: agents({ rootCause: "done", validation: "active" }),
        decisionLabel: "HUMAN HANDOFF",
        decisionCopy:
          "Diagnosis ready with 84% confidence. Field technician receives a test request with the exact terminal location.",
      },
      evidence: [
        {
          id: "H1",
          title: "Human handoff",
          meta: "push sent",
          tone: "warning",
          marker: { x: 55, y: 74 },
        },
      ],
      flow: [
        {
          id: "handoff",
          index: "04",
          title: "Handoff",
          body: "Facility manager receives a field test request with exact terminal location.",
          timestamp: "03:21:11",
          source: "Push Notification",
          tone: "secondary",
        },
      ],
    },
  };

  if (scenario === "confirm") {
    return [
      detect,
      delegate,
      retrieve,
      handoff,
      {
        delayMs: 2600,
        action: {
          type: "apply",
          patch: {
            agents: agents({ validation: "done", remediation: "active", dispatch: "active" }),
            decisionLabel: "VALIDATION: CONFIRMED",
            decisionCopy:
              "Field measurement confirmed the Power Feed 1 fault. Phase 2 building the action report.",
          },
          flow: [
            {
              id: "validate",
              index: "05",
              title: "Validate",
              body: "Technician confirmed the fault on-site. Remediation and dispatch agents engaged.",
              timestamp: "03:24:05",
              source: "Field Validation",
              tone: "warning",
            },
          ],
        },
      },
      {
        delayMs: 2200,
        action: {
          type: "apply",
          patch: {
            caseStatus: "resolved",
            agents: agents({ remediation: "done", dispatch: "done" }),
            decisionLabel: "CASE RESOLVED",
            decisionCopy:
              "Cited repair procedure, parts, and crew booking archived. Action report generated.",
          },
          flow: [
            {
              id: "resolve",
              index: "06",
              title: "Resolve",
              body: "Action report ready: procedure, cost, inventory, and dispatch in one document.",
              timestamp: "03:26:40",
              source: "Action Report",
              tone: "secondary",
            },
          ],
        },
      },
    ];
  }

  return [
    detect,
    delegate,
    retrieve,
    handoff,
    {
      delayMs: 2600,
      action: {
        type: "apply",
        patch: {
          agents: agents({ validation: "done", correlation: "active", rootCause: "active" }),
          decisionLabel: "VALIDATION: PIVOT",
          decisionCopy:
            "Field measurement contradicts the hypothesis — voltage nominal at the terminal. Phase 1 re-running with the contradiction in context.",
        },
        evidence: [
          {
            id: "D2",
            title: "Hypothesis pivot",
            meta: "voltage nominal",
            tone: "warning",
            marker: { x: 30, y: 55 },
          },
        ],
        flow: [
          {
            id: "pivot",
            index: "05",
            title: "Pivot",
            body: "Field evidence contradicts the diagnosis. Phase 1 re-runs with revised context.",
            timestamp: "03:24:40",
            source: "Agent Pivot",
            tone: "warning",
          },
        ],
      },
    },
    {
      delayMs: 2200,
      action: {
        type: "apply",
        patch: {
          agents: agents({
            correlation: "done",
            rootCause: "done",
            remediation: "active",
            dispatch: "active",
          }),
          decisionLabel: "PHASE 2",
          decisionCopy: "Revised diagnosis accepted. Remediation and dispatch agents building the report.",
        },
        flow: [
          {
            id: "phase2",
            index: "06",
            title: "Remediate",
            body: "Revised procedure prepared with parts and crew for the cooling-loop fault.",
            timestamp: "03:25:58",
            source: "Remediation",
            tone: "neutral",
          },
        ],
      },
    },
    {
      delayMs: 2000,
      action: {
        type: "apply",
        patch: {
          caseStatus: "resolved",
          agents: agents({ remediation: "done", dispatch: "done" }),
          decisionLabel: "CASE RESOLVED",
          decisionCopy: "Pivoted diagnosis validated and archived. Action report generated.",
        },
        flow: [
          {
            id: "resolve",
            index: "07",
            title: "Resolve",
            body: "Action report ready after pivot: revised diagnosis, procedure, and dispatch.",
            timestamp: "03:27:31",
            source: "Action Report",
            tone: "secondary",
          },
        ],
      },
    },
  ];
}

// ---------------------------------------------------------------------------
// Live stream mapping — exact wire names from the frozen contract
// (contracts/EVENTS.md): fault_detected, phase_started, agent_started,
// agent_completed, retrieval_performed, diagnostic_ready, push_sent,
// awaiting_field_validation, validation_received, validation_result,
// remediation_ready, action_report_ready, doc_requested, incident_resolved.
// ---------------------------------------------------------------------------

const WIRE_AGENT_TO_NODE: Record<string, AgentId> = {
  correlation: "correlation",
  root_cause: "rootCause",
  validation: "validation",
  remediation: "remediation",
  cost_inventory_dispatch: "dispatch",
};

function str(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function actionForBackendEvent(event: BackendEventEnvelope): InvestigationAction | null {
  const timestamp = event.ts.slice(11, 19) || event.ts;
  const flowBase = { timestamp, source: "Live Stream" } as const;

  switch (event.type) {
    case "fault_detected": {
      const failures = Array.isArray(event.data.failures) ? (event.data.failures as Array<Record<string, unknown>>) : [];
      const first = failures[0];
      return {
        type: "apply",
        patch: {
          caseStatus: "investigating",
          caseId: event.incident_id,
          startedAt: timestamp,
          decisionLabel: "FAULT DETECTED",
          decisionCopy: first
            ? `${str(first.code) || "Fault"} on ${str(first.equipment) || "equipment"} (${str(first.severity) || "unknown"}).`
            : "Watchdog trigger fired. Phase 1 starting.",
        },
        evidence: [
          {
            id: `S-${event.seq}`,
            title: first ? str(first.code) || "Sensor anomaly" : "Sensor anomaly",
            meta: first ? str(first.equipment) || event.type : event.type,
            tone: "primary",
            marker: { x: 55, y: 62 },
          },
        ],
        flow: [
          {
            id: event.id,
            index: "01",
            title: "Detect",
            body: `Incident ${event.incident_id} opened from live signals.`,
            tone: "primary",
            ...flowBase,
          },
        ],
      };
    }

    case "phase_started": {
      const pivot = event.data.cause === "pivot";
      if (!pivot) return null;
      return {
        type: "apply",
        patch: {
          caseStatus: "investigating",
          decisionLabel: "PIVOT",
          decisionCopy: "Field evidence contradicted the diagnosis. Phase 1 re-running with revised context.",
        },
        flow: [
          {
            id: event.id,
            index: "•",
            title: "Pivot",
            body: "Phase 1 re-entered with the contradiction in context.",
            tone: "warning",
            ...flowBase,
          },
        ],
      };
    }

    case "agent_started": {
      const node = WIRE_AGENT_TO_NODE[str(event.data.agent)];
      if (!node) return null;
      return {
        type: "apply",
        patch: {
          agents: agents({ [node]: "active" }),
          decisionLabel: AGENTS[node].name.toUpperCase(),
          decisionCopy: AGENTS[node].role,
        },
      };
    }

    case "agent_completed": {
      const node = WIRE_AGENT_TO_NODE[str(event.data.agent)];
      if (!node) return null;
      const status = str(event.data.status);
      return {
        type: "apply",
        patch: {
          agents: agents({ [node]: "done" }),
          ...(status !== "ok"
            ? {
                decisionLabel: "DEGRADED",
                decisionCopy: `${AGENTS[node].name} finished with ${status}. Run continues on fallbacks.`,
              }
            : {}),
        },
      };
    }

    case "retrieval_performed": {
      const results = Array.isArray(event.data.results) ? (event.data.results as Array<Record<string, unknown>>) : [];
      const top = results[0];
      if (!top) return null;
      return {
        type: "apply",
        patch: {},
        evidence: [
          {
            id: `D-${event.seq}`,
            title: str(top.title) || str(top.doc_id) || "Document",
            meta: `retrieval pass ${String(event.data.pass ?? "1")}`,
            tone: "primarySubtle",
            marker: { x: 42, y: 48 },
          },
        ],
      };
    }

    case "diagnostic_ready": {
      const causes = Array.isArray(event.data.causes) ? (event.data.causes as Array<Record<string, unknown>>) : [];
      const top = causes[0];
      return {
        type: "apply",
        patch: {
          decisionLabel: "DIAGNOSIS READY",
          decisionCopy: top
            ? `Top cause: ${str(top.cause)} (confidence ${Math.round(Number(top.confidence ?? 0) * 100)}%).`
            : "Phase 1 diagnosis complete.",
        },
        flow: [
          {
            id: event.id,
            index: "•",
            title: "Diagnose",
            body: top ? `Ranked causes ready — top: ${str(top.cause)}.` : "Ranked causes ready.",
            tone: "neutral",
            ...flowBase,
          },
        ],
      };
    }

    case "push_sent": {
      const payload = extractPushPayload(event);
      return {
        type: "apply",
        patch: {
          caseId: payload?.incident_id ?? event.incident_id,
          decisionLabel: "HUMAN HANDOFF",
          decisionCopy: payload
            ? `Push sent to field technician for ${payload.site.name} (${payload.failures.length} failure${payload.failures.length === 1 ? "" : "s"}).`
            : "Push sent to field technician.",
        },
        evidence: [
          { id: `H-${event.seq}`, title: "Human handoff", meta: "push sent", tone: "warning", marker: { x: 55, y: 74 } },
        ],
        flow: [
          {
            id: event.id,
            index: "•",
            title: "Handoff",
            body: "Field technician received a validation request on the iOS app.",
            tone: "secondary",
            ...flowBase,
          },
        ],
      };
    }

    case "awaiting_field_validation":
      return {
        type: "apply",
        patch: {
          caseStatus: "awaiting-validation",
          agents: agents({ validation: "active" }),
          decisionLabel: "AWAITING FIELD VALIDATION",
          decisionCopy: "Waiting for the technician's measurements and verdict.",
        },
      };

    case "validation_received":
      return {
        type: "apply",
        patch: {
          decisionLabel: "VALIDATION RECEIVED",
          decisionCopy: "Technician response received. Validation agent scoring the verdict.",
        },
      };

    case "validation_result": {
      const pivot = event.data.result === "pivot";
      return {
        type: "apply",
        patch: {
          caseStatus: "investigating",
          decisionLabel: pivot ? "VALIDATION: PIVOT" : "VALIDATION: CONFIRMED",
          decisionCopy: str(event.data.rationale) || (pivot ? "Diagnosis contradicted in the field." : "Diagnosis confirmed in the field."),
        },
        flow: [
          {
            id: event.id,
            index: "•",
            title: pivot ? "Pivot" : "Validate",
            body: str(event.data.rationale) || "Field verdict processed.",
            tone: pivot ? "warning" : "secondary",
            ...flowBase,
          },
        ],
      };
    }

    case "remediation_ready":
      return {
        type: "apply",
        patch: {
          decisionLabel: "REMEDIATION READY",
          decisionCopy: "Cited repair procedure and parts list prepared.",
        },
      };

    case "action_report_ready":
      return {
        type: "apply",
        patch: {
          decisionLabel: "ACTION REPORT READY",
          decisionCopy: "Diagnosis, actions, cost, inventory, and dispatch compiled.",
        },
        flow: [
          {
            id: event.id,
            index: "•",
            title: "Report",
            body: "Action report compiled with citations and honesty notes.",
            tone: "secondary",
            ...flowBase,
          },
        ],
      };

    case "doc_requested":
      return {
        type: "apply",
        patch: {},
        evidence: [
          {
            id: `G-${event.seq}`,
            title: "Missing document",
            meta: str(event.data.description) || str(event.data.query) || "doc requested",
            tone: "warning",
          },
        ],
      };

    case "incident_resolved": {
      const downgraded = event.data.outcome === "downgraded";
      return {
        type: "apply",
        patch: {
          caseStatus: "resolved",
          agents: IDLE_AGENTS,
          decisionLabel: downgraded ? "RESOLVED (DEGRADED)" : "CASE RESOLVED",
          decisionCopy: str(event.data.summary) || "Incident closed. Action report archived.",
        },
        flow: [
          {
            id: event.id,
            index: "•",
            title: "Resolve",
            body: str(event.data.summary) || "Incident closed.",
            tone: "secondary",
            ...flowBase,
          },
        ],
      };
    }

    default:
      return null;
  }
}
