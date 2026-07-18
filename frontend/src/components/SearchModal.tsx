/**
 * SearchModal component - ⌘K command palette for the Knowledge Base (#155)
 *
 * Features:
 * - Live search with debouncing across articles and notes
 * - Full keyboard navigation: arrows + Enter to open, Esc to close
 * - Action verbs (new note, graph, random note) and recently viewed
 *   items when the query is empty
 * - Keyboard shortcut (Cmd/Ctrl+K) to open
 */

"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { logger } from "@/lib/logger";
import { mascotFor } from "@/lib/delight";
import { getRecents, recordRecent, type RecentItem } from "@/lib/recents";
import { MagnifyingGlass, NotePencil, Graph, Shuffle } from "@phosphor-icons/react";
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

interface Action {
  key: string;
  label: string;
  icon: React.ReactNode;
  href: string;
  /** "random" resolves its target at activation time */
  special?: "random";
}

/** One navigable row in the palette, whatever section it came from. */
type PaletteItem =
  | { kind: "action"; action: Action }
  | { kind: "recent"; recent: RecentItem }
  | { kind: "result"; result: SearchResult };

const ACTIONS: Action[] = [
  {
    key: "new-note",
    label: "New note",
    icon: <NotePencil size={16} aria-hidden="true" />,
    href: "/knowledge-base/notes/new",
  },
  {
    key: "graph",
    label: "Open graph",
    icon: <Graph size={16} aria-hidden="true" />,
    href: "/knowledge-base/notes/graph",
  },
  {
    key: "random",
    label: "Random note",
    icon: <Shuffle size={16} aria-hidden="true" />,
    href: "/knowledge-base/inspire",
    special: "random",
  },
];

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

function hrefFor(type: "article" | "note", id: string | number): string {
  return type === "article" ? `/knowledge-base/articles/${id}` : `/knowledge-base/notes/${id}`;
}

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [recents, setRecents] = useState<RecentItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

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

  // Focus input and load recents when modal opens
  useEffect(() => {
    if (isOpen) {
      setRecents(getRecents());
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
      setActiveIndex(0);
    }
  }, [isOpen]);

  // The flat, keyboard-navigable item list. Empty query shows actions +
  // recents; a query shows matching actions above search results.
  const items = useMemo<PaletteItem[]>(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) {
      return [
        ...ACTIONS.map((action): PaletteItem => ({ kind: "action", action })),
        ...recents.map((recent): PaletteItem => ({ kind: "recent", recent })),
      ];
    }
    const matchingActions = ACTIONS.filter((a) => a.label.toLowerCase().includes(q));
    return [
      ...matchingActions.map((action): PaletteItem => ({ kind: "action", action })),
      ...searchResults.map((result): PaletteItem => ({ kind: "result", result })),
    ];
  }, [searchQuery, recents, searchResults]);

  // Clamp/reset the active row whenever the list changes
  useEffect(() => {
    setActiveIndex(0);
  }, [searchQuery, searchResults, recents]);

  const activateItem = useCallback(
    async (item: PaletteItem) => {
      onClose();
      if (item.kind === "action") {
        if (item.action.special === "random") {
          try {
            const res = await fetch(`${API_URL}/api/notes/random`);
            if (res.ok) {
              const note = await res.json();
              if (note?.id) {
                recordRecent({ type: "note", id: note.id, title: note.title || note.id });
                router.push(hrefFor("note", note.id));
                return;
              }
            }
          } catch {
            // Fall through to the inspire page
          }
        }
        router.push(item.action.href);
      } else if (item.kind === "recent") {
        router.push(hrefFor(item.recent.type, item.recent.id));
        recordRecent(item.recent); // Bump to front
      } else {
        recordRecent({
          type: item.result.type,
          id: String(item.result.id),
          title: item.result.title,
        });
        router.push(hrefFor(item.result.type, item.result.id));
      }
    },
    [onClose, router]
  );

  // Keyboard: Esc closes, arrows move, Enter opens
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((prev) => (items.length ? (prev + 1) % items.length : 0));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((prev) => (items.length ? (prev - 1 + items.length) % items.length : 0));
      } else if (e.key === "Enter" && items[activeIndex]) {
        e.preventDefault();
        activateItem(items[activeIndex]);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, items, activeIndex, activateItem]);

  // Keep the active row visible while arrowing through a long list
  useEffect(() => {
    listRef.current
      ?.querySelector(`[data-index="${activeIndex}"]`)
      ?.scrollIntoView?.({ block: "nearest" });
  }, [activeIndex]);

  if (!isOpen) return null;

  const showEmptyState = !searchQuery.trim();
  const flatIndexOf = (item: PaletteItem): number => items.indexOf(item);

  const renderRow = (item: PaletteItem): React.ReactNode => {
    const index = flatIndexOf(item);
    const isActive = index === activeIndex;
    const rowProps = {
      "data-index": index,
      id: `palette-item-${index}`,
      role: "option",
      "aria-selected": isActive,
      className: `${styles.resultItem} ${isActive ? styles.active : ""}`,
      onMouseEnter: () => setActiveIndex(index),
    };

    if (item.kind === "action") {
      return (
        <button
          key={`action-${item.action.key}`}
          type="button"
          {...rowProps}
          onClick={() => activateItem(item)}
        >
          <div className={styles.resultMeta}>
            <span className={styles.actionIcon}>{item.action.icon}</span>
          </div>
          <div className={styles.resultContent}>
            <div className={styles.resultTitle}>{item.action.label}</div>
          </div>
        </button>
      );
    }

    const { type, id, title } =
      item.kind === "recent"
        ? item.recent
        : { type: item.result.type, id: item.result.id, title: item.result.title };

    return (
      <Link
        key={`${item.kind}-${type}-${id}`}
        href={hrefFor(type, id)}
        {...rowProps}
        onClick={() => {
          recordRecent({ type, id: String(id), title });
          onClose();
        }}
      >
        <div className={styles.resultMeta}>
          <span className={styles.resultType} data-type={type}>
            {type === "article" ? "ART" : "NOTE"}
          </span>
          {item.kind === "result" && (
            <span className={styles.resultScore}>{item.result.score.toFixed(1)}</span>
          )}
        </div>
        <div className={styles.resultContent}>
          <div className={styles.resultTitle}>
            {type === "note" && mascotFor(String(id)) && (
              <span className="delight-mascot" aria-hidden="true">
                {mascotFor(String(id))}
              </span>
            )}
            {item.kind === "result" ? highlightText(title, searchQuery) : title}
          </div>
          {item.kind === "result" && (
            <div className={styles.resultSnippet}>
              {highlightText(item.result.snippet, searchQuery)}
            </div>
          )}
        </div>
      </Link>
    );
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Search Input */}
        <div className={styles.searchHeader}>
          <span className={styles.searchIcon} aria-hidden="true">
            <MagnifyingGlass size={18} />
          </span>
          <input
            ref={inputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search, or jump to an action..."
            className={styles.searchInput}
            autoComplete="off"
            role="combobox"
            aria-expanded="true"
            aria-controls="palette-listbox"
            aria-activedescendant={items[activeIndex] ? `palette-item-${activeIndex}` : undefined}
          />
          <button onClick={onClose} className={styles.closeButton}>
            <kbd>esc</kbd>
          </button>
        </div>

        {/* Results */}
        <div className={styles.results} ref={listRef} id="palette-listbox" role="listbox">
          {isSearching && <div className={styles.loading}>Searching...</div>}

          {searchError && <div className={styles.error}>{searchError}</div>}

          {showEmptyState ? (
            <div className={styles.resultsList}>
              <div className={styles.sectionLabel}>Actions</div>
              {items.filter((i) => i.kind === "action").map(renderRow)}
              {recents.length > 0 && (
                <>
                  <div className={styles.sectionLabel}>Recent</div>
                  {items.filter((i) => i.kind === "recent").map(renderRow)}
                </>
              )}
            </div>
          ) : (
            !isSearching &&
            items.length > 0 && <div className={styles.resultsList}>{items.map(renderRow)}</div>
          )}

          {!showEmptyState && !isSearching && items.length === 0 && hasSearched && !searchError && (
            <div className={styles.noResults}>No results found for &quot;{searchQuery}&quot;</div>
          )}
        </div>

        {/* Keyboard hint footer */}
        <div className={styles.footerHint} aria-hidden="true">
          <span>
            <kbd>↑</kbd>
            <kbd>↓</kbd> navigate
          </span>
          <span>
            <kbd>↵</kbd> open
          </span>
          <span>
            <kbd>esc</kbd> close
          </span>
        </div>
      </div>
    </div>
  );
}
