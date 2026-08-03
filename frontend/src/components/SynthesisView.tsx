"use client";

/**
 * Deep-synthesis tab (#166): "deep synthesis" mode of the existing /api/ask
 * pipeline - wide retrieval across the knowledge base plus a structured
 * markdown synthesis (Key Concepts / Your Positions / Gaps & Open Questions).
 *
 * Mirrors the structure of SuggestView (AIPanel.tsx): a self-contained view
 * that stays mounted while the panel is open so results survive tab
 * switches, with its own loading/error/streaming state.
 */

import { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Warning } from "@phosphor-icons/react";
import { logger } from "@/lib/logger";
import { streamSSE } from "@/lib/sse";
import { saveDraft } from "@/lib/draft";
import SourceList, { type Source } from "@/components/SourceList";
import styles from "./AIPanel.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 120000; // CPU inference can be slow, same budget as Ask

type SynthesisEvent =
  | { type: "sources"; sources: Source[] }
  | { type: "token"; text: string }
  | { type: "complete" }
  | { type: "error"; message?: string };

interface SynthesisViewProps {
  active: boolean;
}

export default function SynthesisView({ active }: SynthesisViewProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [synthesis, setSynthesis] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [saved, setSaved] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const runNonStreaming = useCallback(async (submittedQueryValue: string) => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

      const response = await fetch(`${API_URL}/api/synthesize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: submittedQueryValue }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (response.status === 503) {
        setUnavailable(true);
        setLoading(false);
        return;
      }
      if (!response.ok) {
        throw new Error(`Request failed: ${response.statusText}`);
      }

      const data = await response.json();
      setSources(data.sources || []);
      if (data.degraded || !data.synthesis) {
        setError("The AI didn't return a synthesis. Try a different query, or try again.");
      } else {
        setSynthesis(data.synthesis);
      }
    } catch (err) {
      logger.error("Synthesis (non-streaming) failed", err);
      setError(err instanceof Error ? err.message : "Failed to generate synthesis.");
    } finally {
      setLoading(false);
    }
  }, []);

  const performSynthesis = useCallback(
    async (trimmed: string) => {
      if (!trimmed || loading) return;

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setSubmittedQuery(trimmed);
      setLoading(true);
      setError(null);
      setUnavailable(false);
      setSaved(false);
      setSynthesis("");
      setSources([]);

      // EventSource can't do POST, so this always goes through the fetch-based
      // reader. If streaming itself is unusable in this environment, or the
      // stream fails outright, fall back to the non-streaming endpoint.
      if (typeof ReadableStream === "undefined") {
        await runNonStreaming(trimmed);
        return;
      }

      let streamedAnyToken = false;
      let sawError = false;

      await streamSSE<SynthesisEvent>(`${API_URL}/api/synthesize/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
        signal: controller.signal,
        onEvent: (event) => {
          switch (event.type) {
            case "sources":
              setSources(event.sources || []);
              break;
            case "token":
              streamedAnyToken = true;
              setSynthesis((prev) => prev + event.text);
              break;
            case "complete":
              setLoading(false);
              break;
            case "error":
              sawError = true;
              logger.warn("Synthesis stream reported an error", { message: event.message });
              break;
          }
        },
        onError: (err) => {
          sawError = true;
          logger.warn("Synthesis stream transport error, falling back", err);
        },
        onDone: () => {
          setLoading(false);
        },
      });

      // Degrade gracefully: a stream that errored (transport or application)
      // without producing any prose falls back to the non-streaming endpoint,
      // which may succeed independently (e.g. a mid-stream generation hiccup).
      if (sawError && !streamedAnyToken) {
        setSynthesis("");
        setLoading(true);
        await runNonStreaming(trimmed);
      }
    },
    [loading, runNonStreaming]
  );

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      void performSynthesis(query.trim());
    },
    [query, performSynthesis]
  );

  const handleRetry = useCallback(() => {
    void performSynthesis(submittedQuery);
  }, [performSynthesis, submittedQuery]);

  const handleSaveDraft = useCallback(() => {
    if (!synthesis) return;
    saveDraft({
      title: `Synthesis: ${submittedQuery}`,
      content: synthesis,
      tags: "synthesis",
      isReference: false,
    });
    setSaved(true);
    logger.info("Synthesis saved as note draft", { query: submittedQuery });
    router.push("/knowledge-base/notes/new");
  }, [synthesis, submittedQuery, router]);

  const hasResult = synthesis.length > 0 || sources.length > 0;

  return (
    <div className={styles.synthesisView}>
      <div className={styles.synthesisResults}>
        {!active ? null : !hasResult && !loading && !error && !unavailable ? (
          <div className={styles.emptyState}>
            <p className={styles.emptyTitle}>Deep Synthesis</p>
            <p className={styles.emptyDescription}>
              Ask a broad question like &quot;Synthesize everything I know about incident
              response.&quot; I&apos;ll pull from up to 12 notes and articles and produce a
              structured summary with key concepts, your positions, and gaps in your knowledge base
              - with citations.
            </p>
          </div>
        ) : null}

        {unavailable && (
          <div className={styles.errorBanner}>
            AI synthesis is not available. The LLM is not running or not configured.
          </div>
        )}

        {error && !unavailable && (
          <div className={styles.errorBanner}>
            {error}
            <button onClick={handleRetry} className={styles.retryButton}>
              Retry
            </button>
          </div>
        )}

        {loading && !synthesis && (
          <div className={styles.streamingProgress}>
            <div className={styles.suggestLoadingContent}>
              <div className={styles.spinner}></div>
              <div className={styles.progressText}>
                <span className={styles.progressStatus}>
                  Gathering sources and generating synthesis...
                </span>
                {sources.length > 0 && (
                  <span className={styles.progressCounts}>
                    {sources.length} source{sources.length !== 1 ? "s" : ""} found
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {synthesis && (
          <>
            <div className={styles.synthesisOutput}>
              {synthesis}
              {loading && <span className={styles.synthesisStreamingCursor} />}
            </div>

            {!loading && (
              <div className={styles.synthesisActions}>
                <button
                  onClick={handleSaveDraft}
                  className={styles.saveDraftButton}
                  disabled={saved}
                >
                  {saved ? "Saved as draft ✓" : "Save as note draft"}
                </button>
              </div>
            )}
          </>
        )}

        {sources.length > 0 && <SourceList sources={sources} />}

        {loading && (
          <div className={styles.performanceNotice}>
            <p className={styles.noticeTitle}>
              <Warning size={14} aria-hidden="true" /> This can take a while
            </p>
            <p className={styles.noticeDescription}>
              Synthesis pulls from many documents and can take 30-120+ seconds, especially on
              CPU-only infrastructure.
            </p>
          </div>
        )}
      </div>

      <div className={styles.inputArea}>
        <form onSubmit={handleSubmit} className={styles.inputForm}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Synthesize everything I know about..."
            className={styles.input}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !query.trim()} className={styles.submitButton}>
            {loading ? "..." : "Synthesize"}
          </button>
        </form>
      </div>
    </div>
  );
}
