"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Download, ExternalLink, FileText, X } from "lucide-react";
import { Button } from "@/components/Button";
import type { ActionReport } from "@/lib/reports";
import { revealScale } from "@/motion/tokens";

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function Metric({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="border-l border-borderStrong pl-4 first:border-l-0 first:pl-0">
      <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted">{label}</dt>
      <dd className="mt-1 text-body-sm font-semibold text-text">{value}</dd>
      {detail && <dd className="mt-0.5 text-caption text-textSecondary">{detail}</dd>}
    </div>
  );
}

export function ActionReportPanel({
  report,
  open,
  onClose,
  onDownloadPdf,
  onViewArchive,
}: {
  report: ActionReport | null;
  open: boolean;
  onClose: () => void;
  onDownloadPdf: () => void;
  onViewArchive: () => void;
}) {
  const reduce = useReducedMotion();

  return (
    <AnimatePresence>
      {open && report && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          <button
            aria-label="Dismiss action report"
            onClick={onClose}
            className="absolute inset-0 bg-black/35 backdrop-blur-[2px]"
          />

          <motion.article
            role="dialog"
            aria-modal="true"
            aria-label="Intervention report"
            variants={revealScale}
            initial={reduce ? "show" : "hidden"}
            animate="show"
            className="relative flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-lg border border-borderStrong bg-background shadow-[0_24px_80px_rgba(0,0,0,0.22)]"
          >
            <header className="border-b border-borderStrong px-7 py-6">
              <div className="flex items-start justify-between gap-6">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-textSecondary">
                      Intervention report
                    </p>
                    <span className="text-muted">/</span>
                    <p className="font-mono text-[11px] text-muted">{report.id}</p>
                  </div>
                  <h2 className="mt-3 max-w-3xl font-display text-h4 font-semibold leading-tight text-text">
                    {report.title}
                  </h2>
                </div>
                <button
                  onClick={onClose}
                  aria-label="Close"
                  className="shrink-0 rounded border border-border p-2 text-muted transition-colors hover:border-borderStrong hover:text-text"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <dl className="mt-5 grid grid-cols-2 gap-4 border-t border-borderSubtle pt-4 sm:grid-cols-4">
                <Metric label="Incident" value={report.caseId} />
                <Metric label="Site" value={report.site} />
                <Metric label="Closed" value={formatDate(report.resolvedAt)} />
                <Metric label="Operator" value={report.operator} />
              </dl>
            </header>

            <div className="min-h-0 flex-1 overflow-y-auto px-7 py-6">
              {report.diagnosis && (
                <section className="grid gap-4 sm:grid-cols-[1fr_140px]">
                  <div>
                    <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-textSecondary">
                      Confirmed diagnosis
                    </h3>
                    <p className="mt-2 text-[16px] leading-relaxed text-text">{report.diagnosis.cause}</p>
                  </div>
                  <div className="border-l border-borderStrong pl-5">
                    <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted">Confidence</p>
                    <p className="mt-2 font-display text-h4 font-semibold text-text">
                      {Math.round(report.diagnosis.confidence * 100)}%
                    </p>
                  </div>
                </section>
              )}

              {report.actions && report.actions.length > 0 && (
                <section className="mt-7 border-t border-borderStrong pt-5">
                  <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-textSecondary">
                    Recommended actions
                  </h3>
                  <ol className="mt-3 divide-y divide-borderSubtle border-y border-borderSubtle">
                    {report.actions.map((action, index) => (
                      <li key={`${action.priority}-${index}`} className="grid grid-cols-[52px_1fr] gap-4 py-3.5">
                        <span className="font-mono text-[11px] font-semibold text-textSecondary">{action.priority}</span>
                        <div>
                          <p className="text-body-sm leading-relaxed text-text">{action.action}</p>
                          {action.owner && (
                            <p className="mt-1 font-mono text-[10px] uppercase tracking-wide text-muted">
                              Owner: {action.owner}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              )}

              {(report.cost || report.inventory || report.dispatch) && (
                <section className="mt-7 border-t border-borderStrong pt-5">
                  <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-textSecondary">
                    Operational summary
                  </h3>
                  <dl className="mt-4 grid gap-5 sm:grid-cols-3">
                    {report.cost && (
                      <Metric
                        label="Intervention cost"
                        value={`${report.cost.intervention.toLocaleString("fr-FR")} ${report.cost.currency}`}
                        detail={`${report.cost.avoided.toLocaleString("fr-FR")} ${report.cost.currency} estimated avoided cost`}
                      />
                    )}
                    {report.inventory && (
                      <Metric
                        label="Required part"
                        value={report.inventory.part_no}
                        detail={report.inventory.in_stock
                          ? `${report.inventory.qty_available} available · ${report.inventory.location}`
                          : "Not currently in stock"}
                      />
                    )}
                    {report.dispatch && (
                      <Metric
                        label="Dispatch"
                        value={report.dispatch.conflict || report.dispatch.crew}
                        detail={report.dispatch.booking_id || undefined}
                      />
                    )}
                  </dl>
                </section>
              )}

              {report.honesty_notes && report.honesty_notes.length > 0 && (
                <section className="mt-7 border-t border-borderStrong pt-5">
                  <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-textSecondary">
                    Limitations and assumptions
                  </h3>
                  <ul className="mt-3 list-disc space-y-1.5 pl-5 text-body-sm leading-relaxed text-textSecondary">
                    {report.honesty_notes.map((note, index) => <li key={index}>{note}</li>)}
                  </ul>
                </section>
              )}

              {report.sources && report.sources.length > 0 && (
                <section className="mt-7 border-t border-borderStrong pt-5">
                  <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-textSecondary">
                    References
                  </h3>
                  <ol className="mt-3 space-y-3">
                    {report.sources.map((source, index) => {
                      const href = source.open_url || source.url || undefined;
                      const title = source.title || source.doc_id;
                      return (
                        <li key={`${source.doc_id}-${index}`} className="grid grid-cols-[28px_1fr] gap-3 text-body-sm">
                          <span className="font-mono text-caption text-muted">[{index + 1}]</span>
                          <div className="min-w-0">
                            {href ? (
                              <a
                                href={href}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1.5 font-medium text-text underline decoration-borderStrong underline-offset-4 hover:decoration-text"
                              >
                                {title}
                                <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                              </a>
                            ) : (
                              <p className="font-medium text-text">{title}</p>
                            )}
                            <p className="mt-0.5 text-caption leading-relaxed text-textSecondary">
                              {[source.publisher, typeof source.page === "number" ? `page ${source.page}` : null, source.claim]
                                .filter(Boolean)
                                .join(" · ")}
                            </p>
                          </div>
                        </li>
                      );
                    })}
                  </ol>
                </section>
              )}
            </div>

            <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-borderStrong bg-panelMuted px-7 py-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
                Generated from validated incident evidence
              </p>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={onClose}>Close</Button>
                <Button
                  variant="ghost"
                  size="sm"
                  leadingIcon={<FileText className="h-4 w-4" />}
                  onClick={onViewArchive}
                >
                  Open archive
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  leadingIcon={<Download className="h-4 w-4" />}
                  onClick={onDownloadPdf}
                >
                  Export PDF
                </Button>
              </div>
            </footer>
          </motion.article>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
