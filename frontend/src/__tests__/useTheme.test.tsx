import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { useTheme } from "../hooks/useTheme";

describe("useTheme", () => {
  beforeEach(() => {
    delete document.documentElement.dataset.theme;
    localStorage.clear();
  });

  it("resolves explicit data-theme after mount", async () => {
    document.documentElement.dataset.theme = "dark";
    const { result } = renderHook(() => useTheme());
    await waitFor(() => expect(result.current.theme).toBe("dark"));
  });

  it("falls back to light when no explicit theme and no dark OS preference", async () => {
    // jsdom matchMedia (mocked in vitest.setup.ts) reports no dark preference
    const { result } = renderHook(() => useTheme());
    await waitFor(() => expect(result.current.theme).toBe("light"));
  });

  it("setTheme updates state, dataset, and localStorage", async () => {
    const { result } = renderHook(() => useTheme());
    await waitFor(() => expect(result.current.theme).not.toBeNull());

    act(() => result.current.setTheme("dark"));

    expect(result.current.theme).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem("theme")).toBe("dark");
  });
});
