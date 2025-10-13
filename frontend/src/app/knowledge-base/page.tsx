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
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-sm text-blue-600 hover:text-blue-800">
              ← Home
            </Link>
            <h1 className="text-3xl font-bold text-gray-900">Knowledge Base</h1>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Search Section */}
        <div className="mb-8 rounded-lg bg-white p-8 shadow-md">
          <h2 className="mb-4 text-xl font-semibold text-gray-900">🔍 Search Everything</h2>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Search articles and notes..."
              className="flex-1 rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button className="rounded-lg bg-blue-600 px-6 py-3 text-white transition-colors hover:bg-blue-700">
              Search
            </button>
          </div>
          <p className="mt-2 text-sm text-gray-500">Powered by AI semantic search</p>
        </div>

        {/* Content Type Cards */}
        <div className="mb-8 grid gap-6 md:grid-cols-2">
          {/* Articles Card */}
          <div className="rounded-lg bg-white p-6 shadow-md">
            <div className="mb-4 text-4xl">📚</div>
            <h3 className="mb-2 text-2xl font-bold text-gray-900">Articles</h3>
            <p className="mb-4 text-gray-600">
              Long-form curated content. Professional essays and deep dives into topics like SaaS
              billing, engineering management, and SRE practices.
            </p>
            <div className="flex gap-3">
              <Link
                href="/knowledge-base/articles"
                className="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
              >
                Browse Articles →
              </Link>
            </div>
          </div>

          {/* Notes Card */}
          <div className="rounded-lg bg-white p-6 shadow-md">
            <div className="mb-4 text-4xl">🔗</div>
            <h3 className="mb-2 text-2xl font-bold text-gray-900">Notes</h3>
            <p className="mb-4 text-gray-600">
              Atomic ideas, connected. A Zettelkasten-inspired system with wikilinks, backlinks, and
              graph visualization for building your personal knowledge graph.
            </p>
            <div className="flex gap-3">
              <Link
                href="/knowledge-base/notes"
                className="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
              >
                Browse Notes →
              </Link>
              <Link
                href="/knowledge-base/notes/graph"
                className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50"
              >
                View Graph →
              </Link>
            </div>
          </div>
        </div>

        {/* Info Section */}
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-6">
          <h3 className="mb-2 text-lg font-semibold text-blue-900">💡 How to Use</h3>
          <div className="grid gap-4 text-sm text-blue-800 md:grid-cols-2">
            <div>
              <strong>Articles</strong> are long-form, polished content for deep exploration of
              topics.
            </div>
            <div>
              <strong>Notes</strong> are atomic ideas that can be linked together using
              [[wikilinks]].
            </div>
            <div>
              Both systems support cross-linking - reference notes from articles and vice versa.
            </div>
            <div>
              Use AI-powered search to find relevant content across both articles and notes.
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
