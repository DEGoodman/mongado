/**
 * TopNavigation component - Persistent navigation bar for Knowledge Base
 *
 * Features:
 * - Logo/branding linking to home
 * - Section links (Articles, Notes) with active state
 * - Global search (Cmd/Ctrl+K) accessible from anywhere
 * - Header menu (theme, AI settings, account actions incl. Admin link)
 *
 * Only appears in Knowledge Base section, not on homepage
 */

"use client";

import { useState, useEffect } from "react";
import { MagnifyingGlass, Lightning } from "@phosphor-icons/react";
import { prefetchOnce } from "@/lib/prefetch";

// The graph payload (100+ notes with edges) is the slowest KB fetch; warm the
// browser HTTP cache while the user is still hovering the nav link.
function prefetchGraphData(): void {
  prefetchOnce("graph:data", () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const token = localStorage.getItem("admin_token");
    const headers: HeadersInit = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return fetch(`${apiUrl}/api/notes/graph/data`, { headers, credentials: "include" });
  });
}
import Link from "next/link";
import { usePathname } from "next/navigation";
import HeaderMenu from "./HeaderMenu";
import SearchModal from "./SearchModal";
import QuickCapture from "./QuickCapture";
import { isAuthenticated } from "@/lib/api/client";
import styles from "./TopNavigation.module.scss";

export default function TopNavigation() {
  const pathname = usePathname();
  const [searchOpen, setSearchOpen] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(false);
  // Client-side only to avoid hydration mismatch
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(isAuthenticated());
  }, []);

  // Determine active section
  const isArticlesSection = pathname?.startsWith("/knowledge-base/articles");
  const isGraphSection = pathname?.startsWith("/knowledge-base/notes/graph");
  const isNotesSection = pathname?.startsWith("/knowledge-base/notes") && !isGraphSection;
  const isToolboxSection = pathname?.startsWith("/knowledge-base/toolbox");
  const isInspireSection = pathname?.startsWith("/knowledge-base/inspire");

  // Keyboard shortcuts: Cmd/Ctrl+K opens search; plain "n" (outside inputs)
  // opens quick capture (#154) when authenticated
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(true);
        return;
      }

      if (e.key === "n" && !e.metaKey && !e.ctrlKey && !e.altKey && !e.shiftKey) {
        const target = e.target as HTMLElement;
        const typing =
          target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
        if (!typing && isAuthenticated()) {
          e.preventDefault();
          setCaptureOpen(true);
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <>
      <nav className={styles.topNav} aria-label="Main navigation">
        <div className={styles.container}>
          {/* Left: Logo/Branding */}
          <div className={styles.left}>
            <Link href="/" className={styles.logo}>
              <span className={styles.logoText}>Mongado</span>
            </Link>
          </div>

          {/* Center: Section Links */}
          <div className={styles.center}>
            <Link
              href="/knowledge-base/articles"
              className={`${styles.navLink} ${isArticlesSection ? styles.active : ""}`}
            >
              Articles
            </Link>
            <Link
              href="/knowledge-base/notes"
              className={`${styles.navLink} ${isNotesSection ? styles.active : ""}`}
            >
              Notes
            </Link>
            <Link
              href="/knowledge-base/notes/graph"
              className={`${styles.navLink} ${isGraphSection ? styles.active : ""}`}
              onMouseEnter={prefetchGraphData}
              onFocus={prefetchGraphData}
            >
              Graph
            </Link>
            <Link
              href="/knowledge-base/toolbox"
              className={`${styles.navLink} ${isToolboxSection ? styles.active : ""}`}
            >
              Toolbox
            </Link>
            <Link
              href="/knowledge-base/inspire"
              className={`${styles.navLink} ${isInspireSection ? styles.active : ""}`}
            >
              Inspire
            </Link>
          </div>

          {/* Right: Capture + Search + Settings + User Menu */}
          <div className={styles.right}>
            {authed && (
              <button
                onClick={() => setCaptureOpen(true)}
                className={styles.captureButton}
                aria-label="Quick capture a note"
              >
                <span className={styles.searchIcon} aria-hidden="true">
                  <Lightning size={16} />
                </span>
                <span className={styles.searchLabel}>Capture</span>
                <kbd className={styles.searchKbd}>N</kbd>
              </button>
            )}
            <button
              onClick={() => setSearchOpen(true)}
              className={styles.searchButton}
              aria-label="Open search"
            >
              <span className={styles.searchIcon} aria-hidden="true">
                <MagnifyingGlass size={16} />
              </span>
              <span className={styles.searchLabel}>Search</span>
              <kbd className={styles.searchKbd}>⌘K</kbd>
            </button>
            <HeaderMenu />
          </div>
        </div>
      </nav>

      {/* Search Modal */}
      <SearchModal isOpen={searchOpen} onClose={() => setSearchOpen(false)} />

      {/* Quick Capture Modal */}
      <QuickCapture isOpen={captureOpen} onClose={() => setCaptureOpen(false)} />
    </>
  );
}
