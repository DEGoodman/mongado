/**
 * SearchModal component - Global search accessible from anywhere in Knowledge Base
 *
 * Features:
 * - Modal overlay with search input
 * - Live search with debouncing
 * - Results link to articles/notes
 * - Keyboard shortcut (Cmd/Ctrl+K) to open
 * - Escape to close
 */

"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { logger } from "@/lib/logger";
import styles from "./SearchModal.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SearchResult {
  id: number | string;
  type: "article" | "note";
  title: string;
  content: string;
  snippet: string;
  score: number;
}

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// Helper function to highlight search terms in text
function highlightText(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;

  const regex = new RegExp(`(${query.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
  const parts = text.split(regex);

  return parts.map((part, index) =>
    regex.test(part) ? (
      <mark key={index} className={styles.highlight}>
        {part}
      </mark>
    ) : (
      part
    )
  );
}

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const performSearch = useCallback(async (query: string) => {
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
          semantic: false,
          limit: 10,
        }),
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data = await response.json();
      setSearchResults(data.results || []);
      logger.info("Global search completed", {
        query: query,
        resultCount: data.results?.length || 0,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to perform search";
      setSearchError(errorMessage);
      logger.error("Global search failed", err);
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Debounced search as user types
  useEffect(() => {
    if (!isOpen) return;

    const timeoutId = setTimeout(() => {
      if (searchQuery.trim().length > 0) {
        performSearch(searchQuery);
      } else {
        setSearchResults([]);
        setHasSearched(false);
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery, isOpen, performSearch]);

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [isOpen]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setSearchQuery("");
      setSearchResults([]);
      setSearchError(null);
      setHasSearched(false);
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleResultClick = () => {
    onClose();
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Search Input */}
        <div className={styles.searchHeader}>
          <span className={styles.searchIcon}>🔍</span>
          <input
            ref={inputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search articles and notes..."
            className={styles.searchInput}
            autoComplete="off"
          />
          <button onClick={onClose} className={styles.closeButton}>
            <kbd>esc</kbd>
          </button>
        </div>

        {/* Results */}
        <div className={styles.results}>
          {isSearching && <div className={styles.loading}>Searching...</div>}

          {searchError && <div className={styles.error}>{searchError}</div>}

          {!isSearching && searchResults.length > 0 && (
            <div className={styles.resultsList}>
              {searchResults.map((result) => {
                const href =
                  result.type === "article"
                    ? `/knowledge-base/articles/${result.id}`
                    : `/knowledge-base/notes/${result.id}`;

                return (
                  <Link
                    key={`${result.type}-${result.id}`}
                    href={href}
                    className={styles.resultItem}
                    onClick={handleResultClick}
                  >
                    <div className={styles.resultMeta}>
                      <span className={styles.resultType}>
                        {result.type === "article" ? "📚" : "📝"}
                      </span>
                      <span className={styles.resultScore}>{result.score.toFixed(1)}</span>
                    </div>
                    <div className={styles.resultContent}>
                      <div className={styles.resultTitle}>
                        {highlightText(result.title, searchQuery)}
                      </div>
                      <div className={styles.resultSnippet}>
                        {highlightText(result.snippet, searchQuery)}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}

          {!isSearching && searchResults.length === 0 && hasSearched && !searchError && (
            <div className={styles.noResults}>No results found for &quot;{searchQuery}&quot;</div>
          )}

          {!hasSearched && !isSearching && (
            <div className={styles.hint}>Start typing to search across all articles and notes</div>
          )}
        </div>
      </div>
    </div>
  );
}
