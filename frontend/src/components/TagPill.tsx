/**
 * TagPill component for consistent tag styling across Articles and Notes
 * Replaces inconsistent tag rendering with unified pill design
 */

interface TagPillProps {
  tag: string;
  showHash?: boolean; // Whether to show # prefix (for articles)
  onClick?: (tag: string) => void; // Optional click handler for filtering
  className?: string;
}

export default function TagPill({ tag, showHash = false, onClick, className = "" }: TagPillProps) {
  const handleClick = (e: React.MouseEvent) => {
    if (onClick) {
      e.preventDefault();
      e.stopPropagation();
      onClick(tag);
    }
  };

  const baseClasses = `inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700 transition ${className}`;
  const interactiveClasses = onClick
    ? "cursor-pointer hover:bg-blue-100 hover:text-blue-800"
    : "hover:bg-gray-200";

  return (
    <span className={`${baseClasses} ${interactiveClasses}`} onClick={handleClick}>
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
  onClick?: (tag: string) => void; // Optional click handler for filtering
  className?: string;
}

export function TagPillList({
  tags,
  showHash = false,
  maxVisible,
  onClick,
  className = "",
}: TagPillListProps) {
  const visibleTags = maxVisible ? tags.slice(0, maxVisible) : tags;
  const remainingCount = maxVisible && tags.length > maxVisible ? tags.length - maxVisible : 0;

  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {visibleTags.map((tag) => (
        <TagPill key={tag} tag={tag} showHash={showHash} onClick={onClick} />
      ))}
      {remainingCount > 0 && (
        <span className="inline-flex items-center text-sm text-gray-500">
          +{remainingCount} more
        </span>
      )}
    </div>
  );
}
