/**
 * useTheme - read/write access to the light/dark theme.
 *
 * Resolution order: explicit choice (localStorage "theme", applied to
 * <html data-theme> by an inline script in the root layout before first
 * paint) wins, otherwise the OS preference applies. `theme` is null until
 * mounted because the server doesn't know the theme.
 *
 * For read-only live tracking (incl. OS changes), see useResolvedTheme.
 */

"use client";

import { useEffect, useState } from "react";

export type Theme = "light" | "dark";

function resolveInitialTheme(): Theme {
  const explicit = document.documentElement.dataset.theme;
  if (explicit === "light" || explicit === "dark") return explicit;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function useTheme(): { theme: Theme | null; setTheme: (next: Theme) => void } {
  const [theme, setThemeState] = useState<Theme | null>(null);

  useEffect(() => {
    setThemeState(resolveInitialTheme());
  }, []);

  const setTheme = (next: Theme): void => {
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Private browsing or blocked storage - the choice just won't persist
    }
    setThemeState(next);
  };

  return { theme, setTheme };
}
