"use client";

/**
 * Advisory card for the #146 Phase 2 writing-partner commands (challenge /
 * gaps / contradictions). Unlike Phase 1's transforms, these commands never
 * touch the document - the result is commentary with citations, rendered
 * here and left entirely up to the user to act on ("Insert as quote") or
 * discard ("Dismiss"). NoteEditor.tsx owns all state and streaming; this
 * component is a pure presentational shell so it's cheaply testable in
 * isolation.
 *
 * Markdown prose is rendered as raw text (white-space: pre-wrap), matching
 * SynthesisView.tsx (#166) - the app doesn't run a markdown parser over
 * streamed AI prose anywhere else, so this doesn't introduce a new pattern.
 * Citations reuse SourceList.tsx verbatim; the backend's source shape
 * (id/type/title/content/score) was matched to it deliberately.
 */

import { useEffect, useRef, useState } from "react";
import SourceList, { type Source } from "@/components/SourceList";
import styles from "./NoteEditor.module.scss";

export interface WritingPartnerCardProps {
  /** Command label shown as the card heading, e.g. "Challenge this assumption". */
  label: string;
  /** Anchor point (from CodeMirror's coordsAtPos), pre-clamp. */
  anchor: { top: number; left: number };
  /** Accumulated markdown prose streamed so far (or the non-streaming result). */
  prose: string;
  /** True while a stream is in flight and more tokens may still arrive. */
  streaming: boolean;
  /** True for the zero-retrieval case: prose is a fixed honest message, not
   * an LLM output - render as information, not as an error. */
  degraded: boolean;
  sources: Source[];
  /** Set when both streaming and the non-streaming fallback failed. */
  errorMessage: string | null;
  onInsertQuote: () => void;
  onDismiss: () => void;
}

const CARD_MARGIN = 8;

export default function WritingPartnerCard({
  label,
  anchor,
  prose,
  streaming,
  degraded,
  sources,
  errorMessage,
  onInsertQuote,
  onDismiss,
}: WritingPartnerCardProps) {
  const cardRef = useRef<HTMLDivElement | null>(null);
  const [position, setPosition] = useState(anchor);
  const [copied, setCopied] = useState(false);

  // Re-clamp on every render that could change the card's size (new tokens,
  // sources landing, error state) so it never overflows the viewport.
  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let left = anchor.left;
    let top = anchor.top;

    if (left + rect.width + CARD_MARGIN > viewportWidth) {
      left = Math.max(CARD_MARGIN, viewportWidth - rect.width - CARD_MARGIN);
    }
    if (top + rect.height + CARD_MARGIN > viewportHeight) {
      // Flip above the anchor point when it would overflow the bottom edge;
      // fall back to clamping against the bottom if there isn't room above
      // either (e.g. a very tall card on a short viewport).
      const flippedTop = anchor.top - rect.height - CARD_MARGIN;
      top =
        flippedTop >= CARD_MARGIN
          ? flippedTop
          : Math.max(CARD_MARGIN, viewportHeight - rect.height - CARD_MARGIN);
    }

    setPosition({ top, left });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anchor, prose, sources.length, streaming, errorMessage, degraded]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onDismiss();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onDismiss]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(prose);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API can fail silently (permissions, insecure context) -
      // not worth surfacing as an error; the user can still select the text.
    }
  };

  const hasProse = prose.length > 0;
  const canAct = !streaming && !errorMessage && hasProse;

  return (
    <div
      ref={cardRef}
      className={styles.partnerCard}
      style={{ top: `${position.top}px`, left: `${position.left}px` }}
      role="dialog"
      aria-label={label}
    >
      <div className={styles.partnerCardHeader}>
        <span className={styles.partnerCardLabel}>{label}</span>
      </div>

      <div className={styles.partnerCardBody}>
        {errorMessage ? (
          <div className={styles.partnerCardError}>{errorMessage}</div>
        ) : (
          <>
            {!hasProse && streaming && (
              <div className={styles.partnerCardPending}>
                <span className={styles.slashPendingDot} aria-hidden="true" />
                Thinking…
              </div>
            )}
            {hasProse && (
              <div className={styles.partnerCardProse}>
                {prose}
                {streaming && (
                  <span className={styles.synthesisStreamingCursorLocal} aria-hidden="true" />
                )}
              </div>
            )}
            {degraded && !streaming && (
              <div className={styles.partnerCardDegradedNote}>
                Nothing in the knowledge base yet to check this against.
              </div>
            )}
          </>
        )}

        {sources.length > 0 && <SourceList sources={sources} />}
      </div>

      <div className={styles.partnerCardActions}>
        <button
          type="button"
          className={styles.partnerCardButtonPrimary}
          onClick={onInsertQuote}
          disabled={!canAct}
        >
          Insert as quote
        </button>
        <button
          type="button"
          className={styles.partnerCardButton}
          onClick={handleCopy}
          disabled={!canAct}
        >
          {copied ? "Copied ✓" : "Copy"}
        </button>
        <button type="button" className={styles.partnerCardButton} onClick={onDismiss}>
          Dismiss
        </button>
      </div>
    </div>
  );
}
