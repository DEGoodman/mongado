import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import HeaderMenu from "../components/HeaderMenu";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    className,
    onClick,
  }: {
    children: React.ReactNode;
    href: string;
    className?: string;
    onClick?: () => void;
  }) => (
    <a href={href} className={className} onClick={onClick}>
      {children}
    </a>
  ),
}));

const mockIsAuthenticated = vi.fn();
const mockClearAdminToken = vi.fn();
vi.mock("@/lib/api/client", () => ({
  isAuthenticated: () => mockIsAuthenticated(),
  clearAdminToken: () => mockClearAdminToken(),
}));

vi.mock("@/hooks/useFeatureFlags", () => ({
  useFeatureFlags: () => ({ llmFeaturesEnabled: true, loaded: true }),
}));

const mockUpdatePreferences = vi.fn();
vi.mock("@/hooks/useUserPreferences", () => ({
  useUserPreferences: () => ({
    preferences: { aiMode: "off" },
    updatePreferences: mockUpdatePreferences,
  }),
}));

const mockSetTheme = vi.fn();
vi.mock("@/hooks/useTheme", () => ({
  useTheme: () => ({ theme: "light", setTheme: mockSetTheme }),
}));

function openMenu() {
  fireEvent.click(screen.getByRole("button", { name: "Menu" }));
}

describe("HeaderMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated.mockReturnValue(false);
  });

  it("renders a single menu button, closed by default", () => {
    render(<HeaderMenu />);
    const button = screen.getByRole("button", { name: "Menu" });
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Theme")).not.toBeInTheDocument();
  });

  it("opens and closes on click", () => {
    render(<HeaderMenu />);
    openMenu();
    expect(screen.getByText("Theme")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Menu" }));
    expect(screen.queryByText("Theme")).not.toBeInTheDocument();
  });

  it("shows Sign In (and no admin/sign-out) when logged out", () => {
    render(<HeaderMenu />);
    openMenu();
    expect(screen.getByRole("link", { name: "Sign In" })).toHaveAttribute("href", "/login");
    expect(screen.queryByText("Admin Settings")).not.toBeInTheDocument();
    expect(screen.queryByText("Sign Out")).not.toBeInTheDocument();
  });

  it("shows Admin Settings link and Sign Out when logged in", () => {
    mockIsAuthenticated.mockReturnValue(true);
    render(<HeaderMenu />);
    openMenu();
    expect(screen.getByText("Admin User")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Admin Settings" })).toHaveAttribute(
      "href",
      "/admin"
    );
    expect(screen.getByRole("button", { name: "Sign Out" })).toBeInTheDocument();
    expect(screen.queryByText("Sign In")).not.toBeInTheDocument();
  });

  it("signs out: clears token and redirects to /login", () => {
    mockIsAuthenticated.mockReturnValue(true);
    render(<HeaderMenu />);
    openMenu();
    fireEvent.click(screen.getByRole("button", { name: "Sign Out" }));
    expect(mockClearAdminToken).toHaveBeenCalled();
    expect(mockPush).toHaveBeenCalledWith("/login");
  });

  it("theme segmented control calls setTheme", () => {
    render(<HeaderMenu />);
    openMenu();
    fireEvent.click(screen.getByRole("button", { name: "Dark" }));
    expect(mockSetTheme).toHaveBeenCalledWith("dark");
  });

  it("AI mode segmented control calls updatePreferences", () => {
    render(<HeaderMenu />);
    openMenu();
    fireEvent.click(screen.getByRole("button", { name: "On-demand" }));
    expect(mockUpdatePreferences).toHaveBeenCalledWith({ aiMode: "on-demand" });
  });
});
