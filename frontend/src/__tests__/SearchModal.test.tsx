/**
 * Tests for SearchModal component
 *
 * Tests cover:
 * - Modal visibility and rendering
 * - Search input behavior
 * - Results display
 * - Keyboard interactions (Escape to close)
 * - Click outside to close
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import SearchModal from "../components/SearchModal";

// Mock next/link
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    onClick,
  }: {
    children: React.ReactNode;
    href: string;
    onClick?: () => void;
  }) => (
    <a href={href} onClick={onClick}>
      {children}
    </a>
  ),
}));

// Mock the logger
vi.mock("@/lib/logger", () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

// Mock fetch for API calls
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("SearchModal", () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ results: [], count: 0 }),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Visibility", () => {
    it("renders nothing when isOpen is false", () => {
      const { container } = render(<SearchModal isOpen={false} onClose={mockOnClose} />);
      expect(container.firstChild).toBeNull();
    });

    it("renders modal when isOpen is true", () => {
      render(<SearchModal isOpen={true} onClose={mockOnClose} />);
      expect(screen.getByPlaceholderText("Search articles and notes...")).toBeInTheDocument();
    });

    it("shows search icon", () => {
      render(<SearchModal isOpen={true} onClose={mockOnClose} />);
      expect(screen.getByText("🔍")).toBeInTheDocument();
    });

    it("shows escape hint", () => {
      render(<SearchModal isOpen={true} onClose={mockOnClose} />);
      expect(screen.getByText("esc")).toBeInTheDocument();
    });
  });

  describe("Search Input", () => {
    it("focuses input when modal opens", async () => {
      render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Search articles and notes...")).toHaveFocus();
      });
    });

    it("updates input value on typing", async () => {
      const user = userEvent.setup();
      render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      const input = screen.getByPlaceholderText("Search articles and notes...");
      await user.type(input, "test query");

      expect(input).toHaveValue("test query");
    });

    it("triggers search after debounce", async () => {
      const user = userEvent.setup();
      render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      const input = screen.getByPlaceholderText("Search articles and notes...");
      await user.type(input, "engineering");

      // Wait for debounce (300ms) + API call
      await waitFor(
        () => {
          expect(mockFetch).toHaveBeenCalledWith(
            expect.stringContaining("/api/search"),
            expect.objectContaining({
              method: "POST",
              body: expect.stringContaining("engineering"),
            })
          );
        },
        { timeout: 1000 }
      );
    });
  });

  describe("Results Display", () => {
    it("shows hint text when no search performed", () => {
      render(<SearchModal isOpen={true} onClose={mockOnClose} />);
      expect(
        screen.getByText("Start typing to search across all articles and notes")
      ).toBeInTheDocument();
    });

    it("shows no results message when search returns empty", async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ results: [], count: 0 }),
      });

      render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      const input = screen.getByPlaceholderText("Search articles and notes...");
      await user.type(input, "xyznonexistent");

      await waitFor(() => {
        expect(screen.getByText(/No results found for "xyznonexistent"/)).toBeInTheDocument();
      });
    });

    it("displays search results with correct structure", async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          results: [
            {
              id: "article-1",
              type: "article",
              title: "Engineering Article",
              content: "Full content here",
              snippet: "...contextual snippet...",
              score: 2.5,
            },
            {
              id: "note-1",
              type: "note",
              title: "Design Note",
              content: "Note content",
              snippet: "Note snippet here",
              score: 1.8,
            },
          ],
          count: 2,
        }),
      });

      render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      const input = screen.getByPlaceholderText("Search articles and notes...");
      await user.type(input, "query");

      await waitFor(() => {
        // Use regex or function matcher to handle text split by highlights
        expect(screen.getByText(/Engineering Article/)).toBeInTheDocument();
        expect(screen.getByText(/Design Note/)).toBeInTheDocument();
      });

      // Check icons for article vs note
      expect(screen.getByText("📚")).toBeInTheDocument();
      expect(screen.getByText("📝")).toBeInTheDocument();

      // Check snippets are displayed
      expect(screen.getByText("...contextual snippet...")).toBeInTheDocument();
      expect(screen.getByText("Note snippet here")).toBeInTheDocument();
    });

    it("links to correct paths for articles and notes", async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          results: [
            {
              id: "123",
              type: "article",
              title: "My Article Title",
              content: "Content",
              snippet: "Snippet",
              score: 1.0,
            },
            {
              id: "my-note",
              type: "note",
              title: "My Note Title",
              content: "Content",
              snippet: "Snippet",
              score: 1.0,
            },
          ],
          count: 2,
        }),
      });

      render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      const input = screen.getByPlaceholderText("Search articles and notes...");
      await user.type(input, "query");

      await waitFor(() => {
        // Get links by their href since text may be split by highlights
        const links = screen.getAllByRole("link");
        const articleLink = links.find((l) => l.getAttribute("href")?.includes("/articles/"));
        const noteLink = links.find((l) => l.getAttribute("href")?.includes("/notes/"));

        expect(articleLink).toHaveAttribute("href", "/knowledge-base/articles/123");
        expect(noteLink).toHaveAttribute("href", "/knowledge-base/notes/my-note");
      });
    });
  });

  describe("Closing Behavior", () => {
    it("closes on Escape key", async () => {
      render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      fireEvent.keyDown(document, { key: "Escape" });

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("closes on clicking overlay", () => {
      render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      // Find the overlay (first child with onClick)
      const overlay = screen.getByPlaceholderText("Search articles and notes...").parentElement
        ?.parentElement?.parentElement;

      if (overlay) {
        fireEvent.click(overlay);
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      }
    });

    it("does not close on clicking modal content", () => {
      render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      const input = screen.getByPlaceholderText("Search articles and notes...");
      fireEvent.click(input);

      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it("closes on clicking esc button", () => {
      render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      const escButton = screen.getByText("esc").parentElement;
      if (escButton) {
        fireEvent.click(escButton);
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      }
    });

    it("closes and navigates when clicking a result", async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          results: [
            {
              id: "123",
              type: "article",
              title: "Engineering Guide",
              content: "Content",
              snippet: "Snippet",
              score: 1.0,
            },
          ],
          count: 1,
        }),
      });

      render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      const input = screen.getByPlaceholderText("Search articles and notes...");
      await user.type(input, "query");

      await waitFor(() => {
        expect(screen.getByText(/Engineering Guide/)).toBeInTheDocument();
      });

      // Find the link by href since text may be split
      const resultLink = screen.getByRole("link");
      fireEvent.click(resultLink);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("State Reset", () => {
    it("clears search state when modal closes and reopens", async () => {
      const user = userEvent.setup();
      const { rerender } = render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      // Type something
      const input = screen.getByPlaceholderText("Search articles and notes...");
      await user.type(input, "test query");
      expect(input).toHaveValue("test query");

      // Close modal
      rerender(<SearchModal isOpen={false} onClose={mockOnClose} />);

      // Reopen modal
      rerender(<SearchModal isOpen={true} onClose={mockOnClose} />);

      // Input should be cleared
      const newInput = screen.getByPlaceholderText("Search articles and notes...");
      expect(newInput).toHaveValue("");
    });
  });

  describe("Error Handling", () => {
    it("displays error message on API failure", async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValue({
        ok: false,
        statusText: "Internal Server Error",
      });

      render(<SearchModal isOpen={true} onClose={mockOnClose} />);

      const input = screen.getByPlaceholderText("Search articles and notes...");
      await user.type(input, "test");

      await waitFor(() => {
        expect(screen.getByText(/Search failed: Internal Server Error/)).toBeInTheDocument();
      });
    });
  });
});
