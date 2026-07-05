"use client";

// Arc control room — Figma "01 Arc Investigation Concept" (133:276 building /
// 133:589 agents). One full-screen viewport at a time, switched by the
// attached segmented control in the header row; the evidence bar is shared
// across both views. Case resolution raises the action-report modal and
// archives the report for /reports.

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { AgentGraph } from "@/components/investigation/AgentGraph";
import { ActionReportPanel } from "@/components/investigation/ActionReportPanel";
import { BuildingSituation } from "@/components/investigation/BuildingSituation";
import { DebugDock } from "@/components/investigation/DebugDock";
import { SituationLauncher } from "@/components/investigation/SituationLauncher";
import { AppTopBar, CaseStatusChip } from "@/components/investigation/TopBar";
import { BackendClient } from "@/lib/backend-client";
import { extractPushPayload, makeDemoValidation, type DemoScenario, type IncidentPushPayload, type ValidationVerdict } from "@/lib/contracts";
import {
  actionForBackendEvent,
  initialInvestigationState,
  investigationReducer,
  scenarioBeats,
  type AgentId,
  type InvestigationState,
} from "@/lib/investigation";
import { buildActionReport, reportToPdf, saveReport, type ActionReport, type ReportMeta } from "@/lib/reports";
import { getSession } from "@/lib/session";

const backendURL = process.env.NEXT_PUBLIC_ARC_BACKEND_URL ?? "http://127.0.0.1:8000";

const SITE = "Site PAR-021-NORD · equipment shelter";

function buildReport(state: InvestigationState, scenario: DemoScenario | "live", operator: string): ActionReport {
  const pivoted = state.flow.some((step) => step.id === "pivot" || step.title === "Pivot");
  const meta: ReportMeta = {
    id: state.caseId.replace(/^INC/, "RPT") + (state.caseId === "—" ? Date.now().toString() : ""),
    caseId: state.caseId,
    title: pivoted
      ? "Pivoted diagnosis validated in the field — PAR-021-NORD"
      : "Rectifier DC fault confirmed in the field — PAR-021-NORD",
    scenario,
    status: pivoted ? "pivoted" : "confirmed",
    site: SITE,
    summary: state.decisionCopy,
    operator,
    flow: state.flow,
    evidence: state.evidence,
  };
  // Rich telecom report when the backend (or local demo) supplied one; else a
  // legacy report with the optional telecom fields left undefined.
  if (state.report) return buildActionReport(state.report, meta);
  return { ...meta, resolvedAt: new Date().toISOString() };
}

export default function MonitorPage() {
  const router = useRouter();
  const [state, dispatch] = useReducer(investigationReducer, initialInvestigationState);
  const [selectedAgent, setSelectedAgent] = useState<AgentId | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"simple" | "technical">("simple");
  const [running, setRunning] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamNote, setStreamNote] = useState<string | null>(null);
  const [report, setReport] = useState<ActionReport | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
  // Latest incident push payload from the stream — the `incident` the demo
  // "Field validate" control submits (mirrors the /console path). Additive:
  // captured alongside the existing dispatch, never replaces the iOS flow.
  const [incident, setIncident] = useState<IncidentPushPayload | null>(null);

  const timersRef = useRef<number[]>([]);
  const streamAbortRef = useRef<AbortController | null>(null);
  const scenarioRef = useRef<DemoScenario | "live">("live");
  const reportedCaseRef = useRef<string | null>(null);

  useEffect(() => {
    if (!getSession()) router.replace("/login?next=/monitor");
  }, [router]);

  // Archive the action report and raise the finale panel exactly once per case —
  // keyed by case id so back-to-back runs each get their own report. Fires as
  // soon as the report lands (`action_report_ready`) or the case resolves.
  useEffect(() => {
    const ready = state.report !== null || state.caseStatus === "resolved";
    if (ready && reportedCaseRef.current !== state.caseId && state.caseId !== "—") {
      reportedCaseRef.current = state.caseId;
      const operator = getSession()?.name ?? "operator";
      const nextReport = buildReport(state, scenarioRef.current, operator);
      saveReport(nextReport);
      setReport(nextReport);
      setReportOpen(true);
    }
  }, [state]);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach((id) => window.clearTimeout(id));
    timersRef.current = [];
  }, []);

  const reset = useCallback(() => {
    clearTimers();
    setRunning(false);
    setSelectedAgent(null);
    setSelectedEvidence(null);
    setReportOpen(false);
    setReport(null);
    setIncident(null);
    reportedCaseRef.current = null;
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
      setSelectedAgent(null);
      setSelectedEvidence(null);
      setReportOpen(false);
      setReport(null);
      reportedCaseRef.current = null;
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
          // Capture the incident push payload so the demo "Field validate"
          // control can submit the same call /console uses. Additive — the
          // reducer mapping above is untouched.
          const payload = extractPushPayload(event);
          if (payload) setIncident(payload);
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

  // Demo convenience: submit the field verdict from the web (same POST the iOS
  // app / /console make) so the end-to-end finale can complete without a phone.
  // This does NOT replace the real iOS validation path — it's an extra control.
  const submitFieldValidation = useCallback(
    (verdict: ValidationVerdict) => {
      if (!incident) {
        setStreamNote("No incident to validate yet — wait for the push_sent event.");
        return;
      }
      new BackendClient(backendURL)
        .submitValidation(makeDemoValidation(incident, verdict))
        .catch((error: unknown) => {
          setStreamNote(error instanceof Error ? error.message : "validation failed");
        });
    },
    [incident],
  );

  useEffect(() => {
    if (!getSession()) return;
    startStream();
  }, [startStream]);

  useEffect(
    () => () => {
      clearTimers();
      streamAbortRef.current?.abort();
      // Null the ref so a StrictMode remount (dev) — or any remount — opens a
      // FRESH stream. Without this, startStream()'s `if (streamAbortRef.current)`
      // guard early-returns after the cleanup abort, leaving `streaming` true but
      // the SSE connection dead — so "Run incident" POSTs to the backend yet no
      // events stream back and nothing renders (the reported bug). toggleStream
      // already nulls the ref, which is why clicking "Stream on" twice unstuck it.
      streamAbortRef.current = null;
    },
    [clearTimers],
  );

  return (
    <div className="flex h-screen min-h-[680px] flex-col overflow-hidden bg-outer">
      <AppTopBar crumb="Site PAR-021-NORD   /   -48V rectifier fault">
        <p className="font-mono text-body-sm text-textSecondary">
          {state.caseId}&nbsp;&nbsp;·&nbsp;&nbsp;started {state.startedAt}
        </p>
        <CaseStatusChip caseStatus={state.caseStatus} />
      </AppTopBar>

      <main className="flex min-h-0 w-full flex-1 flex-col px-6 pb-6 pt-5">
        <div className="flex w-full shrink-0 items-center justify-between gap-4">
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[11px] uppercase tracking-label text-ember">Live incident</span>
            <h1 className="font-display text-h5 font-semibold text-text">
              {viewMode === "simple" ? "Site situation" : "Multi-agent orchestration"}
            </h1>
            <p className="text-body-sm text-textSecondary">
              {viewMode === "simple"
                ? "Factory map with live fault localization."
                : "One incident state, passed from detection to human validation."}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex h-9 overflow-hidden rounded-md border border-border" aria-label="Display detail">
              {(["simple", "technical"] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setViewMode(mode)}
                  className={[
                    "px-3 font-mono text-[10px] font-semibold uppercase tracking-wide transition-colors",
                    mode === "technical" ? "border-l border-border" : "",
                    viewMode === mode ? "bg-text text-background" : "bg-panel text-muted hover:text-text",
                  ].join(" ")}
                >
                  {mode}
                </button>
              ))}
            </div>
            <SituationLauncher
              caseStatus={state.caseStatus}
              running={running}
              canValidate={incident !== null}
              streamNote={streamNote}
              onRun={runScenario}
              onReset={reset}
              onValidate={submitFieldValidation}
            />
          </div>
        </div>

        <div className="mt-4 min-h-0 w-full flex-1 overflow-hidden rounded-xl border border-borderSubtle bg-background">
          <div className={viewMode === "simple" ? "h-full w-full" : "hidden"}>
            <BuildingSituation
              evidence={state.evidence}
              selectedId={selectedEvidence}
              onSelect={(id) => setSelectedEvidence((current) => current === id ? null : id)}
            />
          </div>
          <div className={viewMode === "technical" ? "h-full w-full" : "hidden"}>
            <AgentGraph
              agents={state.agents}
              decisionLabel={state.decisionLabel}
              decisionCopy={state.decisionCopy}
              responder={state.responder}
              activity={state.activity}
              selectedAgent={selectedAgent}
              onSelectAgent={setSelectedAgent}
            />
          </div>
        </div>
      </main>

      <ActionReportPanel
        report={report}
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        onDownloadPdf={() => {
          if (report) void reportToPdf(report);
        }}
        onViewArchive={() => router.push("/reports")}
      />

      <DebugDock
        running={running}
        streaming={streaming}
        streamNote={streamNote}
        canValidate={incident !== null}
        onRun={runScenario}
        onReset={reset}
        onToggleStream={toggleStream}
        onValidate={submitFieldValidation}
      />
    </div>
  );
}
