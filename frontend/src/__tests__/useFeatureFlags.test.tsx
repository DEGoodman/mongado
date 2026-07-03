/**
 * Tests for useFeatureFlags hook
 *
 * Tests cover:
 * - Fetching runtime flags from the backend status endpoint
 * - Defaulting to disabled on fetch failure
 * - Sharing one fetch across consumers (module-level store)
 * - applyFeatureFlag updating the store directly
 */

import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// The hook keeps module-level state, so re-import a fresh copy per test
async function freshHook() {
  vi.resetModules();
  return import("../hooks/useFeatureFlags");
}

describe("useFeatureFlags", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads flags from the backend status endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ llm_features_enabled: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { useFeatureFlags } = await freshHook();
    const { result } = renderHook(() => useFeatureFlags());

    expect(result.current.loaded).toBe(false);
    expect(result.current.llmFeaturesEnabled).toBe(false);

    await waitFor(() => expect(result.current.loaded).toBe(true));
    expect(result.current.llmFeaturesEnabled).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/$/),
      expect.objectContaining({ cache: "no-store" })
    );
  });

  it("defaults to disabled when the fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    const { useFeatureFlags } = await freshHook();
    const { result } = renderHook(() => useFeatureFlags());

    await waitFor(() => expect(result.current.loaded).toBe(true));
    expect(result.current.llmFeaturesEnabled).toBe(false);
  });

  it("shares a single fetch across multiple consumers", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ llm_features_enabled: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { useFeatureFlags } = await freshHook();
    const first = renderHook(() => useFeatureFlags());
    const second = renderHook(() => useFeatureFlags());

    await waitFor(() => expect(first.result.current.loaded).toBe(true));
    await waitFor(() => expect(second.result.current.loaded).toBe(true));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(second.result.current.llmFeaturesEnabled).toBe(true);
  });

  it("applyFeatureFlag updates subscribed components without a fetch", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ llm_features_enabled: false }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { useFeatureFlags, applyFeatureFlag } = await freshHook();
    const { result } = renderHook(() => useFeatureFlags());
    await waitFor(() => expect(result.current.loaded).toBe(true));
    expect(result.current.llmFeaturesEnabled).toBe(false);

    applyFeatureFlag("llm_features", true);
    await waitFor(() => expect(result.current.llmFeaturesEnabled).toBe(true));

    // Unknown flag names are ignored
    applyFeatureFlag("nonexistent_flag", false);
    expect(result.current.llmFeaturesEnabled).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
