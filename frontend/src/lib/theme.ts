"use client";

import { useEffect, useState } from "react";

// Class-based theme switch: localStorage override, falling back to the OS
// preference. The blocking script in layout.tsx applies the class before
// paint; this module keeps in-page toggles in sync with it.
export type Theme = "light" | "dark";

const KEY = "arc-theme";

export function getStoredTheme(): Theme | null {
  if (typeof window === "undefined") return null;
  const value = window.localStorage.getItem(KEY);
  return value === "light" || value === "dark" ? value : null;
}

export function systemTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.style.colorScheme = theme;
}

export function setTheme(theme: Theme): void {
  window.localStorage.setItem(KEY, theme);
  applyTheme(theme);
}

export function useTheme(): [Theme, (theme: Theme) => void] {
  const [theme, setThemeState] = useState<Theme>("dark");

  useEffect(() => {
    setThemeState(getStoredTheme() ?? systemTheme());
  }, []);

  const update = (next: Theme) => {
    setThemeState(next);
    setTheme(next);
  };

  return [theme, update];
}
