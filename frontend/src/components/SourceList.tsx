"use client";

/**
 * Shared source-citation card list, used by both the Ask/Search message
 * list and the Synthesis view (#166). Extracted from AIPanel.tsx so the
 * id/type/title/content/score rendering (links to /knowledge-base/articles/
 * or /knowledge-base/notes/) exists in exactly one place.
 */

import styles from "./AIPanel.module.scss";

export interface Source {
  id: number | string;
  type?: "article" | "note";
  title: string;
  content: string;
  score?: number;
}

export default function SourceList({ sources }: { sources: Source[] }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className={styles.sources}>
      {sources.map((source, idx) => {
        const resourcePath =
          source.type === "article"
            ? `/knowledge-base/articles/${source.id}`
            : source.type === "note"
              ? `/knowledge-base/notes/${source.id}`
              : null;

        return (
          <div key={`${source.id}-${idx}`} className={styles.sourceCard}>
            <div className={styles.sourceHeader}>
              <div className={styles.sourceInfo}>
                <span className={styles.sourceTitle}>
                  <span className={styles.sourceType} data-type={source.type}>
                    {source.type === "article" ? "ART" : source.type === "note" ? "NOTE" : "REF"}
                  </span>{" "}
                  {source.title || `Document ${source.id}`}
                </span>
                {source.score && (
                  <span className={styles.sourceScore}>{source.score.toFixed(3)}</span>
                )}
              </div>
              {resourcePath && (
                <a
                  href={resourcePath}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.sourceLink}
                >
                  View →
                </a>
              )}
            </div>
            <div className={styles.sourceContent}>{source.content}</div>
          </div>
        );
      })}
    </div>
  );
}
