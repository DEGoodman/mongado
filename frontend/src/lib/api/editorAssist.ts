/**
 * API client for editor slash commands (#146 Phase 1).
 *
 * The backend gates both endpoints on AdminUser (see backend/routers/ai.py) -
 * unlike /api/ask, which is intentionally open. That's why this module uses
 * the fetch()-based streamSSE reader (frontend/src/lib/sse.ts) rather than
 * EventSource: only fetch() can attach the Authorization header these
 * endpoints require.
 */

import { getAuthHeaders, apiPost } from "@/lib/api/client";
import { streamSSE } from "@/lib/sse";
import type { SlashCommandName } from "@/lib/slashCommands";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface EditorAssistRequestBody {
  command: SlashCommandName;
  text: string;
  note_title?: string;
  note_content?: string;
  note_id?: string;
}

export interface EditorLinkSuggestion {
  note_id: string;
  title: string;
  reason: string;
  confidence?: number;
}

/** Citation shape for writing-partner commands (#146 Phase 2) - matches
 * SourceList.tsx's `Source` prop exactly; the backend was built to this
 * shape deliberately so the component can be reused as-is. */
export interface EditorAssistSource {
  id: number | string;
  type?: "article" | "note";
  title: string;
  content: string;
  score?: number;
}

export type EditorAssistEvent =
  | { type: "sources"; sources: EditorAssistSource[] }
  | { type: "token"; text: string }
  | ({ type: "link" } & EditorLinkSuggestion)
  | { type: "complete"; degraded?: boolean }
  | { type: "error"; message?: string };

export interface EditorAssistResponse {
  command: string;
  result?: string | null;
  suggestions?: EditorLinkSuggestion[] | null;
  sources?: EditorAssistSource[] | null;
  degraded: boolean;
}

/** Stream a slash-command result. Resolves once the stream ends (normally,
 * on error, or on abort) - failures are reported via onError/error events,
 * not thrown, so callers can fall back to runEditorAssist. */
export async function streamEditorAssist(
  body: EditorAssistRequestBody,
  handlers: {
    onEvent: (event: EditorAssistEvent) => void;
    onError?: (error: Error) => void;
    onDone?: () => void;
    signal?: AbortSignal;
  }
): Promise<void> {
  await streamSSE<EditorAssistEvent>(`${API_URL}/api/editor/assist/stream`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
    ...handlers,
  });
}

/** Non-streaming fallback for when streaming itself is unusable or fails
 * without producing any output. */
export async function runEditorAssist(
  body: EditorAssistRequestBody
): Promise<EditorAssistResponse> {
  return apiPost<EditorAssistResponse>("/api/editor/assist", body);
}
