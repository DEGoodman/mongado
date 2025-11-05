/**
 * Badge component for indicating content type
 * Used to distinguish between Articles (read-only) and Notes (editable)
 * Migrated to CSS Modules with retro-modern color scheme
 */

import styles from "./Badge.module.scss";

interface BadgeProps {
  type: "article" | "note";
  className?: string;
}

export default function Badge({ type, className = "" }: BadgeProps) {
  const config = {
    article: {
      icon: "📚",
      label: "Article",
    },
    note: {
      icon: "📝",
      label: "Note",
    },
  };

  const { icon, label } = config[type];

  return (
    <span
      className={`${styles.badge} ${className}`}
      data-type={type}
      role="status"
      aria-label={`Content type: ${label}`}
    >
      <span className={styles.icon} aria-hidden="true">
        {icon}
      </span>
      {label}
    </span>
  );
}
