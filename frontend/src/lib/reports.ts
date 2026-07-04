"use client";

import type { DemoScenario } from "./contracts";
import type { EvidenceItem, FlowStep } from "./investigation";

// Action reports produced when a case closes (roadmap: validation loop ends
// with an action report on the web). Persisted client-side: the backend has
// no reports endpoint — the report arrives once as the `action_report_ready`
// SSE event (contracts/EVENTS.md), so the web archives it locally.

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
};

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
      { id: "D1", title: "Discharge curve match", meta: "OEM-UPS-3000.pdf", tone: "primarySubtle" },
      { id: "H1", title: "Field measurement", meta: "43.9V busbar", tone: "warning" },
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

  doc.setFontSize(8);
  doc.setTextColor(...PDF.muted);
  doc.text("Generated by Arc — autonomous building incident response.", PDF.margin, 290);

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
