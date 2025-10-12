"use client";

import Link from "next/link";
import { useState } from "react";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";

export default function KnowledgeBasePage() {
  const [aiPanelOpen, setAiPanelOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-blue-600 hover:text-blue-800 text-sm">
              ← Home
            </Link>
            <h1 className="text-3xl font-bold text-gray-900">Knowledge Base</h1>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Section */}
        <div className="bg-white rounded-lg shadow-md p-8 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            🔍 Search Everything
          </h2>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Search articles and notes..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
              Search
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Powered by AI semantic search
          </p>
        </div>

        {/* Content Type Cards */}
        <div className="grid gap-6 md:grid-cols-2 mb-8">
          {/* Articles Card */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="text-4xl mb-4">📚</div>
            <h3 className="text-2xl font-bold text-gray-900 mb-2">Articles</h3>
            <p className="text-gray-600 mb-4">
              Long-form curated content. Professional essays and deep dives into
              topics like SaaS billing, engineering management, and SRE practices.
            </p>
            <div className="flex gap-3">
              <Link
                href="/knowledge-base/articles"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Browse Articles →
              </Link>
            </div>
          </div>

          {/* Notes Card */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="text-4xl mb-4">🔗</div>
            <h3 className="text-2xl font-bold text-gray-900 mb-2">Notes</h3>
            <p className="text-gray-600 mb-4">
              Atomic ideas, connected. A Zettelkasten-inspired system with
              wikilinks, backlinks, and graph visualization for building your
              personal knowledge graph.
            </p>
            <div className="flex gap-3">
              <Link
                href="/knowledge-base/notes"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Browse Notes →
              </Link>
              <Link
                href="/knowledge-base/notes/graph"
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                View Graph →
              </Link>
            </div>
          </div>
        </div>

        {/* Info Section */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">
            💡 How to Use
          </h3>
          <div className="grid gap-4 md:grid-cols-2 text-sm text-blue-800">
            <div>
              <strong>Articles</strong> are long-form, polished content for
              deep exploration of topics.
            </div>
            <div>
              <strong>Notes</strong> are atomic ideas that can be linked
              together using [[wikilinks]].
            </div>
            <div>
              Both systems support cross-linking - reference notes from
              articles and vice versa.
            </div>
            <div>
              Use AI-powered search to find relevant content across both
              articles and notes.
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
