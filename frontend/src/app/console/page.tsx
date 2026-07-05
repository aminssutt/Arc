"use client";

import { Activity, CheckCircle2, CircleStop, RotateCcw, Send, Server, Zap } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { BackendClient } from "@/lib/backend-client";
import {
  type BackendEventEnvelope,
  type DemoScenario,
  type HealthResponse,
  type IncidentPushPayload,
  extractPushPayload,
  makeDemoValidation,
} from "@/lib/contracts";

const defaultBackendURL = process.env.NEXT_PUBLIC_ARC_BACKEND_URL ?? "http://127.0.0.1:8000";

export default function ControlRoomPage() {
  const [backendURL, setBackendURL] = useState(defaultBackendURL);
  const [status, setStatus] = useState("Backend not checked.");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [incident, setIncident] = useState<IncidentPushPayload | null>(null);
  const [events, setEvents] = useState<BackendEventEnvelope[]>([]);
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const client = useMemo(() => new BackendClient(backendURL.replace(/\/$/, "")), [backendURL]);

  async function run(label: string, operation: () => Promise<string>) {
    try {
      setStatus(`${label}...`);
      setStatus(await operation());
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    }
  }

  async function checkHealth() {
    await run("Checking health", async () => {
      const response = await client.health();
      setHealth(response);
      return `Health: ${response.status}, state: ${response.state}`;
    });
  }

  async function inject(scenario: DemoScenario) {
    startStream();
    await run(`Injecting ${scenario}`, async () => {
      const response = await client.injectFault({ scenario });
      return `Injected ${response.scenario}: ${response.incident_id ?? "no incident"}, state: ${response.state}`;
    });
  }

  async function reset() {
    await run("Resetting", async () => {
      const response = await client.reset();
      setIncident(null);
      setEvents([]);
      setHealth(null);
      return `Reset: ${response.status}`;
    });
  }

  async function submit(verdict: "real" | "false") {
    if (!incident) {
      setStatus("No incident loaded.");
      return;
    }

    await run(`Submitting ${verdict}`, async () => {
      const response = await client.submitValidation(makeDemoValidation(incident, verdict));
      return `Validation accepted: ${response.incident_id}, result: ${response.result}`;
    });
  }

  function startStream() {
    if (abortRef.current) return;

    const controller = new AbortController();
    abortRef.current = controller;
    setStreaming(true);
    setStatus("Stream connected.");

    client
      .streamEvents((event) => {
        setEvents((current) => [event, ...current].slice(0, 12));
        setStatus(`Event: ${event.type}`);

        const payload = extractPushPayload(event);
        if (payload) setIncident(payload);
      }, controller.signal)
      .catch((error) => {
        if (!controller.signal.aborted) {
          setStatus(error instanceof Error ? error.message : String(error));
        }
      })
      .finally(() => {
        if (abortRef.current === controller) {
          abortRef.current = null;
          setStreaming(false);
        }
      });
  }

  function stopStream() {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setStatus("Stream disconnected.");
  }

  return (
    <main className="min-h-screen bg-background px-6 py-6 text-text">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="flex flex-col gap-3 border-b border-border pb-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent">Arc</p>
            <h1 className="mt-1 text-3xl font-semibold">Control Room</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted">
              Next.js contract surface for backend stream, incident payloads, and validation submission.
            </p>
          </div>
          <StatusPill label={streaming ? "SSE connected" : "SSE disconnected"} active={streaming} />
        </header>

        <section className="grid gap-5 lg:grid-cols-[360px_1fr]">
          <aside className="flex flex-col gap-4">
            <Panel title="Backend" icon={<Server size={18} />}>
              <label className="block text-xs font-medium uppercase tracking-[0.12em] text-muted">
                URL
              </label>
              <input
                value={backendURL}
                onChange={(event) => setBackendURL(event.target.value)}
                className="mt-2 w-full rounded-md border border-border bg-raised px-3 py-2 font-mono text-sm outline-none focus:border-accent"
              />
              <p className="mt-3 text-sm text-muted">{status}</p>
              <div className="mt-4 grid grid-cols-2 gap-2">
                <ActionButton icon={<Activity size={16} />} onClick={checkHealth}>Health</ActionButton>
                <ActionButton icon={streaming ? <CircleStop size={16} /> : <Zap size={16} />} onClick={streaming ? stopStream : startStream}>
                  {streaming ? "Stop Stream" : "Start Stream"}
                </ActionButton>
                <ActionButton icon={<Send size={16} />} onClick={() => inject("confirm")}>Inject Confirm</ActionButton>
                <ActionButton icon={<Send size={16} />} onClick={() => inject("pivot")}>Inject Pivot</ActionButton>
                <ActionButton icon={<CheckCircle2 size={16} />} onClick={() => submit("real")} disabled={!incident}>Submit Real</ActionButton>
                <ActionButton icon={<CircleStop size={16} />} onClick={() => submit("false")} disabled={!incident}>Submit False</ActionButton>
              </div>
              <button
                onClick={reset}
                className="mt-2 flex w-full items-center justify-center gap-2 rounded-md border border-border bg-panel px-3 py-2 text-sm font-semibold text-text hover:bg-raised"
              >
                <RotateCcw size={16} />
                Reset Backend
              </button>
            </Panel>

            <Panel title="Health">
              {health ? (
                <dl className="space-y-3 text-sm">
                  <div>
                    <dt className="text-muted">Status</dt>
                    <dd className="font-mono text-accent">{health.status}</dd>
                  </div>
                  <div>
                    <dt className="text-muted">State</dt>
                    <dd className="font-mono">{health.state}</dd>
                  </div>
                  <div>
                    <dt className="text-muted">Seed files</dt>
                    <dd className="font-mono">{Object.keys(health.seeds).length}</dd>
                  </div>
                </dl>
              ) : (
                <p className="text-sm text-muted">No health response yet.</p>
              )}
            </Panel>
          </aside>

          <section className="grid gap-5 xl:grid-cols-[1fr_420px]">
            <Panel title="Incident Payload">
              {incident ? <IncidentView incident={incident} /> : <EmptyState />}
            </Panel>

            <Panel title="Event Log">
              <div className="flex max-h-[620px] flex-col gap-2 overflow-auto">
                {events.length ? (
                  events.map((event) => <EventRow key={event.id} event={event} />)
                ) : (
                  <p className="text-sm text-muted">No stream events yet.</p>
                )}
              </div>
            </Panel>
          </section>
        </section>
      </div>
    </main>
  );
}

function Panel({
  title,
  icon,
  children,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border bg-panel p-4">
      <div className="mb-4 flex items-center gap-2">
        {icon}
        <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-muted">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function ActionButton({
  icon,
  disabled,
  onClick,
  children,
}: {
  icon: React.ReactNode;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      className="flex min-h-10 items-center justify-center gap-2 rounded-md border border-border bg-raised px-3 py-2 text-sm font-semibold text-text hover:border-accent disabled:cursor-not-allowed disabled:opacity-40"
    >
      {icon}
      <span>{children}</span>
    </button>
  );
}

function StatusPill({ label, active }: { label: string; active: boolean }) {
  return (
    <div className="w-fit rounded-full border border-border bg-panel px-3 py-1 text-sm">
      <span className={active ? "text-accent" : "text-muted"}>{label}</span>
    </div>
  );
}

function IncidentView({ incident }: { incident: IncidentPushPayload }) {
  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">{incident.family}</p>
        <h2 className="mt-1 text-2xl font-semibold">{incident.incident_id}</h2>
        <p className="mt-2 text-sm text-muted">
          {incident.site.name} · {incident.site.id}
        </p>
        <p className="mt-1 text-sm text-muted">{incident.site.address}</p>
        <p className="mt-1 font-mono text-xs text-muted">
          {incident.site.lat}, {incident.site.lon}
        </p>
      </div>

      <div className="grid gap-3">
        {incident.failures.map((failure) => (
          <div key={failure.id} className="rounded-md border border-border bg-raised p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold">{failure.code}</p>
                <p className="mt-1 text-sm text-muted">{failure.equipment}</p>
              </div>
              <span className="rounded-md border border-border px-2 py-1 font-mono text-xs text-warning">
                {failure.severity}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EventRow({ event }: { event: BackendEventEnvelope }) {
  return (
    <div className="rounded-md border border-border bg-raised p-3">
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-sm text-text">{event.type}</span>
        <span className="font-mono text-xs text-muted">{event.id}</span>
      </div>
      <p className="mt-2 text-xs text-muted">{event.ts}</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex min-h-[320px] items-center justify-center rounded-md border border-dashed border-border">
      <p className="text-sm text-muted">Start stream, then inject a scenario to load the backend push payload.</p>
    </div>
  );
}
