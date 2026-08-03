"use client";

/**
 * Shared presentational dropdown for the note editor's two popups: wikilink
 * autocomplete (`[[`) and the slash-command palette (`/`, #146). Both use
 * the same absolutely-positioned-list-of-buttons shape and keyboard-nav
 * styling; NoteEditor.tsx owns the keyboard handling (Arrow/Enter/Escape)
 * and guarantees only one of the two is ever open at a time.
 */

import { ReactNode } from "react";
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
  if (items.length === 0) return null;

  return (
    <div
      className={styles.autocomplete}
      style={{ top: `${position.top}px`, left: `${position.left}px` }}
    >
      {items.map((item, index) => (
        <button
          key={item.key}
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
