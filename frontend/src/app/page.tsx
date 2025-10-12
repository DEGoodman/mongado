import ProjectTile from "@/components/ProjectTile";
import { siteConfig } from "@/lib/site-config";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero Section */}
        <div className="bg-white rounded-2xl shadow-xl p-8 sm:p-12 mb-8">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-5xl sm:text-6xl font-bold text-gray-900 mb-4">
              {siteConfig.author.fullTitle}
            </h1>
            <p className="text-xl text-gray-600 mb-2">
              {siteConfig.author.title}
            </p>
            <p className="text-md text-gray-500">
              {siteConfig.author.location}
            </p>
          </div>

          {/* Bio */}
          <div className="prose prose-lg max-w-none mb-8">
            <p className="text-gray-700 leading-relaxed text-center max-w-3xl mx-auto">
              {siteConfig.author.bio}
            </p>
          </div>

          {/* Social Links */}
          <div className="flex flex-wrap gap-4 justify-center mt-8">
            <a
              href={siteConfig.links.github}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors shadow-md hover:shadow-lg"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              GitHub
            </a>
            <a
              href={siteConfig.links.linkedin}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md hover:shadow-lg"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
              </svg>
              LinkedIn
            </a>
            <a
              href={siteConfig.links.email}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 transition-colors shadow-md hover:shadow-lg"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              Email
            </a>
          </div>
        </div>

        {/* Projects Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Projects</h2>
          <div className="grid gap-6 md:grid-cols-2">
            <ProjectTile
              title="Knowledge Base"
              description="Articles and atomic notes in one place. Long-form content alongside a Zettelkasten system with wikilinks, backlinks, and AI-powered search."
              href="/knowledge-base"
              icon="📚"
            />
            <ProjectTile
              title="tagbar"
              description="Instagram hashtag scraper and photo analyzer built with Python. Extract insights and analyze trends from social media content."
              href="https://github.com/DEGoodman/tagbar"
              icon="📊"
            />
            <ProjectTile
              title="EVA"
              description="Audio environmental visualizer built with Processing. Creates dynamic visual representations of sound and music in real-time."
              href="https://github.com/DEGoodman/EVA"
              icon="🎵"
            />
            <ProjectTile
              title="burritoMe"
              description="iOS app for when you need a burrito, like now. Built with Swift to help you find the perfect burrito nearby."
              href="https://github.com/DEGoodman/burritoMe"
              icon="🌯"
            />
          </div>
        </div>

        {/* Footer note */}
        <div className="text-center text-gray-500 text-sm mt-12">
          <p>Built with Next.js, FastAPI, and Python ☕</p>
          <p className="mt-2 text-xs">© 2025 {siteConfig.author.name} • {siteConfig.author.location}</p>
        </div>
      </main>
    </div>
  );
}
