"use client";

import { useEffect, useState } from "react";

/**
 * Resolves the active theme the same way themes.scss does: an explicit
 * data-theme on <html> wins (set by ThemeToggle), otherwise the OS
 * preference applies. Tracks both the toggle and OS changes live.
 */
export function useResolvedTheme(): "light" | "dark" {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    const resolve = (): "light" | "dark" => {
      const explicit = document.documentElement.dataset.theme;
      if (explicit === "dark" || explicit === "light") return explicit;
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    };

    setTheme(resolve());

    const observer = new MutationObserver(() => setTheme(resolve()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setTheme(resolve());
    mq.addEventListener("change", onChange);

    return () => {
      observer.disconnect();
      mq.removeEventListener("change", onChange);
    };
  }, []);

  return theme;
}
