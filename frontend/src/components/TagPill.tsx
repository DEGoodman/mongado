/**
 * TagPill component for consistent tag styling across Articles and Notes
 * Replaces inconsistent tag rendering with unified pill design
 */

interface TagPillProps {
  tag: string;
  showHash?: boolean; // Whether to show # prefix (for articles)
  className?: string;
}

export default function TagPill({ tag, showHash = false, className = "" }: TagPillProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700 transition hover:bg-gray-200 ${className}`}
    >
      {showHash && <span className="mr-0.5">#</span>}
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
  className?: string;
}

export function TagPillList({
  tags,
  showHash = false,
  maxVisible,
  className = "",
}: TagPillListProps) {
  const visibleTags = maxVisible ? tags.slice(0, maxVisible) : tags;
  const remainingCount = maxVisible && tags.length > maxVisible ? tags.length - maxVisible : 0;

  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {visibleTags.map((tag) => (
        <TagPill key={tag} tag={tag} showHash={showHash} />
      ))}
      {remainingCount > 0 && (
        <span className="inline-flex items-center text-sm text-gray-500">
          +{remainingCount} more
        </span>
      )}
    </div>
  );
}
