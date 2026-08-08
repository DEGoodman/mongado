"use client";

/**
 * Shared presentational dropdown for the note editor's two popups: wikilink
 * autocomplete (`[[`) and the slash-command palette (`/`, #146). Both use
 * the same absolutely-positioned-list-of-buttons shape and keyboard-nav
 * styling; NoteEditor.tsx owns the keyboard handling (Arrow/Enter/Escape)
 * and guarantees only one of the two is ever open at a time.
 *
 * As the caller moves `selectedIndex`, we scroll the highlighted item to the
 * center of the visible window so it's always in view while navigating with
 * the keyboard (#285). Centering (clamped by the browser) naturally pins the
 * first item to the top and the last item to the bottom.
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

  // Keep the highlighted item centered within the scroll window (#285).
  useEffect(() => {
    const container = containerRef.current;
    const item = itemRefs.current[selectedIndex];
    if (!container || !item) return;

    // Center the item; the browser clamps scrollTop so the first item stays
    // at the top and the last item stays at the bottom.
    container.scrollTop = item.offsetTop - (container.clientHeight - item.offsetHeight) / 2;
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
