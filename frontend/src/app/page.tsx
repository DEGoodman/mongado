import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="bg-white rounded-2xl shadow-xl p-8 sm:p-12">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-4">
              Welcome to Mongado
            </h1>
            <p className="text-xl text-gray-600">
              Your personal knowledge base
            </p>
          </div>

          {/* Bio Section */}
          <div className="prose prose-lg max-w-none mb-8">
            <p className="text-gray-700 leading-relaxed">
              Mongado is an intelligent knowledge management system designed to help you capture,
              organize, and retrieve information effortlessly. Built with modern web technologies
              and powered by AI, it transforms your notes and articles into an easily searchable
              knowledge base.
            </p>
            <p className="text-gray-700 leading-relaxed">
              Whether you're collecting technical documentation, research notes, or personal insights,
              Mongado provides a clean interface for writing in Markdown and an AI-powered search
              to help you find exactly what you need, when you need it.
            </p>
          </div>

          {/* Call to Action */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mt-12">
            <Link
              href="/articles"
              className="px-8 py-3 bg-blue-600 text-white text-lg font-semibold rounded-lg hover:bg-blue-700 transition-colors text-center shadow-md hover:shadow-lg"
            >
              View Knowledge Base
            </Link>
          </div>

          {/* Features */}
          <div className="grid sm:grid-cols-3 gap-6 mt-12">
            <div className="text-center">
              <div className="text-3xl mb-3">📝</div>
              <h3 className="font-semibold text-gray-900 mb-2">Markdown Support</h3>
              <p className="text-sm text-gray-600">Write in clean, portable Markdown format</p>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-3">🔍</div>
              <h3 className="font-semibold text-gray-900 mb-2">AI-Powered Search</h3>
              <p className="text-sm text-gray-600">Find content using natural language queries</p>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-3">🏷️</div>
              <h3 className="font-semibold text-gray-900 mb-2">Smart Organization</h3>
              <p className="text-sm text-gray-600">Tag and categorize your knowledge</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
