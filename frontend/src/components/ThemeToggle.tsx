"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme";

// Sun/moon toggle — sits in the top bar / nav, matches the ghost button tone.
export function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className={[
        "flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted transition-colors",
        "hover:border-borderStrong hover:text-textSecondary",
        className ?? "",
      ].join(" ")}
    >
      {isDark ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
    </button>
  );
}
