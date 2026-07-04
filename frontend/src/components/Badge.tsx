/**
 * Badge component for indicating content type
 * Used to distinguish between Articles (read-only) and Notes (editable)
 * Uppercase mono labels - category identity via typography, not hue.
 */

import styles from "./Badge.module.scss";

interface BadgeProps {
  type: "article" | "note";
  className?: string;
}

export default function Badge({ type, className = "" }: BadgeProps) {
  const config = {
    article: {
      label: "Article",
      short: "ART",
    },
    note: {
      label: "Note",
      short: "NOTE",
    },
  };

  const { label, short } = config[type];

  return (
    <span
      className={`${styles.badge} ${className}`}
      data-type={type}
      role="status"
      aria-label={`Content type: ${label}`}
    >
      {short}
    </span>
  );
}
