import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Home from "../app/page";

// Mock fetch
global.fetch = vi.fn();

describe("Home Page", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders the main heading", () => {
    (global.fetch as any).mockResolvedValueOnce({
      json: async () => ({ resources: [] }),
    });

    render(<Home />);
    expect(screen.getByText("Knowledge Base")).toBeInTheDocument();
  });

  it("shows empty state when no resources", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      json: async () => ({ resources: [] }),
    });

    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText("No resources yet")).toBeInTheDocument();
    });
  });

  it("shows Add Resource button", () => {
    (global.fetch as any).mockResolvedValueOnce({
      json: async () => ({ resources: [] }),
    });

    render(<Home />);
    expect(screen.getByRole("button", { name: /add resource/i })).toBeInTheDocument();
  });
});
