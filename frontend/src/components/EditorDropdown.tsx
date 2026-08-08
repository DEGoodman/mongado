"use client";

/**
 * Shared presentational dropdown for the note editor's two popups: wikilink
 * autocomplete (`[[`) and the slash-command palette (`/`, #146). Both use
 * the same absolutely-positioned-list-of-buttons shape and keyboard-nav
 * styling; NoteEditor.tsx owns the keyboard handling (Arrow/Enter/Escape)
 * and guarantees only one of the two is ever open at a time.
 *
 * As the caller moves `selectedIndex`, the highlight repaints first (React
 * commit) and then the list smooth-scrolls to center the highlighted item, so
 * it's always in view while navigating with the keyboard without the jittery
 * scroll-then-highlight effect (#285). Centering (clamped by the browser)
 * naturally pins the first item to the top and the last item to the bottom.
 * Reduced-motion users get an instant jump instead of the animation.
 */

import { ReactNode, useEffect, useRef } from "react";
import styles from "./NoteEditor.module.scss";

export interface EditorDropdownItem {
  key: string;
  onSelect: () => void;
  content: ReactNode;
  disabled?: boolean;
}

interface EditorDropdownProps {
  position: { top: number; left: number };
  items: EditorDropdownItem[];
  selectedIndex: number;
}

export default function EditorDropdown({ position, items, selectedIndex }: EditorDropdownProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Keep the highlighted item centered within the scroll window (#285). Runs
  // after the commit that repaints the highlight, so the item moves first and
  // the scroll follows.
  useEffect(() => {
    const container = containerRef.current;
    const item = itemRefs.current[selectedIndex];
    if (!container || !item) return;

    // Center the item; the browser clamps scrollTop so the first item stays
    // at the top and the last item stays at the bottom.
    const top = item.offsetTop - (container.clientHeight - item.offsetHeight) / 2;
    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    container.scrollTo({ top, behavior: prefersReducedMotion ? "auto" : "smooth" });
  }, [selectedIndex, items.length]);

  if (items.length === 0) return null;

  return (
    <div
      ref={containerRef}
      className={styles.autocomplete}
      style={{ top: `${position.top}px`, left: `${position.left}px` }}
    >
      {items.map((item, index) => (
        <button
          key={item.key}
          ref={(el) => {
            itemRefs.current[index] = el;
          }}
          type="button"
          onClick={item.onSelect}
          disabled={item.disabled}
          className={`${styles.autocompleteItem} ${index === selectedIndex ? styles.selected : ""}`}
        >
          {item.content}
        </button>
      ))}
    </div>
  );
}
