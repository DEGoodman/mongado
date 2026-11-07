/**
 * Tests for FilterSheet / FilterButton (#296).
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import FilterSheet, { FilterButton } from "../components/FilterSheet";

describe("FilterButton", () => {
  it("shows the active count only when non-zero", () => {
    const { rerender } = render(<FilterButton activeCount={0} open={false} onClick={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Filters" })).toBeInTheDocument();
    rerender(<FilterButton activeCount={2} open={false} onClick={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Filters (2)" })).toBeInTheDocument();
  });
});

describe("FilterSheet", () => {
  it("always renders its children once, without dialog semantics when closed", () => {
    render(
      <FilterSheet open={false} onClose={vi.fn()} activeCount={0}>
        <p>sort and tags</p>
      </FilterSheet>
    );
    expect(screen.getByText("sort and tags")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("is a labelled modal dialog when open and locks body scroll", () => {
    const { unmount } = render(
      <FilterSheet open onClose={vi.fn()} activeCount={0}>
        <p>content</p>
      </FilterSheet>
    );
    const dialog = screen.getByRole("dialog", { name: "Filters" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveFocus();
    expect(document.body.style.overflow).toBe("hidden");
    unmount();
    expect(document.body.style.overflow).toBe("");
  });

  it("closes via Done, Escape, and the backdrop", () => {
    const onClose = vi.fn();
    const { container } = render(
      <FilterSheet open onClose={onClose} activeCount={0}>
        <p>content</p>
      </FilterSheet>
    );
    fireEvent.click(screen.getByRole("button", { name: "Done" }));
    fireEvent.keyDown(document, { key: "Escape" });
    fireEvent.click(container.querySelector("[aria-hidden='true']") as HTMLElement);
    expect(onClose).toHaveBeenCalledTimes(3);
  });

  it("shows Clear all in the header only when filters are active", () => {
    const onClearAll = vi.fn();
    const { rerender } = render(
      <FilterSheet open onClose={vi.fn()} activeCount={0} onClearAll={onClearAll}>
        <p>content</p>
      </FilterSheet>
    );
    expect(screen.queryByRole("button", { name: "Clear all" })).toBeNull();
    rerender(
      <FilterSheet open onClose={vi.fn()} activeCount={1} onClearAll={onClearAll}>
        <p>content</p>
      </FilterSheet>
    );
    fireEvent.click(screen.getByRole("button", { name: "Clear all" }));
    expect(onClearAll).toHaveBeenCalledTimes(1);
  });

  it("returns focus to the trigger after closing", () => {
    const triggerRef = { current: null as HTMLButtonElement | null };
    const Harness = ({ open }: { open: boolean }) => (
      <>
        <button ref={(el) => void (triggerRef.current = el)}>Filters</button>
        <FilterSheet open={open} onClose={vi.fn()} activeCount={0} triggerRef={triggerRef}>
          <p>content</p>
        </FilterSheet>
      </>
    );
    const { rerender } = render(<Harness open />);
    rerender(<Harness open={false} />);
    expect(triggerRef.current).toHaveFocus();
  });
});
