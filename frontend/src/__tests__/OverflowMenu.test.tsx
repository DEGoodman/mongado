/**
 * Tests for OverflowMenu (#296): open/close behavior and item activation.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import OverflowMenu from "../components/OverflowMenu";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

describe("OverflowMenu", () => {
  it("is closed by default and exposes menu semantics on the trigger", () => {
    render(<OverflowMenu items={[{ label: "Graph", href: "/graph" }]} />);
    const trigger = screen.getByRole("button", { name: "More actions" });
    expect(trigger).toHaveAttribute("aria-haspopup", "menu");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("opens and renders links and buttons as menuitems", () => {
    render(
      <OverflowMenu
        items={[
          { label: "Graph", href: "/graph" },
          { label: "Random", onClick: vi.fn() },
        ]}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "More actions" }));
    expect(screen.getByRole("button", { name: "More actions" })).toHaveAttribute(
      "aria-expanded",
      "true"
    );
    expect(screen.getAllByRole("menuitem")).toHaveLength(2);
    expect(screen.getByRole("menuitem", { name: "Graph" })).toHaveAttribute("href", "/graph");
  });

  it("runs onClick and closes on item activation", () => {
    const onClick = vi.fn();
    render(<OverflowMenu items={[{ label: "Random", onClick }]} />);
    fireEvent.click(screen.getByRole("button", { name: "More actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Random" }));
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("does not fire disabled items", () => {
    const onClick = vi.fn();
    render(<OverflowMenu items={[{ label: "Random", onClick, disabled: true }]} />);
    fireEvent.click(screen.getByRole("button", { name: "More actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Random" }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("closes on Escape and returns focus to the trigger", () => {
    render(<OverflowMenu items={[{ label: "Graph", href: "/graph" }]} />);
    const trigger = screen.getByRole("button", { name: "More actions" });
    fireEvent.click(trigger);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("menu")).toBeNull();
    expect(trigger).toHaveFocus();
  });

  it("closes on outside click", () => {
    render(<OverflowMenu items={[{ label: "Graph", href: "/graph" }]} />);
    fireEvent.click(screen.getByRole("button", { name: "More actions" }));
    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole("menu")).toBeNull();
  });
});
