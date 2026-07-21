/**
 * Tests for the mutation-driven revalidation module (src/lib/api/cache.ts)
 *
 * Tests cover:
 * - First-ever fetch of a URL never forces a reload
 * - Repeated fetches with no invalidation never force a reload
 * - invalidate() forces a reload on the next fetch of a previously-fetched URL
 * - After that forced reload, generation is recorded so it doesn't reload again
 * - A URL invalidated before its first-ever fetch still isn't forced to reload
 * - Non-ok responses don't record generation, so they still revalidate next time
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { revalidatingFetch, invalidate, __resetForTests } from "@/lib/api/cache";

function okResponse() {
  return { ok: true, json: async () => ({}) } as Response;
}

function notOkResponse() {
  return { ok: false, status: 500, json: async () => ({}) } as Response;
}

describe("revalidatingFetch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    __resetForTests();
  });

  it("does not reload on the first-ever fetch of a URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse());
    vi.stubGlobal("fetch", fetchMock);

    await revalidatingFetch("/api/notes");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0];
    expect(init?.cache).toBeUndefined();
  });

  it("does not reload on a second fetch with no intervening invalidate()", async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse());
    vi.stubGlobal("fetch", fetchMock);

    await revalidatingFetch("/api/notes");
    await revalidatingFetch("/api/notes");

    expect(fetchMock).toHaveBeenCalledTimes(2);
    const [, secondInit] = fetchMock.mock.calls[1];
    expect(secondInit?.cache).toBeUndefined();
  });

  it("forces a reload on the next fetch of a previously-fetched URL after invalidate()", async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse());
    vi.stubGlobal("fetch", fetchMock);

    await revalidatingFetch("/api/notes");
    invalidate();
    await revalidatingFetch("/api/notes");

    const [, secondInit] = fetchMock.mock.calls[1];
    expect(secondInit?.cache).toBe("reload");
  });

  it("does not reload again on a subsequent fetch after the forced reload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse());
    vi.stubGlobal("fetch", fetchMock);

    await revalidatingFetch("/api/notes");
    invalidate();
    await revalidatingFetch("/api/notes"); // forced reload, generation recorded
    await revalidatingFetch("/api/notes"); // should not reload again

    const [, thirdInit] = fetchMock.mock.calls[2];
    expect(thirdInit?.cache).toBeUndefined();
  });

  it("does not reload a URL's first-ever fetch even if invalidate() ran earlier", async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse());
    vi.stubGlobal("fetch", fetchMock);

    invalidate();
    await revalidatingFetch("/api/notes/new-url");

    const [, init] = fetchMock.mock.calls[0];
    expect(init?.cache).toBeUndefined();

    // Only after the NEXT invalidate does this now-known URL reload
    invalidate();
    await revalidatingFetch("/api/notes/new-url");
    const [, secondInit] = fetchMock.mock.calls[1];
    expect(secondInit?.cache).toBe("reload");
  });

  it("does not record generation on a non-ok response, so it still revalidates next time", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(okResponse())
      .mockResolvedValueOnce(notOkResponse())
      .mockResolvedValue(okResponse());
    vi.stubGlobal("fetch", fetchMock);

    await revalidatingFetch("/api/notes");
    invalidate();

    const response = await revalidatingFetch("/api/notes");
    expect(response.ok).toBe(false);

    // Because the failed fetch never recorded a generation, the URL is still
    // considered stale (lastGeneration < generation) and reloads again.
    await revalidatingFetch("/api/notes");
    const [, thirdInit] = fetchMock.mock.calls[2];
    expect(thirdInit?.cache).toBe("reload");
  });
});
