"use client";

import type { DemoScenario } from "./contracts";
import type { EventReport, EvidenceItem, FlowStep, ReportCitation } from "./investigation";

// Action reports produced when a case closes (roadmap: validation loop ends
// with an action report on the web). Persisted client-side: the backend has
// no reports endpoint — the report arrives once as the `action_report_ready`
// SSE event (contracts/EVENTS.md), so the web archives it locally.

// A cited document source, enriched by the backend `enrich_citations()` into an
// OPENABLE link. `open_url` (page-anchored) is preferred over `url` for links.
export type Citation = ReportCitation;

export type ReportDiagnosis = { cause: string; confidence: number };
export type ReportAction = { priority: string; action: string; owner?: string };
export type ReportCost = { currency: string; intervention: number; avoided: number; notes?: string };
export type ReportInventory = { part_no: string; qty_available: number; location: string; in_stock: boolean };
export type ReportDispatch = { crew: string; conflict?: string; booking_id: string };

export type ActionReport = {
  id: string;
  caseId: string;
  title: string;
  scenario: DemoScenario | "live";
  status: "confirmed" | "pivoted";
  site: string;
  resolvedAt: string;
  summary: string;
  operator: string;
  flow: FlowStep[];
  evidence: EvidenceItem[];
  // ── Telecom action-report fields (optional; seed/legacy reports omit them) ─
  diagnosis?: ReportDiagnosis;
  actions?: ReportAction[];
  cost?: ReportCost;
  inventory?: ReportInventory;
  dispatch?: ReportDispatch;
  honesty_notes?: string[];
  /** Cited documents used to ground the report — rendered as clickable links. */
  sources?: Citation[];
};

/** The site meta the builder stamps onto a freshly built report. */
export type ReportMeta = {
  id: string;
  caseId: string;
  title: string;
  scenario: DemoScenario | "live";
  status: "confirmed" | "pivoted";
  site: string;
  summary: string;
  operator: string;
  flow: FlowStep[];
  evidence: EvidenceItem[];
};

// Map an `action_report_ready` event payload (+ case meta, flow, evidence) into
// a persistable ActionReport. Sources come from the report's enriched citation
// trail (fallback to the diagnosis citations when the top-level list is empty).
export function buildActionReport(report: EventReport, meta: ReportMeta): ActionReport {
  const sources = (report.citations && report.citations.length > 0
    ? report.citations
    : report.diagnosis.citations) ?? [];
  return {
    id: meta.id,
    caseId: meta.caseId,
    title: meta.title,
    scenario: meta.scenario,
    status: meta.status,
    site: meta.site,
    resolvedAt: new Date().toISOString(),
    summary: meta.summary,
    operator: meta.operator,
    flow: meta.flow,
    evidence: meta.evidence,
    diagnosis: { cause: report.diagnosis.cause, confidence: report.diagnosis.confidence },
    actions: report.actions,
    cost: report.cost,
    inventory: report.inventory,
    dispatch: report.dispatch,
    honesty_notes: report.honesty_notes,
    sources,
  };
}

const KEY = "arc-reports";

const SEED_REPORTS: ActionReport[] = [
  {
    id: "RPT-2026-0702-0087",
    caseId: "INC-2026-0702-0087",
    title: "UPS battery string degradation — Building A-17 B2",
    scenario: "confirm",
    status: "confirmed",
    site: "Building A-17 / B2 power room",
    resolvedAt: "2026-07-02T14:32:09+09:00",
    summary:
      "Electrical Sub-Agent traced a 6% float-voltage sag to battery string 3. Field measurement confirmed cell degradation; replacement scheduled.",
    operator: "K. Han",
    flow: [
      { id: "s1", index: "01", title: "Detect", body: "Float voltage sag detected on UPS string 3.", timestamp: "14:02:51", source: "Sensor Feed", tone: "primary" },
      { id: "s2", index: "02", title: "Delegate", body: "Electrical Sub-Agent activated for battery diagnostics.", timestamp: "14:04:10", source: "Agent Activation", tone: "warning" },
      { id: "s3", index: "03", title: "Retrieve", body: "Battery maintenance history and OEM discharge curves retrieved.", timestamp: "14:06:47", source: "Knowledge Retrieval", tone: "neutral" },
      { id: "s4", index: "04", title: "Handoff", body: "Technician measured string 3 — confirmed degradation.", timestamp: "14:21:33", source: "Field Validation", tone: "secondary" },
    ],
    evidence: [
      { id: "S1", title: "Voltage sag", meta: "confidence 91%", tone: "primary" },
      { id: "D1", title: "Discharge curve match", meta: "EN 300 132-2", tone: "primarySubtle" },
      { id: "H1", title: "Field measurement", meta: "43.9V busbar", tone: "warning" },
    ],
    diagnosis: { cause: "UPS battery string 3 cell degradation — float voltage sag", confidence: 0.91 },
    actions: [
      { priority: "P1", action: "Replace battery string 3 and rebalance the DC plant", owner: "K. Han" },
      { priority: "P2", action: "Log capacity test results against OEM discharge curves" },
    ],
    cost: { currency: "EUR", intervention: 2100, avoided: 9800, notes: "part: 1700.00; labour: 400.00" },
    honesty_notes: ["Field measurement confirmed the degradation before dispatch."],
    sources: [
      {
        doc_id: "S1",
        claim: "Float-voltage limits for a -48V DC plant per the EN 300 132-2 interface.",
        title: "EN 300 132-2 V2.8.1 — -48V DC power interface",
        publisher: "ETSI",
        page: 14,
        url: "https://www.etsi.org/deliver/etsi_en/300100_300199/30013202/02.08.01_60/en_30013202v020801p.pdf",
        open_url:
          "https://www.etsi.org/deliver/etsi_en/300100_300199/30013202/02.08.01_60/en_30013202v020801p.pdf#page=14",
        openable: true,
      },
    ],
  },
  {
    id: "RPT-2026-0703-0112",
    caseId: "INC-2026-0703-0112",
    title: "False RF alarm traced to HVAC interference — Tower C",
    scenario: "pivot",
    status: "pivoted",
    site: "Tower C / rooftop RF array",
    resolvedAt: "2026-07-03T09:18:44+09:00",
    summary:
      "Initial RF degradation hypothesis was contradicted by clean spectrum data. HVAC Sub-Agent identified compressor EMI; shielding work ordered.",
    operator: "J. Meyer",
    flow: [
      { id: "s1", index: "01", title: "Detect", body: "Intermittent RF signal degradation on rooftop array.", timestamp: "08:41:02", source: "Sensor Feed", tone: "primary" },
      { id: "s2", index: "02", title: "Delegate", body: "Network Sub-Agent activated for RF diagnostics.", timestamp: "08:42:19", source: "Agent Activation", tone: "warning" },
      { id: "s3", index: "03", title: "Pivot", body: "Spectrum clean — interference correlates with compressor duty cycle. HVAC takes over.", timestamp: "08:55:36", source: "Agent Pivot", tone: "warning" },
      { id: "s4", index: "04", title: "Handoff", body: "Technician confirmed EMI at compressor contactor.", timestamp: "09:12:58", source: "Field Validation", tone: "secondary" },
    ],
    evidence: [
      { id: "S1", title: "RF degradation", meta: "confidence 72%", tone: "primary" },
      { id: "D2", title: "Hypothesis pivot", meta: "spectrum nominal", tone: "warning" },
      { id: "H1", title: "Field confirmation", meta: "EMI at contactor", tone: "warning" },
    ],
    diagnosis: { cause: "Compressor EMI coupling into the RF array — not an RF fault", confidence: 0.86 },
    actions: [
      { priority: "P1", action: "Order shielding work on the compressor contactor run", owner: "J. Meyer" },
      { priority: "P2", action: "Re-test the rooftop RF array after shielding" },
    ],
    dispatch: { crew: "CREW-C-1", conflict: "no crew available", booking_id: "" },
    honesty_notes: [
      "Initial RF-degradation hypothesis was contradicted by clean spectrum data; this is the post-pivot re-diagnosis.",
      "No crew available for immediate dispatch — booking conflict flagged.",
    ],
    sources: [
      {
        doc_id: "S3",
        claim: "Interference event classified and reported per the X.733 alarm function.",
        title: "X.733 — Alarm reporting function",
        publisher: "ITU-T",
        url: "https://www.itu.int/rec/T-REC-X.733-199202-I/en",
        open_url: "https://www.itu.int/rec/T-REC-X.733-199202-I/en",
        openable: true,
      },
    ],
  },
];

export function listReports(): ActionReport[] {
  if (typeof window === "undefined") return SEED_REPORTS;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) {
      window.localStorage.setItem(KEY, JSON.stringify(SEED_REPORTS));
      return SEED_REPORTS;
    }
    return JSON.parse(raw) as ActionReport[];
  } catch {
    return SEED_REPORTS;
  }
}

export function saveReport(report: ActionReport): ActionReport[] {
  const reports = [report, ...listReports().filter((existing) => existing.id !== report.id)];
  window.localStorage.setItem(KEY, JSON.stringify(reports));
  return reports;
}

// PDF layout constants (A4 portrait, mm). Colors are the Arc light-mode
// tokens so the document prints cleanly.
const PDF = {
  margin: 20,
  width: 210,
  accent: [0, 120, 174] as const, // color/fill/primary (light)
  text: [11, 17, 26] as const, // color/text/primary
  secondary: [71, 85, 105] as const, // color/text/secondary
  muted: [100, 116, 139] as const, // color/text/muted
};

export async function reportToPdf(report: ActionReport): Promise<void> {
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const contentWidth = PDF.width - PDF.margin * 2;
  let y = PDF.margin;

  const ensureRoom = (needed: number) => {
    if (y + needed > 277) {
      doc.addPage();
      y = PDF.margin;
    }
  };

  const heading = (label: string) => {
    ensureRoom(14);
    y += 4;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.setTextColor(...PDF.accent);
    doc.text(label.toUpperCase(), PDF.margin, y);
    y += 6;
  };

  const paragraph = (text: string, size = 10, color: readonly number[] = PDF.secondary) => {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(size);
    doc.setTextColor(color[0], color[1], color[2]);
    const lines = doc.splitTextToSize(text, contentWidth) as string[];
    ensureRoom(lines.length * 5);
    doc.text(lines, PDF.margin, y);
    y += lines.length * 5;
  };

  // Header band
  doc.setFillColor(...PDF.accent);
  doc.rect(0, 0, PDF.width, 3, "F");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(...PDF.accent);
  doc.text("ARC ACTION REPORT", PDF.margin, y);
  y += 8;

  doc.setFontSize(16);
  doc.setTextColor(...PDF.text);
  const titleLines = doc.splitTextToSize(report.title, contentWidth) as string[];
  doc.text(titleLines, PDF.margin, y);
  y += titleLines.length * 7 + 2;

  paragraph(
    `${report.id}  ·  ${report.caseId}  ·  ${report.site}\nResolved ${new Date(report.resolvedAt).toLocaleString()}  ·  Outcome: ${report.status}  ·  Operator: ${report.operator}`,
    9,
    PDF.muted,
  );

  heading("Summary");
  paragraph(report.summary);

  if (report.diagnosis) {
    heading("Diagnosis");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.setTextColor(...PDF.text);
    const causeLines = doc.splitTextToSize(report.diagnosis.cause, contentWidth) as string[];
    ensureRoom(causeLines.length * 5 + 4);
    doc.text(causeLines, PDF.margin, y);
    y += causeLines.length * 5;
    paragraph(`Confidence: ${Math.round(report.diagnosis.confidence * 100)}%`, 9, PDF.muted);
  }

  if (report.actions && report.actions.length > 0) {
    heading("Priority actions");
    for (const action of report.actions) {
      ensureRoom(8);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(9);
      doc.setTextColor(...PDF.accent);
      doc.text(action.priority, PDF.margin, y);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(...PDF.text);
      const owner = action.owner ? `  (${action.owner})` : "";
      const actionLines = doc.splitTextToSize(action.action + owner, contentWidth - 14) as string[];
      doc.text(actionLines, PDF.margin + 14, y);
      y += Math.max(actionLines.length * 5, 5) + 1;
    }
  }

  if (report.cost || report.dispatch || report.inventory) {
    heading("Cost & dispatch");
    if (report.cost) {
      const c = report.cost;
      paragraph(
        `Intervention: ${c.intervention.toLocaleString()} ${c.currency}  ·  Downtime avoided: ${c.avoided.toLocaleString()} ${c.currency}${c.notes ? `  ·  ${c.notes}` : ""}`,
        9,
      );
    }
    if (report.inventory) {
      const inv = report.inventory;
      paragraph(
        `Part ${inv.part_no} — ${inv.in_stock ? "in stock" : "OUT OF STOCK"} (${inv.qty_available} @ ${inv.location})`,
        9,
      );
    }
    if (report.dispatch) {
      const d = report.dispatch;
      paragraph(
        d.conflict
          ? `Dispatch: ${d.conflict}`
          : `Dispatch: crew ${d.crew}${d.booking_id ? ` · booking ${d.booking_id}` : ""}`,
        9,
      );
    }
  }

  heading("Investigation flow");
  for (const step of report.flow) {
    ensureRoom(12);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.setTextColor(...PDF.text);
    doc.text(`${step.index}  ${step.title}`, PDF.margin, y);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(...PDF.muted);
    doc.text(`${step.timestamp} / ${step.source}`, PDF.width - PDF.margin, y, { align: "right" });
    y += 5;
    paragraph(step.body, 9);
    y += 1;
  }

  heading("Evidence");
  for (const item of report.evidence) {
    ensureRoom(6);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.setTextColor(...PDF.text);
    doc.text(item.id, PDF.margin, y);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(...PDF.secondary);
    doc.text(`${item.title} — ${item.meta}`, PDF.margin + 12, y);
    y += 5;
  }

  if (report.sources && report.sources.length > 0) {
    heading("Sources / documents used");
    report.sources.forEach((source, index) => {
      ensureRoom(11);
      const link = source.open_url || source.url || undefined;
      const title = source.title || source.doc_id;
      const pageLabel = typeof source.page === "number" ? `  ·  p.${source.page}` : "";
      const label = `${index + 1}. ${title}${pageLabel}`;
      const labelLines = doc.splitTextToSize(label, contentWidth) as string[];
      doc.setFont("helvetica", "bold");
      doc.setFontSize(9);
      if (link) {
        // Clickable link to the exact document (page-anchored when known).
        doc.setTextColor(...PDF.accent);
        doc.textWithLink(labelLines[0], PDF.margin, y, { url: link });
        for (let i = 1; i < labelLines.length; i++) {
          doc.textWithLink(labelLines[i], PDF.margin, y + i * 5, { url: link });
        }
      } else {
        doc.setTextColor(...PDF.text);
        doc.text(labelLines, PDF.margin, y);
      }
      y += labelLines.length * 5;
      if (source.claim) {
        paragraph(source.claim, 8, PDF.muted);
      }
      y += 1;
    });
  }

  doc.setFontSize(8);
  doc.setTextColor(...PDF.muted);
  doc.text("Generated by Arc — autonomous telecom network operations.", PDF.margin, 290);

  doc.save(`${report.id}.pdf`);
}

export function downloadReportJson(report: ActionReport): void {
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${report.id}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}
