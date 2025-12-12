"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import Badge from "@/components/Badge";
import { logger } from "@/lib/logger";
import styles from "./page.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SearchResult {
  id: number | string;
  type: "article" | "note";
  title: string;
  content: string;
  snippet: string; // Contextual snippet around match
  score: number; // 1.0 for text search, cosine similarity for semantic
}

// Helper function to highlight search terms in text
function highlightText(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;

  // Create regex to match query (case-insensitive, whole word or partial)
  const regex = new RegExp(`(${query.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
  const parts = text.split(regex);

  return parts.map((part, index) =>
    regex.test(part) ? (
      <mark key={index} className="bg-yellow-200 font-medium">
        {part}
      </mark>
    ) : (
      part
    )
  );
}

export default function KnowledgeBasePage() {
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const performSearch = async (query: string) => {
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
          semantic: false, // Always use fast text search
          limit: 10,
        }),
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data = await response.json();
      setSearchResults(data.results || []);
      logger.info("Text search completed", {
        query: query,
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
    await performSearch(searchQuery);
  };

  const clearSearch = () => {
    setSearchQuery("");
    setSearchResults([]);
    setSearchError(null);
    setHasSearched(false);
  };

  // Live search: Auto-search as user types
  useEffect(() => {
    // Debounce: wait 300ms after user stops typing
    const timeoutId = setTimeout(() => {
      const trimmedQuery = searchQuery.trim();

      // Trigger search for any non-empty query
      if (trimmedQuery.length > 0) {
        performSearch(searchQuery);
      } else {
        // Clear results when search is empty
        setSearchResults([]);
        setHasSearched(false);
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  return (
    <div className={styles.container}>
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      {/* Header */}
      <header className={styles.header}>
        <h1 className={styles.title}>Knowledge Base</h1>
      </header>

      <main className={styles.main}>
        {/* Search Section */}
        <div className={styles.searchSection}>
          <h2 className={styles.searchTitle}>🔍 Search Everything</h2>
          <form onSubmit={handleSearch} className={styles.searchForm}>
            <div className={styles.searchRow}>
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search articles and notes..."
                className={styles.searchInput}
                autoFocus
                aria-label="Search all articles and notes"
              />
              {searchResults.length > 0 && (
                <button
                  type="button"
                  onClick={clearSearch}
                  className={styles.clearButton}
                  aria-label="Clear search results"
                >
                  Clear
                </button>
              )}
            </div>
          </form>
          <p className={styles.searchHint}>
            Live search enabled - results appear as you type. For AI-powered semantic search, use
            the AI Assistant.
          </p>

          {/* Search Error */}
          {searchError && <div className={styles.searchError}>{searchError}</div>}

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className={styles.resultsSection}>
              <h3 className={styles.resultsHeader}>
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
                    className={styles.resultCard}
                  >
                    <div className={styles.resultMeta}>
                      <span className={styles.resultType}>
                        {result.type === "article" ? "📚 Article" : "📝 Note"}
                      </span>
                      <span className={styles.resultScore}>Score: {result.score.toFixed(1)}</span>
                    </div>
                    <h4 className={styles.resultTitle}>
                      {highlightText(result.title, searchQuery)}
                    </h4>
                    <p className={styles.resultContent}>
                      {highlightText(result.snippet, searchQuery)}
                    </p>
                  </Link>
                );
              })}
            </div>
          )}

          {/* No Results */}
          {!isSearching && searchResults.length === 0 && hasSearched && !searchError && (
            <div className={styles.noResults}>No results found for &quot;{searchQuery}&quot;</div>
          )}
        </div>

        {/* Content Type Cards */}
        <div className={styles.contentGrid}>
          {/* Articles Card */}
          <div className={`${styles.contentCard} ${styles.articles}`}>
            <div className={styles.cardBadge}>
              <Badge type="article" />
            </div>
            <h3 className={styles.cardTitle}>Articles</h3>
            <p className={styles.cardDescription}>
              Long-form curated content. Professional essays and deep dives into topics like SaaS
              billing, engineering management, and SRE practices.
            </p>
            <div className={styles.cardActions}>
              <Link
                href="/knowledge-base/articles"
                className={`${styles.cardButton} ${styles.primary}`}
              >
                Browse Articles →
              </Link>
            </div>
          </div>

          {/* Notes Card */}
          <div className={`${styles.contentCard} ${styles.notes}`}>
            <div className={styles.cardBadge}>
              <Badge type="note" />
            </div>
            <h3 className={styles.cardTitle}>Notes</h3>
            <p className={styles.cardDescription}>
              Atomic ideas, connected. A Zettelkasten-inspired system with wikilinks, backlinks, and
              graph visualization for building your personal knowledge graph.
            </p>
            <div className={styles.cardActions}>
              <Link
                href="/knowledge-base/notes"
                className={`${styles.cardButton} ${styles.notePrimary}`}
              >
                Browse Notes →
              </Link>
              <Link
                href="/knowledge-base/notes/graph"
                className={`${styles.cardButton} ${styles.noteSecondary}`}
              >
                View Graph →
              </Link>
            </div>
          </div>

          {/* Toolbox Card */}
          <div className={`${styles.contentCard} ${styles.toolbox}`}>
            <div className={styles.cardBadge}>
              <span className={styles.toolboxBadge}>Reference</span>
            </div>
            <h3 className={styles.cardTitle}>Toolbox</h3>
            <p className={styles.cardDescription}>
              Quick reference library. Frameworks, checklists, acronyms, and mental models for fast
              lookup when you need them most.
            </p>
            <div className={styles.cardActions}>
              <Link
                href="/knowledge-base/toolbox"
                className={`${styles.cardButton} ${styles.toolboxPrimary}`}
              >
                Open Toolbox →
              </Link>
            </div>
          </div>
        </div>

        {/* Info Section */}
        <div className={styles.infoSection}>
          <h3 className={styles.infoTitle}>💡 How to Use</h3>
          <div className={styles.infoGrid}>
            <div className={styles.infoItem}>
              <strong>Articles</strong> are long-form, polished content for deep exploration of
              topics.
            </div>
            <div className={styles.infoItem}>
              <strong>Notes</strong> are atomic ideas that can be linked together using
              [[wikilinks]].
            </div>
            <div className={styles.infoItem}>
              Both systems support cross-linking - reference notes from articles and vice versa.
            </div>
            <div className={`${styles.infoItem} ${styles.infoItemFull}`}>
              <strong>Fast Text Search:</strong> Use the search box above for instant keyword
              matching. Best when you know exact terms or want quick results.
            </div>
            <div className={`${styles.infoItem} ${styles.infoItemFull}`}>
              <strong>AI Semantic Search:</strong> Use the AI Assistant&apos;s Search tab to find
              conceptually related content, even without exact keyword matches. Takes longer but
              discovers connections.
            </div>
            <div className={`${styles.infoItem} ${styles.infoItemFull}`}>
              <strong>Chat with AI:</strong> Use the AI Assistant&apos;s Chat tab to ask questions
              and get answers with context from your knowledge base.
            </div>
            <div className={`${styles.infoItem} ${styles.infoItemFull}`}>
              <strong>API Access:</strong> Programmatic access available via the{" "}
              <a href="https://api.mongado.com/docs" target="_blank" rel="noopener noreferrer">
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
