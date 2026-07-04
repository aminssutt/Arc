"use client";

// Lightweight client-side session for the demo product shell.
// Real auth is out of scope for the hackathon; this keeps the profile
// consistent across /monitor and /reports.

export type Session = {
  name: string;
  role: string;
  signedInAt: string;
};

const KEY = "arc-session";

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function signIn(name: string, role: string): Session {
  const session: Session = { name, role, signedInAt: new Date().toISOString() };
  window.localStorage.setItem(KEY, JSON.stringify(session));
  return session;
}

export function signOut(): void {
  window.localStorage.removeItem(KEY);
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]!.toUpperCase())
    .join("");
}
