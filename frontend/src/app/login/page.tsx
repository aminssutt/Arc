"use client";

import { LogIn } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { Button } from "@/components/Button";
import { ThemeToggle } from "@/components/ThemeToggle";
import { signIn } from "@/lib/session";

const ROLES = ["NOC Engineer", "Facility Manager", "Field Technician"];

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [name, setName] = useState("");
  const [role, setRole] = useState(ROLES[0]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    signIn(name.trim(), role);
    router.push(params.get("next") ?? "/monitor");
  };

  return (
    <form onSubmit={submit} className="flex w-full flex-col gap-5">
      <label className="flex flex-col gap-2">
        <span className="text-label font-medium text-textSecondary">Name</span>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Jamie Han"
          autoFocus
          className="h-11 rounded-md border border-border bg-background px-3 text-body text-text outline-none placeholder:text-muted focus:border-accent"
        />
      </label>
      <label className="flex flex-col gap-2">
        <span className="text-label font-medium text-textSecondary">Role</span>
        <div className="flex gap-2">
          {ROLES.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setRole(option)}
              className={[
                "flex-1 rounded-md border px-3 py-2.5 text-body-sm font-medium transition-colors",
                role === option
                  ? "border-accent bg-accentSubtle text-accentBright"
                  : "border-border bg-panelMuted text-muted hover:text-textSecondary",
              ].join(" ")}
            >
              {option}
            </button>
          ))}
        </div>
      </label>
      <Button
        type="submit"
        variant="primary"
        size="md"
        disabled={!name.trim()}
        leadingIcon={<LogIn className="h-4 w-4" />}
        className="w-full"
      >
        Enter control room
      </Button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-outer p-6">
      {/* Ambient glow, matching the landing hero */}
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[480px] w-[720px] -translate-x-1/2 rounded-full bg-accent/10 blur-3xl" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[320px] w-[480px] rounded-full bg-secondary/5 blur-3xl" />

      <ThemeToggle className="absolute right-6 top-6" />

      <div className="arc-fade-up relative flex w-full max-w-md flex-col items-center gap-8">
        <Link href="/">
          <Image src="/assets/arc-logo.svg" alt="Arc" width={120} height={20} />
        </Link>
        <div className="w-full rounded-xl border border-border bg-panel p-8 shadow-glow">
          <h1 className="text-h4 font-semibold text-text">Sign in</h1>
          <p className="mt-1 text-body-sm text-muted">
            Access the Arc control room and your action reports.
          </p>
          <div className="mt-6">
            <Suspense fallback={null}>
              <LoginForm />
            </Suspense>
          </div>
        </div>
        <p className="text-caption text-muted">
          Demo build — sessions are stored locally in this browser.
        </p>
      </div>
    </div>
  );
}
