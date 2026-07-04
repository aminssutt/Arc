"use client";

// Action report archive — list, inspect the investigation flow, download.
// Reports land here when a case resolves on /monitor (roadmap: the human
// validation loop ends with an action report on the web).

import { ChevronDown, Download, FileJson, FileText } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { AppTopBar } from "@/components/investigation/TopBar";
import { downloadReportJson, listReports, reportToPdf, type ActionReport } from "@/lib/reports";
import { getSession } from "@/lib/session";

const STATUS_TONE = {
  confirmed: "secondary",
  pivoted: "warning",
} as const;

function ReportCard({ report }: { report: ActionReport }) {
  const [open, setOpen] = useState(false);
  const resolvedDate = new Date(report.resolvedAt);

  return (
    <article className="arc-fade-up rounded-xl border border-border bg-panel">
      <button
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-4 p-5 text-left"
      >
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={STATUS_TONE[report.status]} emphasis="subtle">
              {report.status}
            </Badge>
            <span className="font-mono text-caption text-muted">{report.id}</span>
          </div>
          <h2 className="truncate text-h6 font-semibold text-text">{report.title}</h2>
          <p className="text-body-sm text-muted">
            {report.site} · resolved {resolvedDate.toLocaleString()} · operator {report.operator}
          </p>
        </div>
        <ChevronDown
          className={`h-5 w-5 shrink-0 text-muted transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="border-t border-borderSubtle p-5">
          <p className="text-body-sm text-textSecondary">{report.summary}</p>

          <h3 className="mt-5 text-label font-medium uppercase tracking-wide text-muted">
            Investigation flow
          </h3>
          <ol className="mt-3 flex flex-col gap-2">
            {report.flow.map((step) => (
              <li key={step.id} className="flex items-start gap-3 rounded-md bg-panelMuted p-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-borderSubtle text-body-sm font-semibold text-textSecondary">
                  {step.index}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-body-sm font-medium text-text">{step.title}</p>
                  <p className="text-body-sm text-textSecondary">{step.body}</p>
                  <p className="mt-1 text-caption text-muted">
                    {step.timestamp} / {step.source}
                  </p>
                </div>
              </li>
            ))}
          </ol>

          <h3 className="mt-5 text-label font-medium uppercase tracking-wide text-muted">Evidence</h3>
          <div className="mt-3 flex flex-wrap gap-2">
            {report.evidence.map((item) => (
              <span
                key={item.id}
                className="inline-flex items-center gap-2 rounded-md border border-borderSubtle bg-panelMuted px-3 py-1.5 text-body-sm text-textSecondary"
              >
                <span className="font-semibold text-text">{item.id}</span>
                {item.title}
                <span className="text-caption text-muted">{item.meta}</span>
              </span>
            ))}
          </div>

          <div className="mt-6 flex gap-2">
            <Button
              variant="primary"
              size="sm"
              leadingIcon={<Download className="h-4 w-4" />}
              onClick={() => void reportToPdf(report)}
            >
              Download PDF
            </Button>
            <Button
              variant="ghost"
              size="sm"
              leadingIcon={<FileJson className="h-4 w-4" />}
              onClick={() => downloadReportJson(report)}
            >
              JSON
            </Button>
          </div>
        </div>
      )}
    </article>
  );
}

export default function ReportsPage() {
  const router = useRouter();
  const [reports, setReports] = useState<ActionReport[]>([]);

  useEffect(() => {
    if (!getSession()) {
      router.replace("/login?next=/reports");
      return;
    }
    setReports(listReports());
  }, [router]);

  return (
    <div className="flex min-h-screen flex-col bg-outer">
      <AppTopBar crumb="Action reports" />
      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-4 p-6">
        <header className="flex items-end justify-between py-4">
          <div>
            <h1 className="text-h4 font-semibold text-text">Action reports</h1>
            <p className="mt-1 text-body-sm text-muted">
              Every resolved case archives its investigation flow, evidence, and field verdict here.
            </p>
          </div>
          <p className="flex items-center gap-2 text-body-sm text-muted">
            <FileText className="h-4 w-4" />
            {reports.length} report{reports.length === 1 ? "" : "s"}
          </p>
        </header>

        {reports.map((report) => (
          <ReportCard key={report.id} report={report} />
        ))}
      </main>
    </div>
  );
}
