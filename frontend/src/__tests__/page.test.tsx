import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Home from "../app/page";

describe("Home Page", () => {
  it("renders the main heading with name", () => {
    render(<Home />);
    expect(screen.getByText("D. Erik Goodman")).toBeInTheDocument();
  });

  it("shows engineering leader title", () => {
    render(<Home />);
    expect(screen.getByText(/Engineering Leader & Builder/)).toBeInTheDocument();
  });

  it("shows location", () => {
    render(<Home />);
    expect(screen.getAllByText(/Birmingham, AL/).length).toBeGreaterThan(0);
  });

  it("shows the GitHub social link", () => {
    render(<Home />);
    const githubLinks = screen.getAllByRole("link", { name: /github/i });
    expect(githubLinks.length).toBeGreaterThanOrEqual(1);
    githubLinks.forEach((link) => {
      expect(link).toHaveAttribute("href", "https://github.com/DEGoodman");
    });
  });

  it("links to the knowledge base via the card", () => {
    render(<Home />);
    const card = screen.getByRole("link", { name: /knowledge base/i });
    expect(card).toHaveAttribute("href", "/knowledge-base");
    expect(screen.getByText(/curated digital garden/i)).toBeInTheDocument();
  });
});
