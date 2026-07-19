"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import styles from "./PageState.module.scss";

/**
 * Shared route-level UI states (#238): one design for loading skeletons,
 * error cards, and empty states across all routes.
 *
 * Full-page by default (renders its own centered container); pass `inline`
 * to embed within an existing layout. Focus-visible outlines and
 * prefers-reduced-motion are handled globally in globals.scss.
 */

type Width = "narrow" | "wide" | "default";

function containerClass(width: Width = "default"): string {
  const widthClass = width === "narrow" ? styles.narrow : width === "wide" ? styles.wide : "";
  return `${styles.stateContainer} ${widthClass}`;
}

// ===== Loading =====

interface LoadingStateProps {
  /** Skeleton shape: stacked rows, card grid, prose block, or one large canvas */
  variant?: "list" | "cards" | "content" | "graph";
  width?: Width;
  /** Screen-reader label */
  label?: string;
  /** Render without the full-page container */
  inline?: boolean;
}

export function LoadingState({
  variant = "content",
  width,
  label = "Loading",
  inline = false,
}: LoadingStateProps) {
  const skeleton = (
    <div className={styles.skeleton} role="status" aria-label={label}>
      <div className={`${styles.skeletonBar} ${styles.skeletonTitle}`}></div>
      {variant === "list" && (
        <div className={styles.skeletonStack}>
          {[1, 2, 3].map((i) => (
            <div key={i} className={`${styles.skeletonBar} ${styles.skeletonItem}`}></div>
          ))}
        </div>
      )}
      {variant === "cards" && (
        <div className={styles.skeletonGrid}>
          {[1, 2, 3].map((i) => (
            <div key={i} className={`${styles.skeletonBar} ${styles.skeletonCard}`}></div>
          ))}
        </div>
      )}
      {variant === "content" && (
        <div className={`${styles.skeletonBar} ${styles.skeletonContent}`}></div>
      )}
      {variant === "graph" && (
        <div className={`${styles.skeletonBar} ${styles.skeletonCanvas}`}></div>
      )}
    </div>
  );

  if (inline) return skeleton;
  return <div className={containerClass(width)}>{skeleton}</div>;
}

// ===== Error =====

interface ErrorStateProps {
  message: string;
  /** Heading; full-page defaults to "Error", inline defaults to none */
  title?: string;
  backHref?: string;
  backLabel?: string;
  width?: Width;
  /** Render as a banner within an existing layout */
  inline?: boolean;
}

export function ErrorState({
  message,
  title,
  backHref,
  backLabel = "← Back",
  width,
  inline = false,
}: ErrorStateProps) {
  const heading = title ?? (inline ? undefined : "Error");

  const card = (
    <div className={styles.errorCard} role="alert">
      {heading && <h2 className={styles.errorTitle}>{heading}</h2>}
      <p className={styles.errorMessage}>{message}</p>
      {backHref && (
        <Link href={backHref} className={styles.backLink}>
          {backLabel}
        </Link>
      )}
    </div>
  );

  if (inline) return card;
  return <div className={containerClass(width)}>{card}</div>;
}

// ===== Empty =====

interface EmptyStateProps {
  message: ReactNode;
  title?: string;
  icon?: ReactNode;
  /** Renders a primary-styled action: a Link when actionHref is set, else a button */
  actionLabel?: string;
  actionHref?: string;
  onAction?: () => void;
  backHref?: string;
  backLabel?: string;
  width?: Width;
  /** Render within an existing layout */
  inline?: boolean;
}

export function EmptyState({
  message,
  title,
  icon,
  actionLabel,
  actionHref,
  onAction,
  backHref,
  backLabel = "← Back",
  width,
  inline = false,
}: EmptyStateProps) {
  const card = (
    <div className={styles.emptyCard}>
      {icon && (
        <div className={styles.emptyIcon} aria-hidden="true">
          {icon}
        </div>
      )}
      {title && <h3 className={styles.emptyTitle}>{title}</h3>}
      <p className={styles.emptyMessage}>{message}</p>
      {actionLabel &&
        (actionHref ? (
          <Link href={actionHref} className={styles.actionButton}>
            {actionLabel}
          </Link>
        ) : (
          <button onClick={onAction} className={styles.actionButton}>
            {actionLabel}
          </button>
        ))}
      {backHref && (
        <Link href={backHref} className={styles.backLink}>
          {backLabel}
        </Link>
      )}
    </div>
  );

  if (inline) return card;
  return <div className={containerClass(width)}>{card}</div>;
}
