/**
 * Tests for the generic fetch()-based SSE reader (src/lib/sse.ts).
 *
 * Covers what #146 (slash commands) will also depend on: multiple events in
 * one chunk, an event split across two chunks, [DONE]/terminal handling,
 * and abort behavior.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { streamSSE } from "@/lib/sse";

/** Build a Response whose body streams the given raw string chunks. */
function streamingResponse(chunks: string[], init?: { ok?: boolean; status?: number }): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });

  return {
    ok: init?.ok ?? true,
    status: init?.status ?? 200,
    statusText: "OK",
    body,
  } as unknown as Response;
}

describe("streamSSE", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("parses multiple events delivered in a single chunk", async () => {
    const events: unknown[] = [];
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        streamingResponse([`data: {"type":"a","n":1}\n\ndata: {"type":"b","n":2}\n\n`])
      );
    vi.stubGlobal("fetch", fetchMock);

    await streamSSE("/api/thing", { onEvent: (e) => events.push(e) });

    expect(events).toEqual([
      { type: "a", n: 1 },
      { type: "b", n: 2 },
    ]);
  });

  it("parses an event whose frame is split across two chunks", async () => {
    const events: unknown[] = [];
    const fetchMock = vi.fn().mockResolvedValue(
      streamingResponse([
        `data: {"type":"tok`, // split mid-JSON-value
        `en","text":"hello"}\n\n`,
      ])
    );
    vi.stubGlobal("fetch", fetchMock);

    await streamSSE("/api/thing", { onEvent: (e) => events.push(e) });

    expect(events).toEqual([{ type: "token", text: "hello" }]);
  });

  it("parses an event whose blank-line frame boundary is split across chunks", async () => {
    const events: unknown[] = [];
    const fetchMock = vi
      .fn()
      .mockResolvedValue(streamingResponse([`data: {"type":"a"}\n`, `\ndata: {"type":"b"}\n\n`]));
    vi.stubGlobal("fetch", fetchMock);

    await streamSSE("/api/thing", { onEvent: (e) => events.push(e) });

    expect(events).toEqual([{ type: "a" }, { type: "b" }]);
  });

  it("stops at a [DONE] sentinel and calls onDone without emitting it as an event", async () => {
    const events: unknown[] = [];
    const doneFn = vi.fn();
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        streamingResponse([`data: {"type":"a"}\n\ndata: [DONE]\n\ndata: {"type":"never"}\n\n`])
      );
    vi.stubGlobal("fetch", fetchMock);

    await streamSSE("/api/thing", { onEvent: (e) => events.push(e), onDone: doneFn });

    expect(events).toEqual([{ type: "a" }]);
    expect(doneFn).toHaveBeenCalledTimes(1);
  });

  it("calls onDone when the stream ends normally without a [DONE] sentinel", async () => {
    const doneFn = vi.fn();
    const fetchMock = vi
      .fn()
      .mockResolvedValue(streamingResponse([`data: {"type":"complete"}\n\n`]));
    vi.stubGlobal("fetch", fetchMock);

    await streamSSE("/api/thing", { onEvent: vi.fn(), onDone: doneFn });

    expect(doneFn).toHaveBeenCalledTimes(1);
  });

  it("flushes a final frame that has no trailing blank line", async () => {
    const events: unknown[] = [];
    const fetchMock = vi.fn().mockResolvedValue(streamingResponse([`data: {"type":"last"}`]));
    vi.stubGlobal("fetch", fetchMock);

    await streamSSE("/api/thing", { onEvent: (e) => events.push(e) });

    expect(events).toEqual([{ type: "last" }]);
  });

  it("calls onError and skips onDone when the response is not ok", async () => {
    const errorFn = vi.fn();
    const doneFn = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue(streamingResponse([], { ok: false, status: 503 }));
    vi.stubGlobal("fetch", fetchMock);

    await streamSSE("/api/thing", { onEvent: vi.fn(), onError: errorFn, onDone: doneFn });

    expect(errorFn).toHaveBeenCalledWith(expect.any(Error));
    expect(doneFn).not.toHaveBeenCalled();
  });

  it("does not call onError when fetch rejects due to an aborted signal", async () => {
    const errorFn = vi.fn();
    const controller = new AbortController();
    const abortError = new DOMException("The operation was aborted.", "AbortError");
    const fetchMock = vi.fn().mockRejectedValue(abortError);
    vi.stubGlobal("fetch", fetchMock);
    controller.abort();

    await streamSSE("/api/thing", {
      onEvent: vi.fn(),
      onError: errorFn,
      signal: controller.signal,
    });

    expect(errorFn).not.toHaveBeenCalled();
  });

  it("passes method, headers, body, and signal through to fetch", async () => {
    const fetchMock = vi.fn().mockResolvedValue(streamingResponse([]));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    await streamSSE("/api/thing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "x" }),
      signal: controller.signal,
      onEvent: vi.fn(),
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/thing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "x" }),
      signal: controller.signal,
    });
  });

  it("defaults to POST when no method is given", async () => {
    const fetchMock = vi.fn().mockResolvedValue(streamingResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await streamSSE("/api/thing", { onEvent: vi.fn() });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
  });
});
