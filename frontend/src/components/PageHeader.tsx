/**
 * PageHeader - shared header zone for Knowledge Base list pages (#282).
 *
 * One compact header pattern across Articles / Notes / Toolbox / Inspire:
 * the slate-blue gradient zone, a Space Grotesk title, an optional mono
 * "terminal readout" subtitle, an inline actions slot, and the decorative
 * AddressLights strip (#283). Per DESIGN.md the strip is the header's one
 * signature flourish, so everything around it stays quiet and dense.
 *
 * The Graph page keeps its own ultra-compact header but shares the same
 * --color-header-bg-* tokens, so it isn't built on this component.
 */

import Link from "next/link";
import AddressLights from "./AddressLights";
import OverflowMenu, { type OverflowMenuItem } from "./OverflowMenu";
import styles from "./PageHeader.module.scss";

interface PageHeaderProps {
  /** Page title, rendered as the h1. */
  title: string;
  /** Optional mono metadata line (counts, cross-links). */
  subtitle?: React.ReactNode;
  /** Breadcrumb element, e.g. <Breadcrumb section="notes" toHub />. */
  breadcrumb?: React.ReactNode;
  /** Right-aligned action controls (buttons/links). */
  actions?: React.ReactNode;
  /** Short inline count shown next to the title on phones ("Notes · 90"). */
  count?: React.ReactNode;
  /** Phones: compact square icon button in the title row (the page's primary action). */
  primaryAction?: {
    label: string;
    href?: string;
    onClick?: () => void;
    icon: React.ReactNode;
  };
  /** Phones: secondary actions tucked into a "⋯" overflow menu. */
  menuActions?: OverflowMenuItem[];
  /** Show the decorative AddressLights strip. Default true. */
  showLights?: boolean;
}

export default function PageHeader({
  title,
  subtitle,
  breadcrumb,
  actions,
  count,
  primaryAction,
  menuActions,
  showLights = true,
}: PageHeaderProps) {
  // Opting in to any mobile prop switches ≤640px to the one-row compact
  // header (#296). Pages that pass none (Inspire) keep the full header.
  const compact = count !== undefined || Boolean(primaryAction) || Boolean(menuActions?.length);
  const hasMobileActions = Boolean(primaryAction) || Boolean(menuActions?.length);

  return (
    <header className={styles.header} data-compact={compact || undefined}>
      <div className={styles.headerContent}>
        {breadcrumb && <div className={styles.breadcrumb}>{breadcrumb}</div>}
        <div className={styles.titleRow}>
          <div className={styles.titleSection}>
            <h1 className={styles.title}>
              {title}
              {count !== undefined && (
                <span className={styles.count}>
                  <span aria-hidden="true"> &middot; </span>
                  {count}
                </span>
              )}
            </h1>
            {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
          </div>
          {actions && (
            <div className={styles.actions} data-replaced={hasMobileActions || undefined}>
              {actions}
            </div>
          )}
          {hasMobileActions && (
            <div className={styles.mobileActions}>
              {primaryAction &&
                (primaryAction.href ? (
                  <Link
                    href={primaryAction.href}
                    className={styles.primaryIcon}
                    aria-label={primaryAction.label}
                    onClick={primaryAction.onClick}
                  >
                    {primaryAction.icon}
                  </Link>
                ) : (
                  <button
                    type="button"
                    className={styles.primaryIcon}
                    aria-label={primaryAction.label}
                    onClick={primaryAction.onClick}
                  >
                    {primaryAction.icon}
                  </button>
                ))}
              {menuActions && menuActions.length > 0 && <OverflowMenu items={menuActions} />}
            </div>
          )}
        </div>
        {showLights && (
          <div className={styles.lightsRow}>
            <AddressLights />
          </div>
        )}
      </div>
    </header>
  );
}
