/**
 * Generic fetch()-based Server-Sent Events (SSE) reader.
 *
 * `EventSource` cannot send a POST body or custom headers, which rules it
 * out for endpoints that need a request body (e.g. a long query/prompt that
 * won't fit a querystring - see /api/synthesize/stream, #166). This module
 * reads an SSE stream from any `fetch()` response body instead: it parses
 * `data: ...\n\n` frames out of the raw byte stream, tolerating frames that
 * are split across chunk boundaries, and JSON-decodes each frame's payload.
 *
 * Kept intentionally small and generic (no synthesis-specific types) so a
 * later caller (#146, slash commands) can reuse it verbatim for a different
 * event shape - just pass a different `T`.
 */

import { logger } from "@/lib/logger";

const sseLogger = logger.withContext("SSE");

/** Sentinel some SSE producers send to mark the end of a stream. */
const DONE_SENTINEL = "[DONE]";

export interface StreamSSEOptions<T> {
  /** HTTP method; defaults to "POST" since that's the reason this exists. */
  method?: string;
  headers?: Record<string, string>;
  body?: BodyInit;
  signal?: AbortSignal;
  /** Called once per parsed event, in stream order. */
  onEvent: (event: T) => void;
  /** Called on a request/parse/stream failure. Not called on intentional abort. */
  onError?: (error: Error) => void;
  /** Called once the stream ends normally (server closed the connection, or [DONE] seen). */
  onDone?: () => void;
}

/**
 * Extract the `data:` payload from one SSE frame (the text between two
 * `\n\n` boundaries). Per the SSE spec, a frame may have multiple `data:`
 * lines, which are joined with `\n`. Lines that aren't `data:` (e.g. `event:`,
 * `id:`, comments starting with `:`) are ignored - this reader only needs
 * the data payload, matching what the backend's `format_sse` emits.
 */
function extractData(frame: string): string | null {
  const dataLines = frame
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice("data:".length).replace(/^ /, ""));

  if (dataLines.length === 0) {
    return null;
  }
  return dataLines.join("\n");
}

/**
 * Stream Server-Sent Events from a `fetch()` request (typically POST).
 *
 * Resolves once the stream ends (normally, via [DONE], or via abort);
 * rejects only in unexpected caller-error situations (it otherwise routes
 * failures through `onError` so callers can degrade gracefully rather than
 * needing a try/catch around every call site).
 */
export async function streamSSE<T = unknown>(
  url: string,
  options: StreamSSEOptions<T>
): Promise<void> {
  const { method = "POST", headers, body, signal, onEvent, onError, onDone } = options;

  let response: Response;
  try {
    response = await fetch(url, { method, headers, body, signal });
  } catch (err) {
    if (signal?.aborted) return;
    onError?.(err instanceof Error ? err : new Error(String(err)));
    return;
  }

  if (!response.ok || !response.body) {
    onError?.(new Error(`SSE request failed: ${response.status} ${response.statusText}`));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const handleFrame = (frame: string): boolean => {
    // Returns false if this frame signals stream termination.
    const data = extractData(frame);
    if (data === null) return true;
    if (data === DONE_SENTINEL) return false;

    try {
      onEvent(JSON.parse(data) as T);
    } catch (err) {
      sseLogger.warn("Failed to parse SSE event payload", { data, error: err });
    }
    return true;
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Frames are separated by a blank line. The last (possibly partial)
      // frame is kept in the buffer for the next chunk - this is what
      // handles an event split across two chunk boundaries.
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        if (!handleFrame(frame)) {
          onDone?.();
          return;
        }
      }
    }

    // Flush a final frame if the stream ended without a trailing blank line.
    if (buffer.trim()) {
      handleFrame(buffer);
    }

    onDone?.();
  } catch (err) {
    if (signal?.aborted) {
      onDone?.();
      return;
    }
    onError?.(err instanceof Error ? err : new Error(String(err)));
  }
}
