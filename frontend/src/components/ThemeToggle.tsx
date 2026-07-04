/**
 * ThemeToggle - switches between light and dark ("phosphor") themes.
 *
 * Resolution order: explicit choice (localStorage "theme") wins, otherwise
 * the OS preference applies. An inline script in the root layout applies the
 * stored choice before first paint, so there is no flash of the wrong theme.
 */

"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "@phosphor-icons/react";
import styles from "./ThemeToggle.module.scss";

type Theme = "light" | "dark";

function resolveInitialTheme(): Theme {
  const explicit = document.documentElement.dataset.theme;
  if (explicit === "light" || explicit === "dark") return explicit;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function ThemeToggle() {
  // null until mounted - the server doesn't know the theme
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    setTheme(resolveInitialTheme());
  }, []);

  const toggle = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Private browsing or blocked storage - the choice just won't persist
    }
    setTheme(next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      className={styles.toggle}
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
    >
      {/* Render both and pick via CSS-free state to avoid hydration mismatch */}
      {theme === "dark" ? (
        <Sun size={18} aria-hidden="true" />
      ) : (
        <Moon size={18} aria-hidden="true" />
      )}
    </button>
  );
}
