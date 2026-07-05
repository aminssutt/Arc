import type { BackendEventEnvelope, DemoScenario } from "./contracts";
import { extractPushPayload } from "./contracts";

// Investigation state machine backing the control-room screen (/monitor).
// Drives both the local scenario replay and the live SSE stream.
//
// Graph nodes mirror the REAL backend architecture (contracts/EVENTS.md,
// backend/app/orchestrator.py, agents/responder_matching): the Watchdog opens
// the incident, the LangGraph Orchestrator routes a typed state through the
// phase-1 agents (correlation, root_cause), the Responder-Matching agent picks
// THE ONE technician to notify, the human validation loop resolves the field
// verdict, and the phase-2 agents (remediation, cost_inventory_dispatch)
// assemble the action report. No fictional domain sentinels — every node maps
// onto an agent the backend actually runs.

export type AgentId =
  | "main" // Watchdog — detects site faults, opens the incident
  | "orchestrator" // LangGraph — routes the typed incident state
  | "correlation" // Phase 1 — topology + alarms
  | "rootCause" // Phase 1 — grounded, cited diagnosis
  | "matching" // Responder-Matching — picks THE ONE technician
  | "validation" // Human field loop
  | "remediation" // Phase 2 — cited fix procedure
  | "dispatch"; // Phase 2 — cost + inventory + dispatch (cost_inventory_dispatch)

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

// ---------------------------------------------------------------------------
// Live activity / reasoning stream — a compact, append-only log of what each
// agent is doing, driven by the same SSE events the graph consumes. This is
// additive: it never replaces `flow` (which still backs the action report), it
// just gives the operator a legible, animated "watching the agents work" feed.
// ---------------------------------------------------------------------------
export type ActivityKind =
  | "detect"
  | "route"
  | "agent"
  | "retrieval"
  | "diagnosis"
  | "match"
  | "handoff"
  | "validation"
  | "pivot"
  | "remediation"
  | "report"
  | "resolve"
  | "degraded";

export type ActivityEntry = {
  id: string;
  kind: ActivityKind;
  agent?: AgentId;
  label: string;
  detail: string;
  timestamp: string;
  tone: FlowTone;
  /**
   * Optional rich reasoning breakdown — the structured, multi-line content a
   * single SSE event actually carries (ranked causes, retrieval hits, procedure
   * steps, validation contradictions). `detail` stays the one-line summary the
   * compact ActivityStream renders; `lines` drives the agent TERMINAL's live
   * reasoning feed. Additive: consumers that ignore it are unaffected.
   */
  lines?: string[];
};

// ---------------------------------------------------------------------------
// Responder-Matching pick — the ONE technician the matching agent notified.
// Rides `awaiting_field_validation.data.responders[0]` in live mode; the local
// demo synthesizes the equivalent. Scores tech on competence × difficulty-fit ×
// zone; the "routed to ONE — not broadcast" moment is surfaced from this.
// ---------------------------------------------------------------------------
export type ChosenResponder = {
  employeeId: string;
  name: string;
  role?: string;
  tier: string; // senior / junior
  region?: string;
  outOfZone: boolean;
  difficulty?: string; // simple / complex
  matchedSkills?: string[];
  reason?: string;
  score?: number;
};

// ---------------------------------------------------------------------------
// Responder-Matching narrowing snapshot — the LIVE candidate slate the matching
// agent scored, carried by the additive `responder_matched` SSE event
// (backend orchestrator `_emit_responder_matched`). `candidates[0]` IS the
// chosen; the rest are alternatives the reveal "switches off" one by one until
// only THE ONE stays lit. Every field is coerced defensively so a degraded
// payload never crashes the stream.
// ---------------------------------------------------------------------------
export type MatchingCard = {
  employeeId: string;
  name: string;
  tier: string; // senior / junior
  region: string; // e.g. "IDF-North"
  matchedSkills: string[]; // e.g. ["power","rectifier"]
  score: number; // 0..1
  reason?: string;
  outOfZone?: boolean;
};

export type MatchingFault = {
  family: string;
  equipmentClass: string;
  code: string;
  region: string;
};

export type MatchingSnapshot = {
  fault: MatchingFault;
  difficulty: string; // "simple" | "complex"
  chosen: MatchingCard;
  candidates: MatchingCard[]; // candidates[0] is the chosen; rest are alternatives
};

// ---------------------------------------------------------------------------
// Action-report payload — the shape carried by the `action_report_ready` SSE
// event (`event.data.report`, backend orchestrator `_assemble_report`). Each
// citation is enriched by the backend `enrich_citations()` into an OPENABLE
// source (title / url / open_url / page / openable) while keeping doc_id +
// claim. We keep every field optional so a degraded report still parses.
// ---------------------------------------------------------------------------
export type ReportCitation = {
  doc_id: string;
  claim?: string;
  title?: string;
  publisher?: string | null;
  family?: string | null;
  rights?: string | null;
  url?: string | null;
  open_url?: string | null;
  local_path?: string | null;
  section?: string;
  snippet?: string | null;
  page?: number;
  openable?: boolean;
  unresolved?: boolean;
};

export type EventReport = {
  diagnosis: { cause: string; confidence: number; citations?: ReportCitation[] };
  actions: Array<{ priority: string; action: string; owner?: string }>;
  cost?: { currency: string; intervention: number; avoided: number; notes?: string };
  inventory?: { part_no: string; qty_available: number; location: string; in_stock: boolean };
  dispatch?: { crew: string; conflict?: string; booking_id: string };
  honesty_notes?: string[];
  citations?: ReportCitation[];
};

export const AGENTS: Record<AgentId, AgentInfo> = {
  main: {
    id: "main",
    name: "Watchdog",
    role: "Detects site faults from live telemetry and opens the incident. Never diagnoses on its own.",
  },
  orchestrator: {
    id: "orchestrator",
    name: "Orchestrator",
    role: "LangGraph state machine — routes the typed incident state through every specialist in order.",
  },
  correlation: {
    id: "correlation",
    name: "Correlation",
    role: "Phase 1 — walks site topology and the alarm graph to scope the outage blast radius.",
  },
  rootCause: {
    id: "rootCause",
    name: "Root-Cause",
    role: "Phase 1 — grounded, cited diagnosis ranked against telecom standards and incident history.",
  },
  matching: {
    id: "matching",
    name: "Matching",
    role: "Scores technicians on competence × difficulty-fit × zone and notifies THE ONE in-zone senior — not a broadcast.",
  },
  validation: {
    id: "validation",
    name: "Validation",
    role: "Human loop — turns the field technician's on-site verdict into confirmed or pivot.",
  },
  remediation: {
    id: "remediation",
    name: "Remediation",
    role: "Phase 2 — cited repair procedure with safety notes.",
  },
  dispatch: {
    id: "dispatch",
    name: "Cost / Inventory / Dispatch",
    role: "Phase 2 — cost, inventory match, and crew booking, compiled into the action report.",
  },
};

// Pipeline order the Orchestrator sequences the specialists in — used by the
// graph to lay out the handoff rail and to animate the beam travelling from a
// finishing agent to the next.
export const AGENT_PIPELINE: AgentId[] = [
  "correlation",
  "rootCause",
  "matching",
  "validation",
  "remediation",
  "dispatch",
];

export type InvestigationState = {
  caseStatus: CaseStatus;
  caseId: string;
  startedAt: string;
  agents: Record<AgentId, AgentStatus>;
  decisionLabel: string;
  decisionCopy: string;
  evidence: EvidenceItem[];
  flow: FlowStep[];
  /** Live reasoning stream — append-only, additive to `flow`. */
  activity: ActivityEntry[];
  /** The ONE technician the matching agent notified, if any. */
  responder: ChosenResponder | null;
  /** Live candidate slate from `responder_matched` — drives the reveal viz. */
  matching: MatchingSnapshot | null;
  /** Captured from `action_report_ready` — the demo finale's rich report. */
  report: EventReport | null;
};

const IDLE_AGENTS: Record<AgentId, AgentStatus> = {
  main: "monitoring",
  orchestrator: "standby",
  correlation: "standby",
  rootCause: "standby",
  matching: "standby",
  validation: "standby",
  remediation: "standby",
  dispatch: "standby",
};

export const initialInvestigationState: InvestigationState = {
  caseStatus: "monitoring",
  caseId: "—",
  startedAt: "—",
  agents: IDLE_AGENTS,
  decisionLabel: "WATCHDOG",
  decisionCopy: "All site feeds nominal. Specialists stay dormant until the Watchdog opens an incident.",
  evidence: [],
  flow: [],
  activity: [],
  responder: null,
  matching: null,
  report: null,
};

export type InvestigationAction =
  | {
      type: "apply";
      patch: Partial<InvestigationState>;
      evidence?: EvidenceItem[];
      flow?: FlowStep[];
      activity?: ActivityEntry[];
    }
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
      // patch.evidence / patch.flow / patch.activity replace the lists (used by
      // fault_detected to wipe the previous run); action.* append.
      const baseEvidence = action.patch.evidence ?? state.evidence;
      if (action.evidence) {
        const known = new Set(baseEvidence.map((item) => item.id));
        next.evidence = [...baseEvidence, ...action.evidence.filter((item) => !known.has(item.id))];
      }
      const baseFlow = action.patch.flow ?? state.flow;
      if (action.flow) {
        const known = new Set(baseFlow.map((step) => step.id));
        next.flow = [...baseFlow, ...action.flow.filter((step) => !known.has(step.id))];
      }
      const baseActivity = action.patch.activity ?? state.activity;
      if (action.activity) {
        const known = new Set(baseActivity.map((entry) => entry.id));
        next.activity = [...baseActivity, ...action.activity.filter((entry) => !known.has(entry.id))];
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

// Demo action reports for the LOCAL (non-streaming) replay, so the finale —
// action report + clickable document sources + PDF — works end-to-end without
// the backend. The live stream overrides these with the real `event.data.report`.
// Citations mirror the enriched shape (openable ETSI/ITU standards).
const DEMO_SOURCES: ReportCitation[] = [
  {
    doc_id: "S1",
    claim: "-48V DC output must hold within the EN 300 132-2 interface envelope.",
    title: "EN 300 132-2 V2.8.1 — -48V DC power interface",
    publisher: "ETSI",
    page: 14,
    url: "https://www.etsi.org/deliver/etsi_en/300100_300199/30013202/02.08.01_60/en_30013202v020801p.pdf",
    open_url:
      "https://www.etsi.org/deliver/etsi_en/300100_300199/30013202/02.08.01_60/en_30013202v020801p.pdf#page=14",
    openable: true,
  },
  {
    doc_id: "S3",
    claim: "Rectifier module fault classified as a critical alarm per X.733.",
    title: "X.733 — Alarm reporting function",
    publisher: "ITU-T",
    url: "https://www.itu.int/rec/T-REC-X.733-199202-I/en",
    open_url: "https://www.itu.int/rec/T-REC-X.733-199202-I/en",
    openable: true,
  },
];

// Demo responder pick — mirrors the ResponderMatchingAgent output for a complex
// energy fault at PAR-021-NORD (IDF-North): the in-zone energy senior EMP-003.
const DEMO_RESPONDER: ChosenResponder = {
  employeeId: "EMP-003",
  name: "K. Haddad",
  role: "Energy technician",
  tier: "senior",
  region: "IDF-North",
  outOfZone: false,
  difficulty: "complex",
  matchedSkills: ["dc_plant", "rectifier", "battery"],
  reason: "in-zone senior · competence 0.92 · complex-fault fit",
  score: 0.9,
};

const DEMO_REPORT_CONFIRM: EventReport = {
  diagnosis: {
    cause: "Rectifier module RM-2 failed — DC output collapsed on the -48V plant",
    confidence: 0.84,
    citations: DEMO_SOURCES,
  },
  actions: [
    { priority: "P1", action: "Replace rectifier module PN-RECT-48-2000 in shelf A (RM-2 slot)", owner: "CREW-NORD-2" },
    { priority: "P2", action: "Rebalance load across the remaining rectifiers and clear the critical alarm" },
    { priority: "P3", action: "Verify battery autonomy after the DC plant returns to nominal" },
  ],
  cost: {
    currency: "EUR",
    intervention: 1850,
    avoided: 12400,
    notes: "part: 1450.00; labour: 400.00",
  },
  inventory: { part_no: "PN-RECT-48-2000", qty_available: 3, location: "WH-PAR-CENTRAL", in_stock: true },
  dispatch: { crew: "CREW-NORD-2", booking_id: "BK-0314" },
  honesty_notes: ["Confidence 84% — field measurement confirmed the rectifier fault before dispatch."],
  citations: DEMO_SOURCES,
};

const DEMO_REPORT_PIVOT: EventReport = {
  diagnosis: {
    cause: "Cooling-loop fault — DC output nominal at the busbar; over-temperature throttled the plant",
    confidence: 0.79,
    citations: DEMO_SOURCES,
  },
  actions: [
    { priority: "P1", action: "Restore shelter cooling and clear the thermal derate on the DC plant", owner: "CREW-NORD-2" },
    { priority: "P2", action: "Inspect rectifier PN-RECT-48-2000 for thermal stress before returning to load" },
  ],
  cost: {
    currency: "EUR",
    intervention: 620,
    avoided: 12400,
    notes: "labour: 620.00",
  },
  inventory: { part_no: "PN-RECT-48-2000", qty_available: 3, location: "WH-PAR-CENTRAL", in_stock: true },
  dispatch: { crew: "CREW-NORD-2", conflict: "no crew available", booking_id: "" },
  honesty_notes: [
    "Initial telemetry-based diagnosis was contradicted by the field measurement; this report is the post-pivot re-diagnosis.",
    "No crew available for immediate dispatch — booking conflict flagged.",
  ],
  citations: DEMO_SOURCES,
};

// Local demo activity-stream helper — keeps the beats readable.
function act(
  id: string,
  kind: ActivityKind,
  agent: AgentId | undefined,
  label: string,
  detail: string,
  timestamp: string,
  tone: FlowTone,
): ActivityEntry {
  return { id, kind, agent, label, detail, timestamp, tone };
}

// Mirrors the real orchestrator sequence: fault_detected → phase 1
// (correlation, root_cause) → responder-matching → push / awaiting_field
// validation → validation verdict → phase 2 (remediation, cost/dispatch) →
// incident_resolved.
export function scenarioBeats(scenario: DemoScenario): ScenarioBeat[] {
  const localStartedAt = new Date().toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const detect: ScenarioBeat = {
    delayMs: 400,
    action: {
      type: "apply",
      patch: {
        caseStatus: "investigating",
        caseId: "INC-2026-0704-0314",
        startedAt: localStartedAt,
        agents: agents({ main: "active", orchestrator: "active" }),
        decisionLabel: "WATCHDOG",
        decisionCopy: "Watchdog triggered on the -48V rectifier DC output. Orchestrator starting phase 1.",
        report: null,
        responder: null,
      },
      evidence: [
        {
          id: "S1",
          title: "Rectifier anomaly",
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
          body: "Watchdog identifies an abnormal DC-output voltage pattern from the live site telemetry.",
          timestamp: "03:14:02",
          source: "Site Telemetry",
          tone: "primary",
        },
      ],
      activity: [
        act("a-detect", "detect", "main", "Watchdog opened INC-…-0314", "Abnormal -48V DC output on the rectifier plant.", "03:14:02", "primary"),
        act("a-route", "route", "orchestrator", "Orchestrator routing", "Typed incident state entering phase 1.", "03:14:03", "neutral"),
      ],
    },
  };

  const delegate: ScenarioBeat = {
    delayMs: 2000,
    action: {
      type: "apply",
      patch: {
        agents: agents({ main: "done", correlation: "active" }),
        decisionLabel: "CORRELATION",
        decisionCopy:
          "Correlation agent walking the site topology and alarm graph to scope the outage blast radius.",
      },
      flow: [
        {
          id: "delegate",
          index: "02",
          title: "Delegate",
          body: "Correlation agent is called because the anomaly maps to the site's DC power plant.",
          timestamp: "03:15:07",
          source: "Agent Activation",
          tone: "warning",
        },
      ],
      activity: [
        act("a-corr-start", "agent", "correlation", "Correlation working", "Scoping topology + alarms around the -48V plant.", "03:15:07", "warning"),
      ],
    },
  };

  const retrieve: ScenarioBeat = {
    delayMs: 2000,
    action: {
      type: "apply",
      patch: {
        agents: agents({ correlation: "done", rootCause: "active" }),
        decisionLabel: "ROOT-CAUSE",
        decisionCopy: "Root-Cause agent ranking causes against telecom standards and incident history.",
      },
      evidence: [
        {
          id: "D1",
          title: "Standard match",
          meta: "EN 300 132-2 · -48V DC",
          tone: "primarySubtle",
          marker: { x: 42, y: 48 },
        },
      ],
      flow: [
        {
          id: "retrieve",
          index: "03",
          title: "Retrieve",
          body: "Relevant ETSI/ITU standards, SOPs, and incident history are pulled into context.",
          timestamp: "03:16:24",
          source: "Knowledge Retrieval",
          tone: "neutral",
        },
      ],
      activity: [
        act("a-corr-done", "agent", "correlation", "Correlation done", "Blast radius scoped to shelf A rectifiers.", "03:16:10", "secondary"),
        act("a-retr", "retrieval", "rootCause", "Retrieved EN 300 132-2", "Grounding the diagnosis in the -48V DC interface standard.", "03:16:24", "neutral"),
        act("a-diag", "diagnosis", "rootCause", "Diagnosis ranked", "Top cause: rectifier RM-2 failure (84%).", "03:16:40", "neutral"),
      ],
    },
  };

  const match: ScenarioBeat = {
    delayMs: 1600,
    action: {
      type: "apply",
      patch: {
        agents: agents({ rootCause: "done", matching: "active" }),
        decisionLabel: "MATCHING",
        decisionCopy:
          "Matching agent scoring technicians on competence × difficulty-fit × zone to notify exactly one.",
      },
      activity: [
        act("a-match", "match", "matching", "Matching → K. Haddad", "In-zone energy senior picked for a complex fault — notified alone.", "03:19:52", "primary"),
      ],
    },
  };

  const handoff: ScenarioBeat = {
    delayMs: 1400,
    action: {
      type: "apply",
      patch: {
        caseStatus: "awaiting-validation",
        agents: agents({ matching: "done", validation: "active" }),
        responder: DEMO_RESPONDER,
        decisionLabel: "HUMAN HANDOFF",
        decisionCopy:
          "Push sent to K. Haddad (in-zone senior) with the exact rectifier terminal to measure. Awaiting the field verdict.",
      },
      evidence: [
        {
          id: "H1",
          title: "Human handoff",
          meta: "push sent · iOS",
          tone: "warning",
          marker: { x: 55, y: 74 },
        },
      ],
      flow: [
        {
          id: "handoff",
          index: "04",
          title: "Handoff",
          body: "The field technician receives a push on their phone with the exact DC busbar terminal to measure.",
          timestamp: "03:21:11",
          source: "Push Notification",
          tone: "secondary",
        },
      ],
      activity: [
        act("a-push", "handoff", "matching", "Push sent · iOS", "Routed to ONE technician — not broadcast to the whole crew.", "03:21:11", "secondary"),
        act("a-await", "validation", "validation", "Awaiting field verdict", "Waiting on K. Haddad's on-site measurement.", "03:21:12", "warning"),
      ],
    },
  };

  if (scenario === "confirm") {
    return [
      detect,
      delegate,
      retrieve,
      match,
      handoff,
      {
        delayMs: 2600,
        action: {
          type: "apply",
          patch: {
            agents: agents({ validation: "done", remediation: "active", dispatch: "active" }),
            decisionLabel: "VALIDATION: CONFIRMED",
            decisionCopy:
              "Field measurement confirmed the rectifier DC fault. Phase 2 building the action report.",
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
          activity: [
            act("a-valid", "validation", "validation", "Field verdict: confirmed", "K. Haddad measured 43.9V — rectifier fault confirmed.", "03:24:05", "secondary"),
            act("a-rem", "remediation", "remediation", "Remediation working", "Building the cited repair procedure.", "03:24:20", "warning"),
          ],
        },
      },
      {
        delayMs: 2200,
        action: {
          type: "apply",
          patch: {
            caseStatus: "resolved",
            agents: agents({ orchestrator: "done", remediation: "done", dispatch: "done" }),
            decisionLabel: "CASE RESOLVED",
            decisionCopy:
              "Cited repair procedure, parts, and crew booking archived. Action report generated.",
            report: DEMO_REPORT_CONFIRM,
          },
          flow: [
            {
              id: "resolve",
              index: "06",
              title: "Resolve",
              body: "Action report ready: diagnosis, cited actions, cost, inventory, and dispatch in one document.",
              timestamp: "03:26:40",
              source: "Action Report",
              tone: "secondary",
            },
          ],
          activity: [
            act("a-report", "report", "dispatch", "Action report compiled", "Diagnosis, actions, cost, inventory, dispatch + citations.", "03:26:40", "secondary"),
            act("a-resolve", "resolve", "orchestrator", "Incident resolved", "Report archived to /reports.", "03:26:41", "secondary"),
          ],
        },
      },
    ];
  }

  return [
    detect,
    delegate,
    retrieve,
    match,
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
        activity: [
          act("a-pivot", "pivot", "validation", "Field verdict: pivot", "Busbar voltage nominal — telemetry diagnosis contradicted.", "03:24:40", "warning"),
          act("a-rerun", "route", "orchestrator", "Phase 1 re-entered", "Correlation + Root-Cause re-running with the contradiction.", "03:24:42", "warning"),
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
        activity: [
          act("a-rediag", "diagnosis", "rootCause", "Re-diagnosis ready", "Cooling-loop fault throttled the DC plant (79%).", "03:25:40", "neutral"),
          act("a-rem2", "remediation", "remediation", "Remediation working", "Cited cooling-restore procedure.", "03:25:58", "warning"),
        ],
      },
    },
    {
      delayMs: 2000,
      action: {
        type: "apply",
        patch: {
          caseStatus: "resolved",
          agents: agents({ orchestrator: "done", remediation: "done", dispatch: "done" }),
          decisionLabel: "CASE RESOLVED",
          decisionCopy: "Pivoted diagnosis validated and archived. Action report generated.",
          report: DEMO_REPORT_PIVOT,
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
        activity: [
          act("a-report2", "report", "dispatch", "Action report compiled", "Post-pivot diagnosis + dispatch conflict flagged honestly.", "03:27:31", "secondary"),
          act("a-resolve2", "resolve", "orchestrator", "Incident resolved", "Report archived to /reports.", "03:27:32", "secondary"),
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

// Terminal-line helpers for the reasoning feed (used only to build
// ActivityEntry.lines — never touches the compact `detail` summary).
function short(text: string, max: number): string {
  const t = text.replace(/\s+/g, " ").trim();
  return t.length > max ? `${t.slice(0, max - 1)}…` : t;
}

const CIRCLED = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨"];
function circle(n: number): string {
  return CIRCLED[n - 1] ?? `${n}.`;
}

function num(value: unknown): number {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

// Lenient coercion of the responder pick carried on `awaiting_field_validation`
// (`data.responders[0]`, from agents/responder_matching/matcher.py). Never
// throws — a missing/degraded pick just yields null and the run continues.
function coerceResponder(value: unknown): ChosenResponder | null {
  const list = isRecord(value) ? value.responders : value;
  const first = Array.isArray(list) ? list[0] : list;
  if (!isRecord(first)) return null;
  const employeeId = str(first.employee_id);
  const name = str(first.name);
  if (!employeeId && !name) return null;
  return {
    employeeId: employeeId || name,
    name: name || employeeId,
    role: str(first.role) || undefined,
    tier: str(first.tier) || "responder",
    region: str(first.region) || undefined,
    outOfZone: Boolean(first.out_of_zone),
    difficulty: str(first.difficulty) || undefined,
    matchedSkills: Array.isArray(first.matched_skills)
      ? (first.matched_skills as unknown[]).map((s) => String(s))
      : undefined,
    reason: str(first.reason) || undefined,
    score: typeof first.score === "number" ? first.score : undefined,
  };
}

// Lenient coercion of a single roster card from the `responder_matched` slate
// (`chosen` / `candidates[]`, backend `_responder_card`). Never throws.
function coerceCard(value: unknown): MatchingCard | null {
  if (!isRecord(value)) return null;
  const employeeId = str(value.employee_id);
  const name = str(value.name);
  if (!employeeId && !name) return null;
  const score = typeof value.score === "number" ? value.score : Number(value.score);
  return {
    employeeId: employeeId || name,
    name: name || employeeId,
    tier: str(value.tier) || "responder",
    region: str(value.region),
    matchedSkills: Array.isArray(value.matched_skills)
      ? (value.matched_skills as unknown[]).map((s) => String(s))
      : [],
    score: Number.isFinite(score) ? score : 0,
    reason: str(value.reason) || undefined,
    outOfZone: "out_of_zone" in value ? Boolean(value.out_of_zone) : undefined,
  };
}

// Lenient coercion of the whole `responder_matched` narrowing snapshot. Ensures
// the chosen card sits at index 0 of `candidates` (the contract already does,
// but we normalize + de-dup so the reveal can rely on it). Yields null on a
// degraded payload with no usable card so the run just continues.
function coerceMatching(data: unknown): MatchingSnapshot | null {
  if (!isRecord(data)) return null;
  const candidates = (Array.isArray(data.candidates) ? data.candidates : [])
    .map(coerceCard)
    .filter((c): c is MatchingCard => c !== null);
  const chosen = coerceCard(data.chosen) ?? candidates[0] ?? null;
  if (!chosen) return null;
  const alternatives = candidates.filter((c) => c.employeeId !== chosen.employeeId);
  const faultRec = isRecord(data.fault) ? data.fault : {};
  return {
    fault: {
      family: str(faultRec.family),
      equipmentClass: str(faultRec.equipment_class),
      code: str(faultRec.code),
      region: str(faultRec.region),
    },
    difficulty: str(data.difficulty),
    chosen,
    candidates: [chosen, ...alternatives],
  };
}

// Lenient coercion of `event.data.report` into an EventReport. The backend
// controls this shape (orchestrator `_assemble_report`); we only guard against
// a malformed/degraded payload so the finale panel never crashes the stream.
function coerceReport(value: unknown): EventReport | null {
  if (!isRecord(value)) return null;
  const diagnosis = isRecord(value.diagnosis) ? value.diagnosis : {};
  const actions = Array.isArray(value.actions)
    ? (value.actions as Array<Record<string, unknown>>).map((a) => ({
        priority: str(a.priority) || "P1",
        action: str(a.action),
        ...(a.owner ? { owner: str(a.owner) } : {}),
      }))
    : [];
  const report: EventReport = {
    diagnosis: {
      cause: str(diagnosis.cause) || "unknown",
      confidence: typeof diagnosis.confidence === "number" ? diagnosis.confidence : 0,
      citations: Array.isArray(diagnosis.citations)
        ? (diagnosis.citations as ReportCitation[])
        : [],
    },
    actions,
    citations: Array.isArray(value.citations) ? (value.citations as ReportCitation[]) : [],
  };
  if (isRecord(value.cost)) {
    report.cost = {
      currency: str(value.cost.currency) || "EUR",
      intervention: typeof value.cost.intervention === "number" ? value.cost.intervention : 0,
      avoided: typeof value.cost.avoided === "number" ? value.cost.avoided : 0,
      notes: str(value.cost.notes),
    };
  }
  if (isRecord(value.inventory)) {
    report.inventory = {
      part_no: str(value.inventory.part_no),
      qty_available: typeof value.inventory.qty_available === "number" ? value.inventory.qty_available : 0,
      location: str(value.inventory.location),
      in_stock: Boolean(value.inventory.in_stock),
    };
  }
  if (isRecord(value.dispatch)) {
    report.dispatch = {
      crew: str(value.dispatch.crew),
      ...(value.dispatch.conflict ? { conflict: str(value.dispatch.conflict) } : {}),
      booking_id: str(value.dispatch.booking_id),
    };
  }
  if (Array.isArray(value.honesty_notes)) {
    report.honesty_notes = (value.honesty_notes as unknown[]).map((n) => String(n));
  }
  return report;
}

export function actionForBackendEvent(event: BackendEventEnvelope): InvestigationAction | null {
  const parsedTimestamp = new Date(event.ts);
  const timestamp = Number.isNaN(parsedTimestamp.getTime())
    ? event.ts.slice(11, 19) || event.ts
    : parsedTimestamp.toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
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
            : "Watchdog trigger fired. Orchestrator starting phase 1.",
          // A new incident starts a clean board — wipe the previous run's
          // evidence, flow, activity, responder, and reset agent states
          // (replayed histories can contain several runs back to back). The
          // Watchdog fires and the Orchestrator picks up routing.
          agents: { ...IDLE_AGENTS, main: "active", orchestrator: "active" },
          evidence: [],
          flow: [],
          activity: [],
          responder: null,
          matching: null,
          report: null,
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
        activity: [
          {
            id: event.id,
            kind: "detect",
            agent: "main",
            label: `Watchdog opened ${event.incident_id}`,
            detail: first
              ? `${str(first.code) || "Fault"} on ${str(first.equipment) || "equipment"}.`
              : "Opened from live signals.",
            tone: "primary",
            timestamp,
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
          agents: agents({ orchestrator: "active", correlation: "active", rootCause: "active" }),
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
        activity: [
          {
            id: event.id,
            kind: "route",
            agent: "orchestrator",
            label: "Phase 1 re-entered",
            detail: "Correlation + Root-Cause re-running with the contradiction.",
            tone: "warning",
            timestamp,
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
          // The Orchestrator is routing; the Watchdog has handed off.
          agents: agents({ [node]: "active", orchestrator: "active", main: "done" }),
          decisionLabel: AGENTS[node].name.toUpperCase(),
          decisionCopy: AGENTS[node].role,
        },
        activity: [
          {
            id: event.id,
            kind: "agent",
            agent: node,
            label: `${AGENTS[node].name} working`,
            detail: AGENTS[node].role,
            tone: "warning",
            timestamp,
          },
        ],
      };
    }

    case "agent_completed": {
      const node = WIRE_AGENT_TO_NODE[str(event.data.agent)];
      if (!node) return null;
      const status = str(event.data.status);
      const ok = status === "ok" || status === "";
      return {
        type: "apply",
        patch: {
          agents: agents({ [node]: "done" }),
          ...(!ok
            ? {
                decisionLabel: "DEGRADED",
                decisionCopy: `${AGENTS[node].name} finished with ${status}. Run continues on fallbacks.`,
              }
            : {}),
        },
        activity: [
          {
            id: event.id,
            kind: ok ? "agent" : "degraded",
            agent: node,
            label: ok ? `${AGENTS[node].name} done` : `${AGENTS[node].name} degraded`,
            detail: ok ? "Handing off to the next stage." : `Finished with ${status} — continuing on fallbacks.`,
            tone: ok ? "secondary" : "warning",
            timestamp,
          },
        ],
      };
    }

    case "retrieval_performed": {
      const results = Array.isArray(event.data.results) ? (event.data.results as Array<Record<string, unknown>>) : [];
      const top = results[0];
      if (!top) return null;
      const title = str(top.title) || str(top.doc_id) || "Document";
      const pass = String(event.data.pass ?? "1");
      const query = str(event.data.query);
      // Reasoning feed: the retrieval pass, its query, and every document the
      // Root-Cause agent grounded on (title + doc id).
      const retrievalLines: string[] = [];
      retrievalLines.push(query ? `retrieve pass ${pass} · "${short(query, 62)}"` : `retrieve pass ${pass}`);
      for (const r of results) {
        const rt = str(r.title) || str(r.doc_id) || "document";
        const id = str(r.doc_id);
        const sec = str(r.section);
        retrievalLines.push(`  ↳ ${short(rt, 60)}${sec && sec !== rt ? ` · ${short(sec, 28)}` : ""}${id ? ` [${id}]` : ""}`);
      }
      return {
        type: "apply",
        patch: {},
        evidence: [
          {
            id: `D-${event.seq}`,
            title,
            meta: `retrieval pass ${pass}`,
            tone: "primarySubtle",
            marker: { x: 42, y: 48 },
          },
        ],
        activity: [
          {
            id: event.id,
            kind: "retrieval",
            agent: "rootCause",
            label: `Grounded ${results.length} doc${results.length === 1 ? "" : "s"} · pass ${pass}`,
            detail: `Retrieved ${title} — grounding the diagnosis in cited sources.`,
            tone: "neutral",
            timestamp,
            lines: retrievalLines,
          },
        ],
      };
    }

    case "diagnostic_ready": {
      const causes = Array.isArray(event.data.causes) ? (event.data.causes as Array<Record<string, unknown>>) : [];
      const top = causes[0];
      // Reasoning feed: the RANKING itself — every candidate cause with its
      // confidence and (when the agent supplied it) why the lower ones were
      // rejected — then the selected top cause. That ranking IS the reasoning.
      const diagnosisLines: string[] = [];
      if (causes.length) {
        diagnosisLines.push(`ranking ${causes.length} candidate cause${causes.length === 1 ? "" : "s"}…`);
        causes.forEach((c, i) => {
          const conf = num(c.confidence).toFixed(2);
          const rej = str(c.rejected_because) || str(c.rejected);
          diagnosisLines.push(
            `${circle(i + 1)} ${short(str(c.cause), 74)} — conf ${conf}${rej ? `  ✗ rejected: ${short(rej, 44)}` : ""}`,
          );
        });
        if (top) diagnosisLines.push(`⇒ selected: ${short(str(top.cause), 66)}`);
      }
      return {
        type: "apply",
        patch: {
          decisionLabel: "DIAGNOSIS READY",
          decisionCopy: top
            ? `Top cause: ${str(top.cause)} (confidence ${Math.round(num(top.confidence) * 100)}%).`
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
        activity: [
          {
            id: event.id,
            kind: "diagnosis",
            agent: "rootCause",
            label: `Ranked ${causes.length || "0"} cause${causes.length === 1 ? "" : "s"}`,
            detail: top
              ? `Top cause: ${str(top.cause)} (${Math.round(num(top.confidence) * 100)}%).`
              : "Ranked causes ready.",
            tone: "neutral",
            timestamp,
            ...(diagnosisLines.length ? { lines: diagnosisLines } : {}),
          },
        ],
      };
    }

    // Additive: capture the matchmaking narrowing slate (candidates + chosen)
    // for the live employee-selection reveal. Does NOT change agent statuses —
    // push_sent / awaiting_field_validation still own the matching→validation
    // handoff — it only stashes `state.matching` and logs one activity line so
    // the matching agent's terminal reflects the narrowing.
    case "responder_matched": {
      const matching = coerceMatching(event.data);
      if (!matching) return null;
      const zone = matching.chosen.outOfZone ? "hors-zone" : "in-zone";
      const alt = matching.candidates.length - 1;
      return {
        type: "apply",
        patch: { matching },
        activity: [
          {
            id: event.id,
            kind: "match",
            agent: "matching",
            label: `Narrowed ${matching.candidates.length} → 1 · ${matching.chosen.name}`,
            detail: `${matching.chosen.tier} · ${zone}${matching.difficulty ? ` · ${matching.difficulty} fault` : ""} retained${alt > 0 ? ` — ${alt} alternative${alt === 1 ? "" : "s"} eliminated.` : "."}`,
            tone: "primary",
            timestamp,
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
          // The matching agent has picked and the push is going out.
          agents: agents({ rootCause: "done", matching: "active" }),
          decisionLabel: "HUMAN HANDOFF",
          decisionCopy: payload
            ? `Push sent to the chosen technician for ${payload.site.name} (${payload.failures.length} failure${payload.failures.length === 1 ? "" : "s"}).`
            : "Push sent to the chosen technician — routed to ONE, not broadcast.",
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
        activity: [
          {
            id: event.id,
            kind: "handoff",
            agent: "matching",
            label: "Push sent · iOS",
            detail: "Routed to ONE technician — not broadcast to the whole crew.",
            tone: "secondary",
            timestamp,
          },
        ],
      };
    }

    case "awaiting_field_validation": {
      const responder = coerceResponder(event.data);
      const zone = responder ? (responder.outOfZone ? "hors-zone" : "in-zone") : "";
      return {
        type: "apply",
        patch: {
          caseStatus: "awaiting-validation",
          // Matching is done (person notified); validation now owns the loop.
          agents: agents({ matching: "done", validation: "active" }),
          ...(responder ? { responder } : {}),
          decisionLabel: "AWAITING FIELD VALIDATION",
          decisionCopy: responder
            ? `Notified ${responder.name} (${responder.tier}, ${zone}). Waiting on their measurement and verdict.`
            : "Waiting for the technician's measurements and verdict.",
        },
        ...(responder
          ? {
              activity: [
                {
                  id: event.id,
                  kind: "match",
                  agent: "matching",
                  label: `Matched → ${responder.name}`,
                  detail: responder.reason
                    ? `${responder.tier} · ${zone} · ${responder.reason}`
                    : `${responder.tier} · ${zone} — notified alone.`,
                  tone: "primary",
                  timestamp,
                },
              ],
            }
          : {}),
      };
    }

    case "validation_received":
      return {
        type: "apply",
        patch: {
          decisionLabel: "VALIDATION RECEIVED",
          decisionCopy: "Technician response received. Validation agent scoring the verdict.",
        },
        activity: [
          {
            id: event.id,
            kind: "validation",
            agent: "validation",
            label: "Field response received",
            detail: "Validation agent scoring the verdict.",
            tone: "warning",
            timestamp,
          },
        ],
      };

    case "validation_result": {
      const pivot = event.data.result === "pivot";
      const rationale = str(event.data.rationale);
      const contradictions = Array.isArray(event.data.contradictions)
        ? (event.data.contradictions as unknown[])
        : [];
      // Reasoning feed: the validation agent's verdict, its rationale, and any
      // field contradictions it weighed against the diagnosis.
      const validationLines: string[] = [
        `verdict: ${pivot ? "PIVOT — field evidence contradicts the diagnosis" : "CONFIRMED — diagnosis holds in the field"}`,
      ];
      if (rationale) validationLines.push(`rationale: ${short(rationale, 96)}`);
      for (const c of contradictions) {
        const text = isRecord(c)
          ? str(c.detail) || str(c.reason) || str(c.field) || Object.values(c).map(String).join(" · ")
          : String(c);
        if (text) validationLines.push(`✗ contradiction: ${short(text, 78)}`);
      }
      return {
        type: "apply",
        patch: {
          caseStatus: "investigating",
          agents: agents({ validation: "done" }),
          decisionLabel: pivot ? "VALIDATION: PIVOT" : "VALIDATION: CONFIRMED",
          decisionCopy: rationale || (pivot ? "Diagnosis contradicted in the field." : "Diagnosis confirmed in the field."),
        },
        flow: [
          {
            id: event.id,
            index: "•",
            title: pivot ? "Pivot" : "Validate",
            body: rationale || "Field verdict processed.",
            tone: pivot ? "warning" : "secondary",
            ...flowBase,
          },
        ],
        activity: [
          {
            id: event.id,
            kind: pivot ? "pivot" : "validation",
            agent: "validation",
            label: pivot ? "Field verdict: pivot" : "Field verdict: confirmed",
            detail: rationale || "Field verdict processed.",
            tone: pivot ? "warning" : "secondary",
            timestamp,
            lines: validationLines,
          },
        ],
      };
    }

    case "remediation_ready": {
      const procedure = isRecord(event.data.procedure) ? event.data.procedure : {};
      const steps = Array.isArray(procedure.steps) ? (procedure.steps as Array<Record<string, unknown>>) : [];
      const safety = Array.isArray(procedure.safety) ? (procedure.safety as Array<Record<string, unknown>>) : [];
      const parts = Array.isArray(event.data.parts) ? (event.data.parts as unknown[]) : [];
      // Reasoning feed: the cited repair procedure, step by step, plus safety
      // notes and the parts list the agent compiled.
      const remediationLines: string[] = [];
      const procTitle = str(procedure.title);
      if (procTitle) remediationLines.push(`procedure: ${short(procTitle, 78)}`);
      steps.forEach((s, i) => {
        const n = s.n != null ? String(s.n) : String(i + 1);
        remediationLines.push(`${n}. ${short(str(s.text), 84)}`);
      });
      safety.forEach((s) => {
        const text = str(s.text) || (typeof s === "string" ? String(s) : "");
        if (text) remediationLines.push(`⚠ safety: ${short(text, 78)}`);
      });
      if (parts.length) {
        const names = parts
          .map((p) => (isRecord(p) ? str(p.part_no) || str(p.name) || str(p.ref) : String(p)))
          .filter(Boolean);
        if (names.length) remediationLines.push(`parts: ${short(names.join(", "), 84)}`);
      }
      return {
        type: "apply",
        patch: {
          agents: agents({ remediation: "active", dispatch: "active" }),
          decisionLabel: "REMEDIATION READY",
          decisionCopy: "Cited repair procedure and parts list prepared.",
        },
        activity: [
          {
            id: event.id,
            kind: "remediation",
            agent: "remediation",
            label: steps.length ? `Procedure · ${steps.length} step${steps.length === 1 ? "" : "s"}` : "Remediation ready",
            detail: "Cited repair procedure + parts list prepared.",
            tone: "warning",
            timestamp,
            ...(remediationLines.length ? { lines: remediationLines } : {}),
          },
        ],
      };
    }

    case "action_report_ready":
      return {
        type: "apply",
        patch: {
          decisionLabel: "ACTION REPORT READY",
          decisionCopy: "Diagnosis, actions, cost, inventory, and dispatch compiled.",
          // Stash the rich report payload for the finale panel + PDF. The
          // flow-step mapping below is preserved unchanged.
          report: coerceReport(event.data.report),
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
        activity: [
          {
            id: event.id,
            kind: "report",
            agent: "dispatch",
            label: "Action report compiled",
            detail: "Diagnosis, cited actions, cost, inventory, dispatch.",
            tone: "secondary",
            timestamp,
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
          agents: { ...IDLE_AGENTS, orchestrator: "done" },
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
        activity: [
          {
            id: event.id,
            kind: "resolve",
            agent: "orchestrator",
            label: downgraded ? "Resolved (degraded)" : "Incident resolved",
            detail: str(event.data.summary) || "Report archived to /reports.",
            tone: "secondary",
            timestamp,
          },
        ],
      };
    }

    default:
      return null;
  }
}
