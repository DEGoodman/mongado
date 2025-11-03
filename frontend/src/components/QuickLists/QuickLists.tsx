/**
 * QuickLists Component
 * Displays categorized note lists: Orphans, Hubs, Central Concepts
 * Part of Phase 2 - Quick Lists System
 */

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import styles from "./QuickLists.module.scss";

interface Note {
  id: string;
  title?: string;
  link_count?: number;
  backlink_count?: number;
}

interface QuickListsData {
  orphans: Note[];
  hubs: Note[];
  central_concepts: Note[];
  counts: {
    orphans: number;
    hubs: number;
    central_concepts: number;
  };
}

interface QuickListsSectionProps {
  title: string;
  icon: string;
  notes: Note[];
  count: number;
  className: string;
  description: string;
  isExpanded: boolean;
  onToggle: () => void;
}

function QuickListsSection({
  title,
  icon,
  notes,
  count,
  className,
  description,
  isExpanded,
  onToggle,
}: QuickListsSectionProps) {
  return (
    <div className={`${styles.section} ${className}`}>
      <div
        className={styles.header}
        onClick={onToggle}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onToggle();
          }
        }}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        aria-controls={`${title.toLowerCase().replace(/\s+/g, "-")}-content`}
      >
        <div className={styles.headerContent}>
          <span className={styles.icon} aria-hidden="true">
            {icon}
          </span>
          <h3 className={styles.title}>{title}</h3>
          <span className={styles.count} aria-label={`${count} notes`}>
            {count}
          </span>
        </div>
        <span className={`${styles.chevron} ${isExpanded ? styles.expanded : ""}`} aria-hidden="true">
          ▼
        </span>
      </div>

      <div
        className={`${styles.content} ${isExpanded ? styles.expanded : ""}`}
        id={`${title.toLowerCase().replace(/\s+/g, "-")}-content`}
      >
        {notes.length === 0 ? (
          <div className={styles.empty}>{description}</div>
        ) : (
          <div className={styles.notesList}>
            {notes.map((note) => (
              <Link key={note.id} href={`/knowledge-base/notes/${note.id}`} className={styles.noteCard}>
                <div className={styles.noteTitle}>{note.title || note.id}</div>
                <div className={styles.noteId}>
                  {note.id}
                  {note.link_count !== undefined && ` · ${note.link_count} links`}
                  {note.backlink_count !== undefined && ` · ${note.backlink_count} backlinks`}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function QuickLists() {
  const [data, setData] = useState<QuickListsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(["orphans"]));

  useEffect(() => {
    async function fetchQuickLists() {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/notes/quick-lists`);
        if (!response.ok) {
          throw new Error("Failed to fetch quick lists");
        }
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    }

    fetchQuickLists();
  }, []);

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  if (loading) {
    return <div className={styles.quickLists}>Loading quick lists...</div>;
  }

  if (error) {
    return <div className={styles.quickLists}>Error: {error}</div>;
  }

  if (!data) {
    return null;
  }

  return (
    <div className={styles.quickLists}>
      <QuickListsSection
        title="Orphan Notes"
        icon="🏝️"
        notes={data.orphans}
        count={data.counts.orphans}
        className={styles.orphans}
        description="No orphaned notes - all notes are well connected!"
        isExpanded={expandedSections.has("orphans")}
        onToggle={() => toggleSection("orphans")}
      />

      <QuickListsSection
        title="Hub Notes"
        icon="🗺️"
        notes={data.hubs}
        count={data.counts.hubs}
        className={styles.hubs}
        description="No hub notes yet - create notes with 3+ outbound links to see them here."
        isExpanded={expandedSections.has("hubs")}
        onToggle={() => toggleSection("hubs")}
      />

      <QuickListsSection
        title="Central Concepts"
        icon="⭐"
        notes={data.central_concepts}
        count={data.counts.central_concepts}
        className={styles.central}
        description="No central concept notes yet - highly referenced notes will appear here."
        isExpanded={expandedSections.has("central")}
        onToggle={() => toggleSection("central")}
      />
    </div>
  );
}
