/**
 * TopNavigation component - Persistent navigation bar for Knowledge Base
 *
 * Features:
 * - Logo/branding linking to home
 * - Section links (Articles, Notes) with active state
 * - Global search (Cmd/Ctrl+K) accessible from anywhere
 * - Settings dropdown (global app settings - available to all users)
 * - User menu (account actions - Sign In or user dropdown when logged in)
 *
 * Only appears in Knowledge Base section, not on homepage
 */

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Settings from "./Settings";
import UserMenu from "./UserMenu";
import SearchModal from "./SearchModal";
import styles from "./TopNavigation.module.scss";

export default function TopNavigation() {
  const pathname = usePathname();
  const [searchOpen, setSearchOpen] = useState(false);

  // Determine active section
  const isArticlesSection = pathname?.startsWith("/knowledge-base/articles");
  const isNotesSection = pathname?.startsWith("/knowledge-base/notes");
  const isToolboxSection = pathname?.startsWith("/knowledge-base/toolbox");

  // Keyboard shortcut: Cmd/Ctrl+K to open search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(true);
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
              href="/knowledge-base/toolbox"
              className={`${styles.navLink} ${isToolboxSection ? styles.active : ""}`}
            >
              Toolbox
            </Link>
          </div>

          {/* Right: Search + Settings + User Menu */}
          <div className={styles.right}>
            <button
              onClick={() => setSearchOpen(true)}
              className={styles.searchButton}
              aria-label="Open search"
            >
              <span className={styles.searchIcon}>🔍</span>
              <span className={styles.searchLabel}>Search</span>
              <kbd className={styles.searchKbd}>⌘K</kbd>
            </button>
            <Settings />
            <UserMenu />
          </div>
        </div>
      </nav>

      {/* Search Modal */}
      <SearchModal isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  );
}
