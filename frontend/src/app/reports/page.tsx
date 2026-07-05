"use client";

// Action report archive — list, inspect the investigation flow, download.
// Reports land here when a case resolves on /monitor (roadmap: the human
// validation loop ends with an action report on the web).

import { ChevronDown, Download, ExternalLink, FileJson, FileText } from "lucide-react";
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

          {report.diagnosis && (
            <div className="mt-4 rounded-md border border-borderSubtle bg-panelMuted p-4">
              <p className="font-mono text-[11px] uppercase tracking-label text-muted">Diagnosis</p>
              <p className="mt-1.5 text-body-sm font-medium text-text">{report.diagnosis.cause}</p>
              <p className="mt-0.5 font-mono text-caption text-resolve">
                confidence {Math.round(report.diagnosis.confidence * 100)}%
              </p>
            </div>
          )}

          {report.actions && report.actions.length > 0 && (
            <>
              <h3 className="mt-5 font-mono text-[11px] font-medium uppercase tracking-label text-muted">
                Priority actions
              </h3>
              <ol className="mt-3 flex flex-col gap-2">
                {report.actions.map((action, index) => (
                  <li
                    key={`${action.priority}-${index}`}
                    className="flex items-start gap-3 rounded-md bg-panelMuted p-3"
                  >
                    <span className="rounded bg-ember/15 px-2 py-0.5 font-mono text-[11px] font-semibold text-ember">
                      {action.priority}
                    </span>
                    <span className="min-w-0 flex-1 text-body-sm text-text">
                      {action.action}
                      {action.owner && (
                        <span className="ml-1 font-mono text-caption text-muted">· {action.owner}</span>
                      )}
                    </span>
                  </li>
                ))}
              </ol>
            </>
          )}

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

          {report.sources && report.sources.length > 0 && (
            <>
              <h3 className="mt-5 font-mono text-[11px] font-medium uppercase tracking-label text-arc">
                Sources — documents used
              </h3>
              <ul className="mt-3 flex flex-col gap-2">
                {report.sources.map((source, index) => {
                  const href = source.open_url || source.url || undefined;
                  const title = source.title || source.doc_id;
                  const pageLabel = typeof source.page === "number" ? `p.${source.page}` : null;
                  const inner = (
                    <>
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="text-body-sm font-medium text-text">{title}</span>
                        {pageLabel && (
                          <span className="font-mono text-caption text-muted">· {pageLabel}</span>
                        )}
                        {source.publisher && (
                          <span className="font-mono text-caption text-muted">· {source.publisher}</span>
                        )}
                        {href && <ExternalLink className="h-3.5 w-3.5 text-arc" />}
                      </span>
                      {source.claim && (
                        <span className="text-caption text-textSecondary">{source.claim}</span>
                      )}
                    </>
                  );
                  return (
                    <li key={`${source.doc_id}-${index}`}>
                      {href ? (
                        <a
                          href={href}
                          target="_blank"
                          rel="noreferrer"
                          className="flex flex-col gap-1 rounded-md border border-arc/40 bg-arc/[0.06] p-3 transition-colors hover:border-arc hover:bg-arc/10"
                        >
                          {inner}
                        </a>
                      ) : (
                        <div className="flex flex-col gap-1 rounded-md border border-borderSubtle bg-panelMuted p-3 opacity-80">
                          {inner}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            </>
          )}

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
            <span className="font-mono text-[11px] uppercase tracking-label text-ember">
              Telecom network operations
            </span>
            <h1 className="mt-1 font-display text-h4 font-semibold text-text">Action reports</h1>
            <p className="mt-1 text-body-sm text-muted">
              Every resolved case archives its diagnosis, cited sources, cost and dispatch, and the
              field verdict here.
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
