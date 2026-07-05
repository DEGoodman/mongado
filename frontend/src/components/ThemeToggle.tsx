/**
 * ThemeToggle - switches between light and dark ("phosphor") themes.
 *
 * Used standalone on the homepage (which has no TopNavigation). Theme
 * resolution/persistence lives in the useTheme hook.
 */

"use client";

import { Moon, Sun } from "@phosphor-icons/react";
import { useTheme } from "@/hooks/useTheme";
import styles from "./ThemeToggle.module.scss";

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const toggle = () => {
    setTheme(theme === "dark" ? "light" : "dark");
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
