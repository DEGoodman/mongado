/**
 * FilterSheet - shared mobile filter UI for KB list pages (#296).
 *
 * Desktop (>1024px): a transparent wrapper (`display: contents`), so the
 * children (sort, tag filter, clear-all) render exactly as sidebar content.
 * ≤1024px: a bottom sheet with a backdrop, opened by <FilterButton>.
 *
 * Children are rendered once; CSS does the switch, so there is no JS
 * media-query and no hydration flash.
 */

"use client";

import { forwardRef, useEffect, useRef } from "react";
import { SlidersHorizontal } from "@phosphor-icons/react";
import styles from "./FilterSheet.module.scss";

interface FilterButtonProps {
  activeCount: number;
  open: boolean;
  onClick: () => void;
}

/** "Filters (2)" trigger. Visible ≤1024px only. */
export const FilterButton = forwardRef<HTMLButtonElement, FilterButtonProps>(function FilterButton(
  { activeCount, open, onClick },
  ref
) {
  return (
    <button
      ref={ref}
      type="button"
      className={styles.filterButton}
      aria-haspopup="dialog"
      aria-expanded={open}
      onClick={onClick}
    >
      <SlidersHorizontal size={18} aria-hidden="true" />
      <span>Filters{activeCount > 0 ? ` (${activeCount})` : ""}</span>
    </button>
  );
});

/** Row holding the search input and the Filters button. */
export function FilterSearchRow({ children }: { children: React.ReactNode }) {
  return <div className={styles.searchRow}>{children}</div>;
}

interface FilterSheetProps {
  open: boolean;
  onClose: () => void;
  activeCount: number;
  onClearAll?: () => void;
  /** Trigger to return focus to when the sheet closes. */
  triggerRef?: React.RefObject<HTMLButtonElement | null>;
  children: React.ReactNode;
}

export default function FilterSheet({
  open,
  onClose,
  activeCount,
  onClearAll,
  triggerRef,
  children,
}: FilterSheetProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const wasOpen = useRef(false);

  // Escape closes; body scroll locked while open.
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      // aria-modal: keep Tab focus cycling inside the sheet
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), select, input, a[href], [tabindex]:not([tabindex="-1"])'
        )
      ).filter((el) => el.offsetParent !== null);
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (!panelRef.current.contains(active)) {
        // Focus strayed outside (e.g. Tab before the open-focus landed): pull it back in
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
      } else if (event.shiftKey && (active === first || active === panelRef.current)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  // Move focus in on open, back to the trigger on close.
  useEffect(() => {
    if (open) {
      panelRef.current?.focus();
    } else if (wasOpen.current) {
      triggerRef?.current?.focus();
    }
    wasOpen.current = open;
  }, [open, triggerRef]);

  return (
    <>
      <div className={styles.backdrop} data-open={open} onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        className={styles.panel}
        data-open={open}
        tabIndex={-1}
        role={open ? "dialog" : undefined}
        aria-modal={open ? "true" : undefined}
        aria-label={open ? "Filters" : undefined}
      >
        <div className={styles.sheetHeader}>
          <h2 className={styles.sheetTitle}>Filters</h2>
          {activeCount > 0 && onClearAll && (
            <button type="button" className={styles.clearAll} onClick={onClearAll}>
              Clear all
            </button>
          )}
          <button type="button" className={styles.done} onClick={onClose}>
            Done
          </button>
        </div>
        <div className={styles.body}>{children}</div>
      </div>
    </>
  );
}
