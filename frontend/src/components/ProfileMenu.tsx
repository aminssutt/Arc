"use client";

import { FileText, LogOut, MonitorDot } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { getSession, initials, signOut, type Session } from "@/lib/session";

// Profile chip + dropdown shown on authenticated app pages.
export function ProfileMenu() {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSession(getSession());
  }, []);

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [open]);

  if (!session) {
    return (
      <Link
        href="/login"
        className="inline-flex h-8 items-center rounded-md border border-accent bg-accentSubtle px-3 text-[14px] font-semibold leading-[14px] text-accentBright hover:bg-accentSubtle/70"
      >
        Sign in
      </Link>
    );
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen((value) => !value)}
        className="flex h-9 w-9 items-center justify-center rounded-full border border-accent bg-accentSubtle text-[13px] font-semibold text-accentBright hover:bg-accentSubtle/70"
        aria-label="Profile menu"
      >
        {initials(session.name)}
      </button>
      {open && (
        <div className="arc-fade-up absolute right-0 top-11 z-50 w-60 rounded-lg border border-border bg-header p-2 shadow-glow">
          <div className="border-b border-borderSubtle px-3 py-2.5">
            <p className="text-body-sm font-medium text-text">{session.name}</p>
            <p className="text-caption text-muted">{session.role}</p>
          </div>
          <nav className="flex flex-col py-1">
            <Link
              href="/monitor"
              className="flex items-center gap-2.5 rounded-md px-3 py-2 text-body-sm text-textSecondary hover:bg-panelMuted hover:text-text"
              onClick={() => setOpen(false)}
            >
              <MonitorDot className="h-4 w-4" /> Control room
            </Link>
            <Link
              href="/reports"
              className="flex items-center gap-2.5 rounded-md px-3 py-2 text-body-sm text-textSecondary hover:bg-panelMuted hover:text-text"
              onClick={() => setOpen(false)}
            >
              <FileText className="h-4 w-4" /> Action reports
            </Link>
            <button
              className="flex items-center gap-2.5 rounded-md px-3 py-2 text-left text-body-sm text-textSecondary hover:bg-panelMuted hover:text-text"
              onClick={() => {
                signOut();
                setOpen(false);
                router.push("/");
              }}
            >
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </nav>
        </div>
      )}
    </div>
  );
}
