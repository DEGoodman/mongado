/**
 * Tests for TopNavigation component
 *
 * Tests cover:
 * - Logo and section links rendering
 * - Active state based on pathname
 * - Search button and keyboard shortcut
 * - SearchModal integration
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TopNavigation from "../components/TopNavigation";

// Mock next/navigation
const mockPathname = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname(),
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    className,
  }: {
    children: React.ReactNode;
    href: string;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

// Mock child components to simplify testing
vi.mock("../components/Settings", () => ({
  default: () => <div data-testid="settings">Settings</div>,
}));

vi.mock("../components/UserMenu", () => ({
  default: () => <div data-testid="user-menu">UserMenu</div>,
}));

vi.mock("../components/SearchModal", () => ({
  default: ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) =>
    isOpen ? (
      <div data-testid="search-modal">
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

describe("TopNavigation", () => {
  beforeEach(() => {
    mockPathname.mockReturnValue("/knowledge-base");
  });

  describe("Logo", () => {
    it("renders logo linking to home", () => {
      render(<TopNavigation />);

      const logo = screen.getByText("Mongado");
      expect(logo.closest("a")).toHaveAttribute("href", "/");
    });
  });

  describe("Section Links", () => {
    it("renders Articles link", () => {
      render(<TopNavigation />);

      const articlesLink = screen.getByRole("link", { name: "Articles" });
      expect(articlesLink).toHaveAttribute("href", "/knowledge-base/articles");
    });

    it("renders Notes link", () => {
      render(<TopNavigation />);

      const notesLink = screen.getByRole("link", { name: "Notes" });
      expect(notesLink).toHaveAttribute("href", "/knowledge-base/notes");
    });

    it("highlights Articles when on articles section", () => {
      mockPathname.mockReturnValue("/knowledge-base/articles");
      render(<TopNavigation />);

      const articlesLink = screen.getByRole("link", { name: "Articles" });
      expect(articlesLink.className).toContain("active");

      const notesLink = screen.getByRole("link", { name: "Notes" });
      expect(notesLink.className).not.toContain("active");
    });

    it("highlights Notes when on notes section", () => {
      mockPathname.mockReturnValue("/knowledge-base/notes");
      render(<TopNavigation />);

      const notesLink = screen.getByRole("link", { name: "Notes" });
      expect(notesLink.className).toContain("active");

      const articlesLink = screen.getByRole("link", { name: "Articles" });
      expect(articlesLink.className).not.toContain("active");
    });

    it("highlights Articles when on article detail page", () => {
      mockPathname.mockReturnValue("/knowledge-base/articles/123");
      render(<TopNavigation />);

      const articlesLink = screen.getByRole("link", { name: "Articles" });
      expect(articlesLink.className).toContain("active");
    });

    it("highlights Notes when on note detail page", () => {
      mockPathname.mockReturnValue("/knowledge-base/notes/my-note");
      render(<TopNavigation />);

      const notesLink = screen.getByRole("link", { name: "Notes" });
      expect(notesLink.className).toContain("active");
    });

    it("no section highlighted on KB hub page", () => {
      mockPathname.mockReturnValue("/knowledge-base");
      render(<TopNavigation />);

      const articlesLink = screen.getByRole("link", { name: "Articles" });
      const notesLink = screen.getByRole("link", { name: "Notes" });

      expect(articlesLink.className).not.toContain("active");
      expect(notesLink.className).not.toContain("active");
    });
  });

  describe("Search Button", () => {
    it("renders search button with icon", () => {
      render(<TopNavigation />);

      expect(screen.getByText("🔍")).toBeInTheDocument();
    });

    it("renders search label", () => {
      render(<TopNavigation />);

      expect(screen.getByText("Search")).toBeInTheDocument();
    });

    it("shows keyboard shortcut hint", () => {
      render(<TopNavigation />);

      expect(screen.getByText("⌘K")).toBeInTheDocument();
    });

    it("opens search modal on click", () => {
      render(<TopNavigation />);

      const searchButton = screen.getByRole("button", { name: /open search/i });
      fireEvent.click(searchButton);

      expect(screen.getByTestId("search-modal")).toBeInTheDocument();
    });

    it("opens search modal on Cmd+K", async () => {
      render(<TopNavigation />);

      // Modal should not be open initially
      expect(screen.queryByTestId("search-modal")).not.toBeInTheDocument();

      // Simulate Cmd+K
      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByTestId("search-modal")).toBeInTheDocument();
      });
    });

    it("opens search modal on Ctrl+K", async () => {
      render(<TopNavigation />);

      // Simulate Ctrl+K (Windows/Linux)
      fireEvent.keyDown(document, { key: "k", ctrlKey: true });

      await waitFor(() => {
        expect(screen.getByTestId("search-modal")).toBeInTheDocument();
      });
    });

    it("closes search modal via onClose callback", async () => {
      render(<TopNavigation />);

      // Open modal
      const searchButton = screen.getByRole("button", { name: /open search/i });
      fireEvent.click(searchButton);

      expect(screen.getByTestId("search-modal")).toBeInTheDocument();

      // Close via the mock's close button
      const closeButton = screen.getByRole("button", { name: "Close" });
      fireEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByTestId("search-modal")).not.toBeInTheDocument();
      });
    });
  });

  describe("Right Section", () => {
    it("renders Settings component", () => {
      render(<TopNavigation />);

      expect(screen.getByTestId("settings")).toBeInTheDocument();
    });

    it("renders UserMenu component", () => {
      render(<TopNavigation />);

      expect(screen.getByTestId("user-menu")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has main navigation landmark", () => {
      render(<TopNavigation />);

      const nav = screen.getByRole("navigation");
      expect(nav).toHaveAttribute("aria-label", "Main navigation");
    });

    it("search button has aria-label", () => {
      render(<TopNavigation />);

      const searchButton = screen.getByRole("button", { name: /open search/i });
      expect(searchButton).toHaveAttribute("aria-label", "Open search");
    });
  });
});
