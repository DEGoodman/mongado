/**
 * Tests for Breadcrumb component
 *
 * Tests cover:
 * - Correct link destinations based on section prop
 * - toHub prop behavior for list pages
 * - Accessibility attributes
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import Breadcrumb from "../components/Breadcrumb";

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

describe("Breadcrumb", () => {
  describe("Section Links (Detail Pages)", () => {
    it("links to /knowledge-base/articles for articles section", () => {
      render(<Breadcrumb section="articles" />);

      const link = screen.getByRole("link");
      expect(link).toHaveAttribute("href", "/knowledge-base/articles");
      expect(link).toHaveTextContent("← Back");
    });

    it("links to /knowledge-base/notes for notes section", () => {
      render(<Breadcrumb section="notes" />);

      const link = screen.getByRole("link");
      expect(link).toHaveAttribute("href", "/knowledge-base/notes");
      expect(link).toHaveTextContent("← Back");
    });
  });

  describe("Hub Links (List Pages)", () => {
    it("links to /knowledge-base when toHub is true for articles", () => {
      render(<Breadcrumb section="articles" toHub />);

      const link = screen.getByRole("link");
      expect(link).toHaveAttribute("href", "/knowledge-base");
      expect(link).toHaveTextContent("← Back");
    });

    it("links to /knowledge-base when toHub is true for notes", () => {
      render(<Breadcrumb section="notes" toHub />);

      const link = screen.getByRole("link");
      expect(link).toHaveAttribute("href", "/knowledge-base");
      expect(link).toHaveTextContent("← Back");
    });

    it("toHub=false (default) links to section list", () => {
      render(<Breadcrumb section="articles" toHub={false} />);

      const link = screen.getByRole("link");
      expect(link).toHaveAttribute("href", "/knowledge-base/articles");
    });
  });

  describe("Accessibility", () => {
    it("has accessible navigation landmark", () => {
      render(<Breadcrumb section="articles" />);

      const nav = screen.getByRole("navigation");
      expect(nav).toHaveAttribute("aria-label", "Breadcrumb");
    });

    it("link is keyboard accessible", () => {
      render(<Breadcrumb section="notes" />);

      const link = screen.getByRole("link");
      expect(link).toBeVisible();
      // Links are keyboard accessible by default
    });
  });

  describe("Custom className", () => {
    it("applies custom className", () => {
      render(<Breadcrumb section="articles" className="custom-class" />);

      const nav = screen.getByRole("navigation");
      expect(nav.className).toContain("custom-class");
    });
  });

  describe("Content", () => {
    it("always shows back arrow", () => {
      render(<Breadcrumb section="articles" />);
      expect(screen.getByText(/←/)).toBeInTheDocument();
    });

    it("always shows Back label", () => {
      render(<Breadcrumb section="notes" />);
      expect(screen.getByText(/Back/)).toBeInTheDocument();
    });
  });
});
