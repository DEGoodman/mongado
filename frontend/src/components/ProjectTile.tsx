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
      className="group block transform rounded-xl border border-gray-200 bg-white p-6 shadow-md transition-all duration-300 hover:-translate-y-1 hover:border-blue-400 hover:shadow-xl"
    >
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 text-4xl">{icon}</div>
        <div className="flex-1">
          <h3 className="mb-2 text-xl font-bold text-gray-900 transition-colors group-hover:text-blue-600">
            {title}
          </h3>
          <p className="text-sm leading-relaxed text-gray-600">{description}</p>
        </div>
        <div className="text-gray-400 transition-colors group-hover:text-blue-600">
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </Link>
  );
}
