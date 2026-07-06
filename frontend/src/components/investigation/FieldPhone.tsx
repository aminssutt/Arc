"use client";

/**
 * FieldPhone — an on-screen, fully interactive replica of the technician's iOS
 * app (ios/Arc/Sources), embedded in the control room so the human-in-the-loop
 * validation can be driven from the site itself. It mirrors the native flow
 * screen-for-screen — lockscreen → push banner → dispatch ticket → (Refuse →
 * counter-measurement with a decimal keypad) → confirmation — but it is NOT a
 * mock: tapping Validate / Refuse fires the SAME POST /api/validation the real
 * phone makes, so the real SSE stream advances and the agent panel beside it
 * continues for real. The native push on the real handset is untouched — this
 * is an additional device.
 *
 * Fully self-contained "hardware": titanium frame, physical side buttons,
 * dynamic island, iOS lockscreen wallpaper, glass notifications, scrollable app
 * surfaces and spring screen transitions. System font stack (SF Pro on macOS,
 * Segoe UI on Windows) so the type reads native, not editorial.
 */
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  Bolt,
  Camera,
  Check,
  ChevronLeft,
  Cpu,
  Delete,
  Flashlight,
  Lock,
  MapPin,
  Wrench,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  FieldMeasurement,
  IncidentPushPayload,
  ValidationVerdict,
} from "@/lib/contracts";
import type { CaseStatus, ChosenResponder } from "@/lib/investigation";

// ── iOS palette (Theme.swift + system colours) ────────────────────────────────
const IOS = {
  bg: "#0a0a0f", // app canvas
  grouped: "#1c1c21", // grouped-list card
  groupedLine: "rgba(255,255,255,0.07)",
  blue: "#0078AE", // Arc brand (ArcTheme.blue)
  blueText: "#2E9FD4", // ArcTheme.blueText
  green: "#30d158", // iOS systemGreen — Validate
  red: "#ff453a", // iOS systemRed — Refuse
  orange: "#ff9f0a", // iOS systemOrange — pivot / warn
  text: "#f5f5f7",
  secondary: "rgba(245,245,247,0.60)",
  tertiary: "rgba(245,245,247,0.35)",
} as const;

// Native-feeling type — SF Pro on Apple hardware, Segoe UI elsewhere. Applied at
// the screen root so every screen inherits it instead of the app's Saira.
const SYSTEM_FONT =
  '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable Display", "Segoe UI", Roboto, sans-serif';

const SPRING = { type: "spring", stiffness: 380, damping: 32 } as const;

// Fixed design size of the handset (iPhone-ish 0.475 ratio). The device is laid
// out at this exact size and then CSS-scaled to fit its rail, so the aspect
// ratio never squashes and every screen's layout is deterministic.
const DEVICE_W = 300;
const DEVICE_H = 632;

function severityColor(sev: string): string {
  switch (sev.toLowerCase()) {
    case "critical":
      return "#ff453a";
    case "major":
      return "#ff9f0a";
    case "minor":
    case "warning":
      return "#ffd60a";
    case "cleared":
      return IOS.green;
    default:
      return IOS.secondary;
  }
}

/** Human form of an alarm code, e.g. "DC_UNDERVOLTAGE" → "DC UNDERVOLTAGE". */
function alarmLabel(code: string): string {
  return code.replace(/_/g, " ");
}

/** Probable cause in plain words — mirrors Diagnostic.probableCause (iOS). */
function probableCause(incident: IncidentPushPayload): string {
  const uv = incident.failures.find((f) => f.code.toUpperCase().includes("UNDERVOLTAGE"));
  if (uv) return "DC undervoltage on the −48 V plant";
  const first = incident.failures[0];
  if (!first) return incident.family;
  const l = alarmLabel(first.code).toLowerCase();
  return l.charAt(0).toUpperCase() + l.slice(1);
}

function primaryFailure(incident: IncidentPushPayload) {
  return (
    incident.failures.find((f) => f.code.toUpperCase().includes("UNDERVOLTAGE")) ??
    incident.failures[0]
  );
}

type Screen = "locked" | "ticket" | "counter" | "sent";

export function FieldPhone({
  incident,
  caseStatus,
  responder,
  streamNote,
  onValidate,
  onReset,
}: {
  incident: IncidentPushPayload | null;
  caseStatus: CaseStatus;
  responder: ChosenResponder | null;
  streamNote: string | null;
  /** Real submission — same POST /api/validation the iOS app makes. */
  onValidate: (verdict: ValidationVerdict, measurement?: FieldMeasurement) => void;
  onReset?: () => void;
}) {
  const reduce = useReducedMotion();
  const [screen, setScreen] = useState<Screen>("locked");
  const [sentVerdict, setSentVerdict] = useState<ValidationVerdict | null>(null);
  const [clock, setClock] = useState<{ time: string; date: string } | null>(null);
  // Track the incident we've surfaced a push for, so a new incident re-arms the
  // lockscreen banner and a full reset returns the phone to standby.
  const armedRef = useRef<string | null>(null);
  // Scale-to-fit: the handset is laid out at DEVICE_W×DEVICE_H and transformed
  // down to whatever the rail offers — the ratio never distorts.
  const shellRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState<number | null>(null);

  useEffect(() => {
    const el = shellRef.current;
    if (!el) return;
    const fit = () => {
      const box = el.getBoundingClientRect();
      setScale(Math.min(box.width / DEVICE_W, box.height / DEVICE_H, 1.1));
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const awaiting = caseStatus === "awaiting-validation" && incident !== null;

  // Lockscreen clock — client-only (avoids hydration drift), ticks regularly.
  useEffect(() => {
    const tick = () => {
      const d = new Date();
      setClock({
        time: d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", hour12: false }),
        date: d.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" }),
      });
    };
    tick();
    const id = window.setInterval(tick, 10000);
    return () => window.clearInterval(id);
  }, []);

  // Arm the push banner when a fresh incident is awaiting validation; on a full
  // reset (back to monitoring) disarm and return the phone to its idle lockscreen.
  // A `resolved` case is left alone so the "sent → Resolved" confirmation stays
  // up until the technician taps "Back to awaiting".
  useEffect(() => {
    if (awaiting && incident && armedRef.current !== incident.incident_id) {
      armedRef.current = incident.incident_id;
      setScreen("locked");
      setSentVerdict(null);
    }
    if (caseStatus === "monitoring") {
      armedRef.current = null;
      setScreen((s) => (s === "locked" ? s : "locked"));
    }
  }, [awaiting, incident, caseStatus]);

  const submit = useCallback(
    (verdict: ValidationVerdict, measurement?: FieldMeasurement) => {
      onValidate(verdict, measurement);
      setSentVerdict(verdict);
      setScreen("sent");
    },
    [onValidate],
  );

  return (
    <div className="flex h-full min-h-0 w-full flex-col">
      <header className="mb-2 flex shrink-0 items-center justify-between">
        <span className="font-mono text-[11px] font-semibold uppercase tracking-label text-textSecondary">
          Field device
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            className={[
              "h-1.5 w-1.5 rounded-full",
              awaiting ? "bg-[#0078AE]" : "bg-muted",
              awaiting && !reduce ? "animate-signal-pulse" : "",
            ].join(" ")}
          />
          <span className="font-mono text-[10px] uppercase tracking-wide text-muted">
            {awaiting ? "push" : screen === "sent" ? "sent" : "standby"}
          </span>
        </span>
      </header>

      {/* Hardware — titanium frame, side buttons, screen. Laid out at the fixed
          design size and CSS-scaled to fit the rail without distorting. */}
      <div ref={shellRef} className="flex min-h-0 flex-1 items-center justify-center overflow-hidden">
        <div
          className="relative shrink-0"
          style={{
            width: DEVICE_W,
            height: DEVICE_H,
            transform: scale !== null ? `scale(${scale})` : undefined,
            transformOrigin: "center",
            visibility: scale === null ? "hidden" : "visible",
          }}
        >
          {/* physical side buttons (behind the frame edges) */}
          <div className="absolute -left-[2px] top-[19%] h-[5.5%] w-[3px] rounded-l-md bg-[#3b3a40]" />
          <div className="absolute -left-[2px] top-[27%] h-[9%] w-[3px] rounded-l-md bg-[#3b3a40]" />
          <div className="absolute -left-[2px] top-[38%] h-[9%] w-[3px] rounded-l-md bg-[#3b3a40]" />
          <div className="absolute -right-[2px] top-[30%] h-[13%] w-[3px] rounded-r-md bg-[#3b3a40]" />

          {/* frame */}
          <div
            className="absolute inset-0 rounded-[3rem] p-[11px]"
            style={{
              background: "linear-gradient(155deg,#4a4952 0%,#232228 30%,#131317 60%,#2f2e35 100%)",
              boxShadow:
                "0 30px 70px -22px rgba(0,0,0,0.75), 0 8px 24px -10px rgba(0,0,0,0.6), inset 0 0 2px 1px rgba(255,255,255,0.12)",
            }}
          >
            {/* screen */}
            <div
              className="relative flex h-full w-full flex-col overflow-hidden rounded-[2.4rem]"
              style={{ background: IOS.bg, color: IOS.text, fontFamily: SYSTEM_FONT }}
            >
              {/* status bar + dynamic island */}
              <div className="relative z-30 flex shrink-0 items-center justify-between px-7 pb-1 pt-3">
                <span className="text-[13px] font-semibold tabular-nums tracking-tight">
                  {clock?.time ?? ""}
                </span>
                <div className="absolute left-1/2 top-[10px] flex h-[24px] w-[84px] -translate-x-1/2 items-center justify-end rounded-full bg-black pr-2">
                  <span className="h-[7px] w-[7px] rounded-full bg-[#1c2636]" />
                </div>
                <span className="flex items-center gap-1">
                  <SignalBars />
                  <span className="text-[10px] font-semibold">5G</span>
                  <Battery />
                </span>
              </div>

              {/* screens */}
              <div className="relative z-10 min-h-0 flex-1">
                <AnimatePresence mode="wait" initial={false}>
                  {screen === "locked" && (
                    <LockScreen
                      key="locked"
                      reduce={!!reduce}
                      awaiting={awaiting}
                      incident={incident}
                      clock={clock}
                      onOpen={() => setScreen("ticket")}
                    />
                  )}
                  {screen === "ticket" && incident && (
                    <TicketScreen
                      key="ticket"
                      reduce={!!reduce}
                      incident={incident}
                      responder={responder}
                      onValidate={() => submit("real")}
                      onRefuse={() => setScreen("counter")}
                    />
                  )}
                  {screen === "counter" && incident && (
                    <CounterScreen
                      key="counter"
                      reduce={!!reduce}
                      onBack={() => setScreen("ticket")}
                      onSend={(m) => submit("false", m)}
                    />
                  )}
                  {screen === "sent" && (
                    <SentScreen
                      key="sent"
                      reduce={!!reduce}
                      verdict={sentVerdict}
                      caseStatus={caseStatus}
                      streamNote={streamNote}
                      onDone={() => {
                        setScreen("locked");
                        onReset?.();
                      }}
                    />
                  )}
                </AnimatePresence>
              </div>

              {/* home indicator */}
              <div className="relative z-30 flex shrink-0 justify-center pb-2 pt-1.5">
                <span className="h-[4px] w-[34%] rounded-full bg-white/40" />
              </div>

              {/* glass glare over the whole panel */}
              <div
                className="pointer-events-none absolute inset-0 z-40 rounded-[2.4rem]"
                style={{
                  background:
                    "linear-gradient(115deg, rgba(255,255,255,0.055) 0%, rgba(255,255,255,0.015) 28%, transparent 45%)",
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── lockscreen — wallpaper, clock, glass push banner, quick actions ──────────
function LockScreen({
  reduce,
  awaiting,
  incident,
  clock,
  onOpen,
}: {
  reduce: boolean;
  awaiting: boolean;
  incident: IncidentPushPayload | null;
  clock: { time: string; date: string } | null;
  onOpen: () => void;
}) {
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={reduce ? undefined : { opacity: 0, scale: 1.06 }}
      transition={{ duration: 0.3, ease: [0.32, 0.72, 0, 1] }}
      className="absolute inset-0 flex flex-col"
    >
      {/* wallpaper — deep-blue mesh, Arc-flavoured */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(120% 90% at 85% -10%, rgba(0,120,174,0.55) 0%, transparent 55%)," +
            "radial-gradient(110% 80% at -15% 40%, rgba(46,86,190,0.38) 0%, transparent 60%)," +
            "radial-gradient(120% 90% at 60% 115%, rgba(88,44,160,0.42) 0%, transparent 60%)," +
            "linear-gradient(180deg, #060a14 0%, #0a0f1e 55%, #070912 100%)",
        }}
      />

      <div className="relative flex min-h-0 flex-1 flex-col items-center px-5 pt-5">
        <Lock className="h-3.5 w-3.5" style={{ color: "rgba(245,245,247,0.75)" }} />
        <p className="mt-2.5 text-[15px] font-medium capitalize" style={{ color: "rgba(245,245,247,0.85)" }}>
          {clock?.date ?? ""}
        </p>
        <p
          className="text-[76px] font-bold leading-[1.02] tabular-nums tracking-[-0.03em]"
          style={{ color: "rgba(245,245,247,0.96)", textShadow: "0 2px 24px rgba(0,0,0,0.35)" }}
        >
          {clock?.time ?? ""}
        </p>

        {awaiting && incident ? (
          <motion.button
            type="button"
            onClick={onOpen}
            initial={reduce ? false : { y: -70, opacity: 0, scale: 0.94 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            transition={{ ...SPRING, delay: 0.12 }}
            whileTap={{ scale: 0.975 }}
            className="mt-7 w-full rounded-[1.55rem] p-3.5 text-left backdrop-blur-xl"
            style={{
              background: "rgba(38,40,48,0.72)",
              border: "1px solid rgba(255,255,255,0.10)",
              boxShadow: "0 14px 34px -14px rgba(0,0,0,0.6)",
            }}
          >
            <div className="flex items-center gap-2.5">
              <span
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px]"
                style={{ background: `linear-gradient(160deg, ${IOS.blueText}, ${IOS.blue})` }}
              >
                <Bolt className="h-[18px] w-[18px] text-white" fill="currentColor" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[13px] font-semibold">Arc Field</span>
                  <span className="text-[11px]" style={{ color: IOS.tertiary }}>
                    now
                  </span>
                </div>
                <p className="truncate text-[13px] font-semibold leading-tight">
                  Field validation requested
                </p>
              </div>
            </div>
            <p className="mt-2 text-[12.5px] leading-snug" style={{ color: IOS.secondary }}>
              {incident.site.id} · {probableCause(incident)}. Tap to review and give your verdict.
            </p>
          </motion.button>
        ) : (
          <div
            className="mt-7 flex items-center gap-2.5 rounded-full px-4 py-2 backdrop-blur-xl"
            style={{ background: "rgba(38,40,48,0.55)", border: "1px solid rgba(255,255,255,0.08)" }}
          >
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full rounded-full opacity-60" style={{ background: IOS.blueText }} />
              <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: IOS.blueText }} />
            </span>
            <span className="text-[12px] font-medium" style={{ color: IOS.secondary }}>
              Arc · standby — awaiting dispatch
            </span>
          </div>
        )}
      </div>

      {/* quick actions */}
      <div className="relative flex shrink-0 items-center justify-between px-9 pb-4">
        <span
          className="flex h-11 w-11 items-center justify-center rounded-full backdrop-blur-xl"
          style={{ background: "rgba(38,40,48,0.6)", border: "1px solid rgba(255,255,255,0.08)" }}
        >
          <Flashlight className="h-[18px] w-[18px]" style={{ color: "rgba(245,245,247,0.85)" }} />
        </span>
        <span
          className="flex h-11 w-11 items-center justify-center rounded-full backdrop-blur-xl"
          style={{ background: "rgba(38,40,48,0.6)", border: "1px solid rgba(255,255,255,0.08)" }}
        >
          <Camera className="h-[18px] w-[18px]" style={{ color: "rgba(245,245,247,0.85)" }} />
        </span>
      </div>
    </motion.div>
  );
}

// ── in-app chrome ─────────────────────────────────────────────────────────────
function AppNav({
  title,
  onBack,
  backLabel,
}: {
  title: string;
  onBack?: () => void;
  backLabel?: string;
}) {
  return (
    <div className="relative flex h-[42px] shrink-0 items-center justify-center px-3">
      {onBack && (
        <button
          type="button"
          onClick={onBack}
          className="absolute left-2 flex items-center text-[15px]"
          style={{ color: IOS.blueText }}
        >
          <ChevronLeft className="h-5 w-5" /> {backLabel ?? "Back"}
        </button>
      )}
      <div className="flex items-center gap-1.5">
        <Bolt className="h-3.5 w-3.5" style={{ color: IOS.blueText }} fill="currentColor" />
        <span className="text-[15px] font-semibold">{title}</span>
      </div>
    </div>
  );
}

/** Grouped-list card, iOS settings style. */
function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-[1.1rem] ${className}`}
      style={{ background: IOS.grouped, border: `1px solid ${IOS.groupedLine}` }}
    >
      {children}
    </div>
  );
}

function Micro({ children }: { children: React.ReactNode }) {
  return (
    <p
      className="text-[10.5px] font-semibold uppercase tracking-[0.07em]"
      style={{ color: IOS.tertiary }}
    >
      {children}
    </p>
  );
}

function Hair() {
  return <div className="h-px w-full" style={{ background: IOS.groupedLine }} />;
}

function SeverityPill({ severity }: { severity: string }) {
  const c = severityColor(severity);
  return (
    <span
      className="rounded-full px-2.5 py-[3px] text-[10px] font-bold uppercase tracking-[0.05em]"
      style={{ color: c, background: `${c}1f`, border: `1px solid ${c}59` }}
    >
      {severity}
    </span>
  );
}

// ── screen: dispatch ticket (scrollable, Validate / Refuse) ───────────────────
function TicketScreen({
  reduce,
  incident,
  responder,
  onValidate,
  onRefuse,
}: {
  reduce: boolean;
  incident: IncidentPushPayload;
  responder: ChosenResponder | null;
  onValidate: () => void;
  onRefuse: () => void;
}) {
  const primary = primaryFailure(incident);
  const secondary = incident.failures.filter((f) => f.id !== primary?.id);
  const initials =
    responder?.name
      .split(/\s+/)
      .map((p) => p.replace(/[^A-Za-zÀ-ÿ]/g, "").charAt(0))
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase() || "T";

  return (
    <motion.div
      initial={reduce ? false : { y: 60, scale: 0.94, opacity: 0 }}
      animate={{ y: 0, scale: 1, opacity: 1 }}
      exit={reduce ? undefined : { opacity: 0, x: -46 }}
      transition={SPRING}
      className="absolute inset-0 flex flex-col"
    >
      <AppNav title="Arc Field" />

      {/* scrollable ticket body — a real phone scroll surface */}
      <div
        className="min-h-0 flex-1 overflow-y-auto px-3.5 pb-3 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        style={{ overscrollBehavior: "contain" }}
      >
        <div className="flex items-center gap-1.5 pb-2.5 pt-1">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute h-full w-full animate-signal-pulse rounded-full" style={{ background: IOS.blueText }} />
          </span>
          <span
            className="text-[10.5px] font-bold uppercase tracking-[0.08em]"
            style={{ color: IOS.blueText }}
          >
            Field validation requested
          </span>
        </div>

        <Card>
          {/* location + severity */}
          <div className="flex items-start justify-between gap-2 p-3.5">
            <div className="min-w-0">
              <Micro>Location</Micro>
              <p className="mt-0.5 text-[18px] font-bold leading-tight tracking-tight">
                {incident.site.id}
              </p>
              <p className="text-[13px]" style={{ color: IOS.secondary }}>
                {incident.site.name}
              </p>
              {incident.site.address && (
                <p className="mt-0.5 flex items-center gap-1 text-[11.5px]" style={{ color: IOS.tertiary }}>
                  <MapPin className="h-3 w-3 shrink-0" /> {incident.site.address}
                </p>
              )}
            </div>
            {primary && <SeverityPill severity={primary.severity} />}
          </div>

          <Hair />

          {/* reading hero */}
          <div className="p-3.5">
            <Micro>Reading</Micro>
            <p
              className="mt-1 break-words font-mono text-[21px] font-bold leading-[1.12] tracking-tight"
              style={{ color: IOS.blueText }}
            >
              {alarmLabel(primary?.code ?? incident.family).toUpperCase()}
            </p>
            {primary && (
              <p className="mt-1.5 flex items-center gap-1.5 text-[12.5px]" style={{ color: IOS.secondary }}>
                <Cpu className="h-3.5 w-3.5 shrink-0" /> {primary.equipment}
              </p>
            )}
          </div>

          <Hair />

          {/* probable cause */}
          <div className="p-3.5">
            <Micro>Probable cause</Micro>
            <p className="mt-1 text-[14px] font-semibold leading-snug">{probableCause(incident)}</p>
            {secondary.length > 0 && (
              <div className="mt-3">
                <Micro>Also detected</Micro>
                <div className="mt-1.5 flex flex-col gap-1.5">
                  {secondary.map((f) => (
                    <div key={f.id} className="flex items-center gap-2 text-[12px]" style={{ color: IOS.secondary }}>
                      <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: severityColor(f.severity) }} />
                      <span className="truncate">
                        {alarmLabel(f.code)} · {f.equipment}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* on-site check */}
        <Card className="mt-3">
          <div className="flex gap-2.5 p-3.5">
            <span
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[9px]"
              style={{ background: "rgba(0,120,174,0.16)" }}
            >
              <Wrench className="h-4 w-4" style={{ color: IOS.blueText }} />
            </span>
            <div className="min-w-0">
              <p className="text-[13px] font-semibold leading-tight">On-site check</p>
              <p className="mt-1 text-[12px] leading-snug" style={{ color: IOS.secondary }}>
                Measure the DC voltage at the busbar output of the rectifier shelf, then confirm or
                refuse the diagnosis. On refuse, your measurement becomes the agent&apos;s ground
                truth.
              </p>
            </div>
          </div>
        </Card>

        {/* assigned technician */}
        {responder && (
          <Card className="mt-3">
            <div className="flex items-center gap-2.5 p-3.5">
              <span
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[12px] font-bold"
                style={{ background: `linear-gradient(160deg, ${IOS.blueText}, ${IOS.blue})`, color: "#fff" }}
              >
                {initials}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13.5px] font-semibold leading-tight">{responder.name}</p>
                <p className="truncate text-[11.5px]" style={{ color: IOS.secondary }}>
                  {[responder.tier, responder.region].filter(Boolean).join(" · ")}
                </p>
              </div>
              <span
                className="rounded-full px-2 py-[3px] text-[10px] font-semibold"
                style={{ background: "rgba(48,209,88,0.14)", color: IOS.green }}
              >
                assigned
              </span>
            </div>
          </Card>
        )}

        {/* meta */}
        <div className="flex items-center justify-between px-1.5 pb-1 pt-3 font-mono text-[10.5px]" style={{ color: IOS.tertiary }}>
          <span>#{incident.incident_id}</span>
          <span>{incident.family}</span>
        </div>
      </div>

      {/* action bar */}
      <div
        className="shrink-0 px-3.5 pb-1.5 pt-2.5 backdrop-blur-xl"
        style={{ borderTop: `1px solid ${IOS.groupedLine}`, background: "rgba(10,10,15,0.85)" }}
      >
        <div className="flex gap-2.5">
          <motion.button
            type="button"
            whileTap={{ scale: 0.96 }}
            onClick={onRefuse}
            className="flex h-[46px] flex-1 items-center justify-center gap-1.5 rounded-[0.9rem] text-[15px] font-semibold"
            style={{ color: IOS.red, background: "rgba(255,69,58,0.13)" }}
          >
            <X className="h-[17px] w-[17px]" strokeWidth={2.5} /> Refuse
          </motion.button>
          <motion.button
            type="button"
            whileTap={{ scale: 0.96 }}
            onClick={onValidate}
            className="flex h-[46px] flex-1 items-center justify-center gap-1.5 rounded-[0.9rem] text-[15px] font-semibold text-black"
            style={{ background: IOS.green }}
          >
            <Check className="h-[17px] w-[17px]" strokeWidth={2.75} /> Validate
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
}

// ── screen: counter-measurement with a decimal keypad ─────────────────────────
const KEYPAD: Array<Array<string>> = [
  ["1", "2", "3"],
  ["4", "5", "6"],
  ["7", "8", "9"],
  [".", "0", "⌫"],
];

function CounterScreen({
  reduce,
  onBack,
  onSend,
}: {
  reduce: boolean;
  onBack: () => void;
  onSend: (m: FieldMeasurement) => void;
}) {
  const [digits, setDigits] = useState(""); // unsigned magnitude, e.g. "53.9"
  const [negative, setNegative] = useState(true); // DC plant voltage is negative
  const [unit, setUnit] = useState("V");

  const press = (key: string) => {
    setDigits((d) => {
      if (key === "⌫") return d.slice(0, -1);
      if (key === ".") return d.includes(".") || d === "" ? d : `${d}.`;
      if (d.replace(".", "").length >= 6) return d; // realistic meter width
      return d === "0" ? key : d + key;
    });
  };

  const parsed = digits !== "" && digits !== "." ? Number(digits) : NaN;
  const valid = Number.isFinite(parsed);

  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, x: 46 }}
      animate={{ opacity: 1, x: 0 }}
      exit={reduce ? undefined : { opacity: 0, x: 46 }}
      transition={SPRING}
      className="absolute inset-0 flex flex-col"
    >
      <AppNav title="Counter-measure" onBack={onBack} />

      <div className="flex min-h-0 flex-1 flex-col px-3.5 pb-2">
        <p className="shrink-0 text-[12px] leading-snug" style={{ color: IOS.secondary }}>
          Enter what you measured on site — the agent re-diagnoses against it.
        </p>

        {/* live display */}
        <Card className="mt-2.5 shrink-0">
          <div className="p-3.5">
            <div className="flex items-center justify-between">
              <Micro>Measurement</Micro>
              <span className="font-mono text-[10.5px]" style={{ color: IOS.tertiary }}>
                DC voltage · busbar
              </span>
            </div>
            <div className="mt-1 flex items-baseline justify-between gap-2">
              <p
                className="min-w-0 flex-1 truncate font-mono text-[38px] font-bold tabular-nums leading-none tracking-tight"
                style={{ color: digits ? IOS.blueText : IOS.tertiary }}
              >
                {negative ? "−" : ""}
                {digits || "53.9"}
              </p>
              <div className="flex shrink-0 items-center gap-1">
                {["V", "A"].map((u) => (
                  <button
                    key={u}
                    type="button"
                    onClick={() => setUnit(u)}
                    className="rounded-full px-2.5 py-1 font-mono text-[12px] font-semibold transition-colors"
                    style={
                      unit === u
                        ? { background: "rgba(0,120,174,0.25)", color: IOS.blueText }
                        : { color: IOS.tertiary }
                    }
                  >
                    {u}
                  </button>
                ))}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setNegative((n) => !n)}
              className="mt-2 rounded-full px-2.5 py-1 font-mono text-[11px] font-semibold"
              style={{
                background: negative ? "rgba(0,120,174,0.18)" : "rgba(255,255,255,0.07)",
                color: negative ? IOS.blueText : IOS.secondary,
              }}
            >
              ± sign: {negative ? "negative" : "positive"}
            </button>
          </div>
        </Card>

        {/* keypad */}
        <div className="mt-auto grid shrink-0 grid-cols-3 gap-1.5 pt-2.5">
          {KEYPAD.flat().map((key) => (
            <motion.button
              key={key}
              type="button"
              whileTap={{ scale: 0.92, backgroundColor: "rgba(255,255,255,0.16)" }}
              onClick={() => press(key)}
              className="flex h-[44px] items-center justify-center rounded-[0.8rem] text-[20px] font-medium tabular-nums"
              style={{ background: "rgba(255,255,255,0.065)" }}
            >
              {key === "⌫" ? <Delete className="h-5 w-5" style={{ color: IOS.secondary }} /> : key}
            </motion.button>
          ))}
        </div>

        <motion.button
          type="button"
          whileTap={{ scale: 0.97 }}
          disabled={!valid}
          onClick={() => valid && onSend({ value: negative ? -parsed : parsed, unit })}
          className="mt-2.5 flex h-[46px] w-full shrink-0 items-center justify-center gap-1.5 rounded-[0.9rem] text-[15px] font-semibold text-white transition-opacity disabled:opacity-40"
          style={{ background: IOS.blue }}
        >
          Send measurement
        </motion.button>
      </div>
    </motion.div>
  );
}

// ── screen: confirmation ──────────────────────────────────────────────────────
function SentScreen({
  reduce,
  verdict,
  caseStatus,
  streamNote,
  onDone,
}: {
  reduce: boolean;
  verdict: ValidationVerdict | null;
  caseStatus: CaseStatus;
  streamNote: string | null;
  onDone: () => void;
}) {
  const pivot = verdict === "false";
  const resolved = caseStatus === "resolved";
  const working = !resolved && caseStatus === "investigating";
  const tint = pivot && !resolved ? IOS.orange : IOS.green;

  const caption = useMemo(() => {
    if (streamNote) return streamNote;
    if (resolved) return "Diagnosis closed — the action report is ready in the control room.";
    return pivot
      ? "Your measurement contradicts the diagnosis — the agent is re-diagnosing live."
      : "Diagnosis confirmed — the control room is writing the action report.";
  }, [pivot, resolved, streamNote]);

  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={reduce ? undefined : { opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center"
    >
      {/* success ring */}
      <div className="relative h-[76px] w-[76px]">
        <svg viewBox="0 0 76 76" className="h-full w-full -rotate-90">
          <circle cx="38" cy="38" r="34" fill="none" stroke={`${tint}30`} strokeWidth="3" />
          <motion.circle
            cx="38"
            cy="38"
            r="34"
            fill="none"
            stroke={tint}
            strokeWidth="3"
            strokeLinecap="round"
            initial={reduce ? { pathLength: 1 } : { pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.7, ease: [0.32, 0.72, 0, 1] }}
          />
        </svg>
        <motion.span
          className="absolute inset-0 flex items-center justify-center"
          initial={reduce ? false : { scale: 0.4, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ ...SPRING, delay: 0.25 }}
        >
          <Check className="h-8 w-8" strokeWidth={2.5} style={{ color: tint }} />
        </motion.span>
      </div>

      <p className="mt-5 text-[18px] font-bold tracking-tight">
        {resolved ? "Resolved" : pivot ? "Sent — re-diagnosing" : "Sent — finishing up"}
      </p>
      <p className="mt-1.5 text-[12.5px] leading-snug" style={{ color: IOS.secondary }}>
        {caption}
      </p>

      {/* live agent status */}
      <div
        className="mt-4 flex items-center gap-2 rounded-full px-3.5 py-1.5"
        style={{ background: "rgba(255,255,255,0.06)" }}
      >
        {working && !reduce ? (
          <motion.span
            className="h-2 w-2 rounded-full"
            style={{ background: IOS.blueText }}
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity }}
          />
        ) : (
          <span className="h-2 w-2 rounded-full" style={{ background: resolved ? IOS.green : IOS.blueText }} />
        )}
        <span className="font-mono text-[10.5px]" style={{ color: IOS.tertiary }}>
          {resolved
            ? "action report ready"
            : `${pivot ? "refuse → pivot" : "validate → confirm"} · sent to backend`}
        </span>
      </div>

      <motion.button
        type="button"
        whileTap={{ scale: 0.96 }}
        onClick={onDone}
        className="mt-8 rounded-[0.9rem] px-5 py-2.5 text-[14px] font-semibold"
        style={{ color: IOS.blueText, background: "rgba(0,120,174,0.14)" }}
      >
        Back to awaiting
      </motion.button>
    </motion.div>
  );
}

// ── status-bar glyphs ─────────────────────────────────────────────────────────
function SignalBars() {
  return (
    <span className="flex items-end gap-[1.5px]">
      {[4, 6, 8, 10].map((h, i) => (
        <span
          key={h}
          className="w-[3px] rounded-[1px]"
          style={{ height: h, background: i < 3 ? "#f5f5f7" : "rgba(245,245,247,0.35)" }}
        />
      ))}
    </span>
  );
}

function Battery() {
  return (
    <span className="ml-0.5 flex items-center">
      <span className="flex h-[11px] w-[21px] items-center rounded-[3px] border border-white/40 px-[1.5px]">
        <span className="h-[7px] w-[70%] rounded-[1px] bg-white" />
      </span>
      <span className="ml-[1px] h-[4px] w-[1.5px] rounded-r-[1px] bg-white/40" />
    </span>
  );
}

export default FieldPhone;
