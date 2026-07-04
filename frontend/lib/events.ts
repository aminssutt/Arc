"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "./api";

// ---- Event contract (mirrors contracts/events.schema.json) ---------------- //
export type ArcEventType =
  | "fault_detected"
  | "phase_started"
  | "agent_started"
  | "agent_completed"
  | "retrieval_performed"
  | "diagnostic_ready"
  | "doc_requested"
  | "push_sent"
  | "awaiting_field_validation"
  | "validation_received"
  | "validation_result"
  | "remediation_ready"
  | "action_report_ready"
  | "incident_resolved";

export const ARC_EVENT_TYPES: ArcEventType[] = [
  "fault_detected", "phase_started", "agent_started", "agent_completed",
  "retrieval_performed", "diagnostic_ready", "doc_requested", "push_sent",
  "awaiting_field_validation", "validation_received", "validation_result",
  "remediation_ready", "action_report_ready", "incident_resolved",
];

export interface Envelope<T = Record<string, unknown>> {
  seq: number;
  id: string;
  ts: string;
  incident_id: string;
  type: ArcEventType;
  data: T;
}

/** Citation enriched by the backend resolver (citation drill-down). */
export interface Citation {
  doc_id: string;
  claim?: string;
  section?: string;
  title?: string;
  publisher?: string;
  snippet?: string | null;
  page?: number;
  url?: string | null;
  open_url?: string | null;
  openable?: boolean;
}

export interface Cause {
  rank?: number;
  cause: string;
  confidence: number;
  citations?: Citation[];
  rejected_because?: string;
}

export interface Responder {
  employee_id: string;
  name: string;
  tier?: string;
  region?: string;
  difficulty?: string;
  reason?: string;
  out_of_zone?: boolean;
}

export interface ActionReport {
  diagnosis: { cause: string; confidence: number; citations?: Citation[] };
  actions: { priority: string; action: string; owner?: string }[];
  cost: { currency: string; intervention: number; avoided: number; notes?: string };
  inventory?: { part_no: string; qty_available: number; location: string; in_stock: boolean };
  dispatch?: { crew: string; conflict?: string; booking_id?: string };
  honesty_notes?: string[];
  citations: Citation[];
}

export type ConnState = "connecting" | "open" | "closed";

/**
 * Subscribe to the backend SSE stream and accumulate the event envelopes.
 * The backend emits one named SSE event per type, whose `data` is the full
 * envelope JSON. Reconnects are handled by the browser's EventSource.
 */
export function useIncidentStream(): { events: Envelope[]; state: ConnState } {
  const [events, setEvents] = useState<Envelope[]>([]);
  const [state, setState] = useState<ConnState>("connecting");
  const seen = useRef<Set<string>>(new Set());

  useEffect(() => {
    const es = new EventSource(`${API_BASE}/api/stream`);
    setState("connecting");

    es.onopen = () => setState("open");
    es.onerror = () => setState("closed");

    const onEvent = (e: MessageEvent) => {
      try {
        const env = JSON.parse(e.data) as Envelope;
        const key = `${env.incident_id}:${env.seq}`;
        if (seen.current.has(key)) return; // de-dupe on reconnect replay
        seen.current.add(key);
        setEvents((prev) => [...prev, env]);
      } catch {
        /* ignore malformed frame */
      }
    };

    for (const t of ARC_EVENT_TYPES) es.addEventListener(t, onEvent as EventListener);
    es.addEventListener("message", onEvent as EventListener); // heartbeat/fallback

    return () => es.close();
  }, []);

  return { events, state };
}
