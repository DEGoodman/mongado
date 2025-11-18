/**
 * TopNavigation component - Persistent navigation bar for Knowledge Base
 *
 * Features:
 * - Logo/branding linking to home
 * - Section links (Articles, Notes) with active state
 * - Settings dropdown (global app settings - available to all users)
 * - User menu (account actions - Sign In or user dropdown when logged in)
 *
 * Only appears in Knowledge Base section, not on homepage
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Settings from "./Settings";
import UserMenu from "./UserMenu";
import styles from "./TopNavigation.module.scss";

export default function TopNavigation() {
  const pathname = usePathname();

  // Determine active section
  const isArticlesSection = pathname?.startsWith("/knowledge-base/articles");
  const isNotesSection = pathname?.startsWith("/knowledge-base/notes");

  return (
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
        </div>

        {/* Right: Settings + User Menu */}
        <div className={styles.right}>
          <Settings />
          <UserMenu />
        </div>
      </div>
    </nav>
  );
}
