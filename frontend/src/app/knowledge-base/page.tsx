"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import { logger } from "@/lib/logger";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SearchResult {
  id: number | string;
  type: "article" | "note";
  title: string;
  content: string;
  score: number; // 1.0 for text search, cosine similarity for semantic
}

export default function KnowledgeBasePage() {
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [useSemanticSearch, setUseSemanticSearch] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const warmupStartedRef = useRef(false);

  const performSearch = async (query: string, semantic: boolean) => {
    if (!query.trim()) {
      setSearchResults([]);
      setSearchError(null);
      setHasSearched(false);
      return;
    }

    setIsSearching(true);
    setSearchError(null);
    setHasSearched(true);

    try {
      const response = await fetch(`${API_URL}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query.trim(),
          semantic: semantic,
          limit: 10,
        }),
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data = await response.json();
      setSearchResults(data.results || []);
      logger.info("Search completed", {
        query: query,
        semantic: semantic,
        resultCount: data.results?.length || 0,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to perform search";
      setSearchError(errorMessage);
      logger.error("Search failed", err);
    } finally {
      setIsSearching(false);
      // Restore focus to search input after React completes rendering
      // Use setTimeout to defer until after the render cycle
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 0);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || isSearching) return;
    await performSearch(searchQuery, useSemanticSearch);
  };

  const clearSearch = () => {
    setSearchQuery("");
    setSearchResults([]);
    setSearchError(null);
    setHasSearched(false);
  };

  // Live search: Auto-search as user types (for fast text search only)
  useEffect(() => {
    // Only do live search for text mode (semantic is too slow)
    if (useSemanticSearch) return;

    // Debounce: wait 300ms after user stops typing
    const timeoutId = setTimeout(() => {
      const trimmedQuery = searchQuery.trim();

      // Only trigger search if query is 3+ characters
      if (trimmedQuery.length >= 3) {
        performSearch(searchQuery, false);
      } else if (trimmedQuery.length === 0) {
        // Clear results when search is empty
        setSearchResults([]);
        setHasSearched(false);
      }
      // For 1-2 character queries, do nothing (wait for user to type more)
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery, useSemanticSearch]);

  // Warm up Ollama on page load for faster semantic search
  useEffect(() => {
    // Prevent duplicate warmups in React Strict Mode (dev only)
    if (warmupStartedRef.current) {
      return;
    }
    warmupStartedRef.current = true;

    const warmupOllama = async () => {
      try {
        logger.info("Starting Ollama warmup");
        const response = await fetch(`${API_URL}/api/ollama/warmup`, {
          method: "POST",
        });

        if (response.ok) {
          const data = await response.json();
          logger.info("Ollama warmup completed", { duration: data.duration_seconds });
        } else {
          logger.warn("Ollama warmup failed", { status: response.status });
        }
      } catch (err) {
        // Silently fail - warmup is optional optimization
        logger.debug("Ollama warmup error (non-critical)", err);
      }
    };

    // Fire and forget - don't block page load
    warmupOllama();
  }, []);

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
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="flex gap-2">
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search articles and notes..."
                className="flex-1 rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                autoFocus
              />
              <button
                type="submit"
                disabled={isSearching || !searchQuery.trim()}
                className="rounded-lg bg-blue-600 px-6 py-3 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSearching ? "Searching..." : useSemanticSearch ? "Search" : "Search"}
              </button>
            </div>
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <input
                  type="checkbox"
                  checked={useSemanticSearch}
                  onChange={(e) => setUseSemanticSearch(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <span>Use AI semantic search (slower, finds conceptually related content)</span>
              </label>
              {searchResults.length > 0 && (
                <button
                  type="button"
                  onClick={clearSearch}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Clear results
                </button>
              )}
            </div>
          </form>
          <p className="mt-2 text-sm text-gray-500">
            {useSemanticSearch
              ? "AI semantic search enabled - click Search button to execute"
              : "Live search enabled - results appear as you type (minimum 3 characters)"}
          </p>

          {/* Search Error */}
          {searchError && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
              {searchError}
            </div>
          )}

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className="mt-6 space-y-3">
              <h3 className="text-sm font-semibold text-gray-700">
                Found {searchResults.length} result{searchResults.length !== 1 ? "s" : ""}
              </h3>
              {searchResults.map((result) => {
                const resourcePath =
                  result.type === "article"
                    ? `/knowledge-base/articles/${result.id}`
                    : `/knowledge-base/notes/${result.id}`;

                return (
                  <Link
                    key={`${result.type}-${result.id}`}
                    href={resourcePath}
                    className="block rounded-lg border border-gray-200 p-4 transition-colors hover:border-blue-300 hover:bg-blue-50"
                  >
                    <div className="mb-1 flex items-center gap-2">
                      <span className="text-xs font-medium text-gray-500">
                        {result.type === "article" ? "📚 Article" : "🔗 Note"}
                      </span>
                      {useSemanticSearch && (
                        <span className="text-xs text-gray-400">
                          Score: {result.score.toFixed(3)}
                        </span>
                      )}
                    </div>
                    <h4 className="mb-2 font-semibold text-gray-900">{result.title}</h4>
                    <p className="line-clamp-2 text-sm text-gray-600">
                      {result.content.substring(0, 200)}
                    </p>
                  </Link>
                );
              })}
            </div>
          )}

          {/* No Results */}
          {!isSearching && searchResults.length === 0 && hasSearched && !searchError && (
            <div className="mt-4 text-center text-sm text-gray-500">
              No results found for &quot;{searchQuery}&quot;
            </div>
          )}
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
            <div className="md:col-span-2">
              <strong>API Access:</strong> Programmatic access available via the{" "}
              <a
                href="https://api.mongado.com/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-blue-600"
              >
                interactive API documentation
              </a>{" "}
              for scripting, backups, and bulk operations.
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
