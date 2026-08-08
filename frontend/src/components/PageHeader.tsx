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

import AddressLights from "./AddressLights";
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
  /** Show the decorative AddressLights strip. Default true. */
  showLights?: boolean;
}

export default function PageHeader({
  title,
  subtitle,
  breadcrumb,
  actions,
  showLights = true,
}: PageHeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.headerContent}>
        {breadcrumb && <div className={styles.breadcrumb}>{breadcrumb}</div>}
        <div className={styles.titleRow}>
          <div className={styles.titleSection}>
            <h1 className={styles.title}>{title}</h1>
            {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
          </div>
          {actions && <div className={styles.actions}>{actions}</div>}
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
