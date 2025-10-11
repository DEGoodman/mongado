import Link from "next/link";

interface ProjectTileProps {
  title: string;
  description: string;
  href: string;
  icon?: string;
}

export default function ProjectTile({ title, description, href, icon = "📦" }: ProjectTileProps) {
  return (
    <Link
      href={href}
      className="group block bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 p-6 border border-gray-200 hover:border-blue-400 transform hover:-translate-y-1"
    >
      <div className="flex items-start gap-4">
        <div className="text-4xl flex-shrink-0">{icon}</div>
        <div className="flex-1">
          <h3 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
            {title}
          </h3>
          <p className="text-gray-600 text-sm leading-relaxed">{description}</p>
        </div>
        <div className="text-gray-400 group-hover:text-blue-600 transition-colors">
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </div>
      </div>
    </Link>
  );
}
