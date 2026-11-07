/**
 * OverflowMenu - "⋯" button that opens a small popover list of actions.
 *
 * Used by PageHeader on phones to tuck secondary actions away (#296).
 * Closes on outside click, Escape (focus returns to the trigger), and
 * item activation.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { DotsThree } from "@phosphor-icons/react";
import styles from "./OverflowMenu.module.scss";

export interface OverflowMenuItem {
  label: string;
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
}

interface OverflowMenuProps {
  items: OverflowMenuItem[];
  /** Accessible name for the trigger button. */
  label?: string;
  className?: string;
}

export default function OverflowMenu({
  items,
  label = "More actions",
  className = "",
}: OverflowMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  if (items.length === 0) return null;

  return (
    <div className={`${styles.container} ${className}`} ref={containerRef}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.trigger}
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        <DotsThree size={22} weight="bold" aria-hidden="true" />
      </button>

      {isOpen && (
        <div className={styles.menu} role="menu" aria-label={label}>
          {items.map((item) =>
            item.href && !item.disabled ? (
              <Link
                key={item.label}
                href={item.href}
                role="menuitem"
                className={styles.item}
                onClick={() => {
                  setIsOpen(false);
                  item.onClick?.();
                }}
              >
                {item.label}
              </Link>
            ) : (
              <button
                key={item.label}
                type="button"
                role="menuitem"
                className={styles.item}
                disabled={item.disabled}
                onClick={() => {
                  setIsOpen(false);
                  item.onClick?.();
                }}
              >
                {item.label}
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
}
