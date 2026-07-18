/**
 * useDelight - read/write access to Delight Mode (#240).
 *
 * Mirrors useTheme: the choice lives in localStorage "delight" and is
 * applied to <html data-delight> by an inline script in the root layout
 * before first paint. All delight styles/behavior are scoped under
 * :root[data-delight="on"], so work mode pays zero cost.
 */

"use client";

import { useEffect, useState } from "react";

export function isDelightOn(): boolean {
  return document.documentElement.dataset.delight === "on";
}

export function useDelight(): { delight: boolean | null; setDelight: (on: boolean) => void } {
  const [delight, setDelightState] = useState<boolean | null>(null);

  useEffect(() => {
    setDelightState(isDelightOn());
  }, []);

  const setDelight = (on: boolean): void => {
    if (on) {
      document.documentElement.dataset.delight = "on";
    } else {
      delete document.documentElement.dataset.delight;
    }
    try {
      localStorage.setItem("delight", on ? "on" : "off");
    } catch {
      // Private browsing or blocked storage - the choice just won't persist
    }
    setDelightState(on);
  };

  return { delight, setDelight };
}
