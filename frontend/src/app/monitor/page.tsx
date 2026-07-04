"use client";

// Arc control room — Figma "01 Arc Investigation Concept" (133:276 building /
// 133:589 agents). One full-screen viewport at a time, switched by the
// attached segmented control in the header row; the evidence bar is shared
// across both views. Case resolution raises the action-report modal and
// archives the report for /reports.

import { BookText, CheckCircle2, FileText } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { Button } from "@/components/Button";
import { Modal } from "@/components/Modal";
import { AgentGraph } from "@/components/investigation/AgentGraph";
import { BuildingSituation } from "@/components/investigation/BuildingSituation";
import { DebugDock } from "@/components/investigation/DebugDock";
import { EvidenceBar } from "@/components/investigation/EvidenceBar";
import { AppTopBar, CaseStatusChip } from "@/components/investigation/TopBar";
import { BackendClient } from "@/lib/backend-client";
import type { DemoScenario } from "@/lib/contracts";
import {
  actionForBackendEvent,
  initialInvestigationState,
  investigationReducer,
  scenarioBeats,
  type AgentId,
  type InvestigationState,
} from "@/lib/investigation";
import { saveReport, type ActionReport } from "@/lib/reports";
import { getSession } from "@/lib/session";

const backendURL = process.env.NEXT_PUBLIC_ARC_BACKEND_URL ?? "http://127.0.0.1:8000";

type PanelId = "building" | "agents";

const PANEL_META: Record<PanelId, { title: string; subtitle: string }> = {
  building: {
    title: "Building Situation",
    subtitle: "B5 electrical room / Power Feed 1 anomaly",
  },
  agents: {
    title: "Agent Orchestration",
    subtitle: "Sub-agents stay dormant until the main agent calls them.",
  },
};

function buildReport(state: InvestigationState, scenario: DemoScenario | "live", operator: string): ActionReport {
  const pivoted = state.flow.some((step) => step.id === "pivot" || step.title === "Pivot");
  return {
    id: state.caseId.replace(/^INC/, "RPT") + (state.caseId === "—" ? Date.now().toString() : ""),
    caseId: state.caseId,
    title: pivoted
      ? "Pivoted diagnosis confirmed in the field — Building A-17 B5"
      : "Power Feed 1 fault confirmed — Building A-17 B5",
    scenario,
    status: pivoted ? "pivoted" : "confirmed",
    site: "Building A-17 / B5 electrical room",
    resolvedAt: new Date().toISOString(),
    summary: state.decisionCopy,
    operator,
    flow: state.flow,
    evidence: state.evidence,
  };
}

export default function MonitorPage() {
  const router = useRouter();
  const [state, dispatch] = useReducer(investigationReducer, initialInvestigationState);
  const [panel, setPanel] = useState<PanelId>("building");
  const [selectedEvidence, setSelectedEvidence] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<AgentId | null>(null);
  const [running, setRunning] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamNote, setStreamNote] = useState<string | null>(null);
  const [report, setReport] = useState<ActionReport | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const timersRef = useRef<number[]>([]);
  const streamAbortRef = useRef<AbortController | null>(null);
  const scenarioRef = useRef<DemoScenario | "live">("live");
  const reportedCaseRef = useRef<string | null>(null);

  useEffect(() => {
    if (!getSession()) router.replace("/login?next=/monitor");
  }, [router]);

  // Archive the action report and raise the modal exactly once per case —
  // keyed by case id so back-to-back runs each get their own report.
  useEffect(() => {
    if (state.caseStatus === "resolved" && reportedCaseRef.current !== state.caseId) {
      reportedCaseRef.current = state.caseId;
      const operator = getSession()?.name ?? "operator";
      const nextReport = buildReport(state, scenarioRef.current, operator);
      saveReport(nextReport);
      setReport(nextReport);
      setModalOpen(true);
    }
  }, [state]);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach((id) => window.clearTimeout(id));
    timersRef.current = [];
  }, []);

  const reset = useCallback(() => {
    clearTimers();
    setRunning(false);
    setSelectedEvidence(null);
    setSelectedAgent(null);
    setModalOpen(false);
    setReport(null);
    dispatch({ type: "reset" });
    if (streaming) {
      new BackendClient(backendURL).reset().catch(() => {
        /* local reset remains valid without a backend */
      });
    }
  }, [clearTimers, streaming]);

  const runScenario = useCallback(
    (scenario: DemoScenario) => {
      clearTimers();
      setSelectedEvidence(null);
      setSelectedAgent(null);
      setModalOpen(false);
      setReport(null);
      dispatch({ type: "reset" });
      setRunning(true);
      scenarioRef.current = scenario;

      if (streaming) {
        // Live mode: the backend drives state via SSE. inject-fault 409s
        // while an incident is active, so reset the orchestrator first.
        const client = new BackendClient(backendURL);
        client
          .reset()
          .then(() => client.injectFault({ scenario }))
          .catch((error: unknown) => {
            setStreamNote(error instanceof Error ? error.message : "inject failed");
          })
          .finally(() => setRunning(false));
        return;
      }

      let elapsed = 0;
      const beats = scenarioBeats(scenario);
      beats.forEach((beat, index) => {
        elapsed += beat.delayMs;
        const timer = window.setTimeout(() => {
          dispatch(beat.action);
          if (index === beats.length - 1) setRunning(false);
        }, elapsed);
        timersRef.current.push(timer);
      });
    },
    [clearTimers, streaming],
  );

  // Reconnects with a capped backoff whenever the stream drops (backend
  // restart, network blip, backend not up yet). Reconnecting from scratch is
  // safe: the backend replays event history and the reducer dedupes by id.
  const startStream = useCallback(() => {
    if (streamAbortRef.current) return;

    const abort = new AbortController();
    streamAbortRef.current = abort;
    setStreaming(true);
    setStreamNote(null);
    scenarioRef.current = "live";

    const connect = (attempt: number) => {
      if (abort.signal.aborted) return;
      new BackendClient(backendURL)
        .streamEvents((event) => {
          const action = actionForBackendEvent(event);
          if (action) dispatch(action);
        }, abort.signal)
        .then(() => {
          // Server closed the stream cleanly — reconnect immediately.
          if (!abort.signal.aborted) connect(0);
        })
        .catch((error: unknown) => {
          if (abort.signal.aborted) return;
          const delay = Math.min(1000 * 2 ** attempt, 10000);
          setStreamNote(
            `${error instanceof Error ? error.message : "stream failed"} — retrying in ${Math.round(delay / 1000)}s`,
          );
          const timer = window.setTimeout(() => connect(attempt + 1), delay);
          timersRef.current.push(timer);
        });
    };

    connect(0);
  }, []);

  const toggleStream = useCallback(() => {
    if (streaming) {
      streamAbortRef.current?.abort();
      streamAbortRef.current = null;
      setStreaming(false);
      setStreamNote(null);
      return;
    }
    startStream();
  }, [startStream, streaming]);

  useEffect(() => {
    if (!getSession()) return;
    startStream();
  }, [startStream]);

  useEffect(
    () => () => {
      clearTimers();
      streamAbortRef.current?.abort();
    },
    [clearTimers],
  );

  const meta = PANEL_META[panel];

  return (
    <div className="flex h-screen min-h-[680px] flex-col overflow-hidden bg-outer">
      <AppTopBar crumb="Building A-17   /   Case B5 electrical fault">
        <p className="text-body text-textSecondary">
          Case ID: {state.caseId}&nbsp;&nbsp;|&nbsp;&nbsp;Started: {state.startedAt}
        </p>
        <CaseStatusChip caseStatus={state.caseStatus} />
      </AppTopBar>

      <main className="flex min-h-0 w-full flex-1 flex-col gap-4 p-6">
        {/* Header row — Figma 133:520 / 133:599 */}
        <div className="flex w-full shrink-0 items-center justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="text-h5 font-semibold text-text">{meta.title}</h1>
            <p className="text-body-sm text-textSecondary">{meta.subtitle}</p>
          </div>
          <div className="flex items-start">
            <button
              onClick={() => setPanel("building")}
              className={[
                "flex h-8 items-center gap-2 rounded-l-md px-3 text-[14px] font-semibold leading-[14px] transition-colors",
                panel === "building"
                  ? "bg-accent text-background"
                  : "border border-r-0 border-accent bg-accentSubtle text-accentBright hover:bg-accentSubtle/70",
              ].join(" ")}
            >
              <BookText className="h-4 w-4" />
              Building Situation
            </button>
            <button
              onClick={() => setPanel("agents")}
              className={[
                "flex h-8 items-center gap-2 rounded-r-md px-3 text-[14px] font-semibold leading-[14px] transition-colors",
                panel === "agents"
                  ? "bg-accent text-background"
                  : "border border-l-0 border-accent bg-accentSubtle text-accentBright hover:bg-accentSubtle/70",
              ].join(" ")}
            >
              <FileText className="h-4 w-4" />
              Agent Orchestration
            </button>
          </div>
        </div>

        {/* Viewport — 133:287 / 133:606 */}
        <div className="min-h-0 w-full flex-1">
          <div className={panel === "building" ? "h-full w-full" : "hidden"}>
            <BuildingSituation
              evidence={state.evidence}
              selectedId={selectedEvidence}
              onSelect={(id) => setSelectedEvidence((current) => (current === id ? null : id))}
            />
          </div>
          <div className={panel === "agents" ? "h-full w-full" : "hidden"}>
            <AgentGraph
              agents={state.agents}
              decisionLabel={state.decisionLabel}
              decisionCopy={state.decisionCopy}
              selectedAgent={selectedAgent}
              onSelectAgent={setSelectedAgent}
            />
          </div>
        </div>

        {/* Shared evidence bar — 133:530 / 133:608 */}
        <EvidenceBar
          evidence={state.evidence}
          selectedId={selectedEvidence}
          onSelect={(id) => {
            setSelectedEvidence((current) => (current === id ? null : id));
            setPanel("building");
          }}
        />
      </main>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        tone="secondary"
        icon={<CheckCircle2 className="h-6 w-6" />}
        title="Field validation complete"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setModalOpen(false)}>
              Stay on monitor
            </Button>
            <Button
              variant="primary"
              size="sm"
              leadingIcon={<FileText className="h-4 w-4" />}
              onClick={() => router.push("/reports")}
            >
              View action report
            </Button>
          </>
        }
      >
        <p>{report?.summary}</p>
        {report && (
          <div className="mt-3 rounded-md border border-borderSubtle bg-panelMuted p-3">
            <p className="text-caption text-muted">
              {report.id} · {report.caseId}
            </p>
            <p className="mt-1 text-body-sm font-medium text-text">{report.title}</p>
          </div>
        )}
      </Modal>

      <DebugDock
        running={running}
        streaming={streaming}
        streamNote={streamNote}
        onRun={runScenario}
        onReset={reset}
        onToggleStream={toggleStream}
      />
    </div>
  );
}
