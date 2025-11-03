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
    expect(screen.getByText("Engineering Leader & Builder")).toBeInTheDocument();
  });

  it("shows location", () => {
    render(<Home />);
    expect(screen.getByText("Birmingham, AL")).toBeInTheDocument();
  });

  it("shows GitHub links", () => {
    render(<Home />);
    // Should have both the social button and the projects link
    const githubLinks = screen.getAllByRole("link", { name: /github/i });
    expect(githubLinks.length).toBeGreaterThanOrEqual(2);
    // Both should point to GitHub
    githubLinks.forEach((link) => {
      expect(link).toHaveAttribute("href", "https://github.com/DEGoodman");
    });
  });
});
