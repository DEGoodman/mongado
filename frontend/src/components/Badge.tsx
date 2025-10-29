/**
 * Badge component for indicating content type
 * Used to distinguish between Articles (read-only) and Notes (editable)
 */

interface BadgeProps {
  type: "article" | "note";
  className?: string;
}

export default function Badge({ type, className = "" }: BadgeProps) {
  const config = {
    article: {
      icon: "📄",
      label: "Article",
      bgColor: "bg-blue-50",
      textColor: "text-blue-700",
      borderColor: "border-blue-200",
    },
    note: {
      icon: "📝",
      label: "Note",
      bgColor: "bg-purple-50",
      textColor: "text-purple-700",
      borderColor: "border-purple-200",
    },
  };

  const { icon, label, bgColor, textColor, borderColor } = config[type];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-0.5 text-xs font-medium ${bgColor} ${textColor} ${borderColor} ${className}`}
      role="status"
      aria-label={`Content type: ${label}`}
    >
      <span aria-hidden="true">{icon}</span>
      {label}
    </span>
  );
}
