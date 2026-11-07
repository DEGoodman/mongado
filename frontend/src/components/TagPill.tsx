/**
 * TagPill component for consistent tag styling across Articles and Notes
 * Replaces inconsistent tag rendering with unified pill design
 */

import styles from "./TagPill.module.scss";

interface TagPillProps {
  tag: string;
  showHash?: boolean; // Whether to show # prefix (for articles)
  onClick?: (tag: string) => void; // Optional click handler for filtering
  variant?: "article" | "note"; // Color variant for warm-cool theme
  className?: string;
}

export default function TagPill({
  tag,
  showHash = false,
  onClick,
  variant,
  className = "",
}: TagPillProps) {
  const handleClick = (e: React.MouseEvent) => {
    if (onClick) {
      e.preventDefault();
      e.stopPropagation();
      onClick(tag);
    }
  };

  const pillClasses = `${styles.tagPill} ${onClick ? styles.interactive : styles.static} ${className}`;

  return (
    <span className={pillClasses} onClick={handleClick} data-variant={variant}>
      {showHash && <span className={styles.hash}>#</span>}
      {tag}
    </span>
  );
}

/**
 * TagPillList component for rendering multiple tags with proper spacing
 */
interface TagPillListProps {
  tags: string[];
  showHash?: boolean;
  maxVisible?: number; // Limit number of tags shown (with "+N more")
  collapseAfter?: number; // Phones only (≤640px): hide tags past N, show a "+N" chip
  onClick?: (tag: string) => void; // Optional click handler for filtering
  variant?: "article" | "note"; // Color variant for warm-cool theme
  className?: string;
}

export function TagPillList({
  tags,
  showHash = false,
  maxVisible,
  collapseAfter,
  onClick,
  variant,
  className = "",
}: TagPillListProps) {
  const visibleTags = maxVisible ? tags.slice(0, maxVisible) : tags;
  const remainingCount = maxVisible && tags.length > maxVisible ? tags.length - maxVisible : 0;

  return (
    <div
      className={`${styles.tagPillList} ${collapseAfter !== undefined ? styles.collapsing : ""} ${className}`}
    >
      {visibleTags.map((tag, index) => (
        <TagPill
          key={tag}
          tag={tag}
          showHash={showHash}
          onClick={onClick}
          variant={variant}
          className={
            collapseAfter !== undefined && index >= collapseAfter ? styles.collapsible : ""
          }
        />
      ))}
      {collapseAfter !== undefined && visibleTags.length > collapseAfter && (
        <span className={styles.collapsedCount}>+{visibleTags.length - collapseAfter}</span>
      )}
      {remainingCount > 0 && <span className={styles.remainingCount}>+{remainingCount} more</span>}
    </div>
  );
}
