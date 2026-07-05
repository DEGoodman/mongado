# Header Menu Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the KB header's ThemeToggle + Settings + UserMenu with a single consolidated `HeaderMenu` dropdown (theme, AI settings, account actions incl. Admin link), and delete dead code.

**Architecture:** New `HeaderMenu` client component owns one dropdown with three sections (Account / Appearance / AI Suggestions). Theme write-logic is extracted from `ThemeToggle` into a shared `useTheme` hook; `ThemeToggle` stays (homepage uses it standalone) but is refactored onto the hook. `Settings.tsx`, `UserMenu.tsx`, and the already-dead `SettingsDropdown.tsx` are deleted.

**Tech Stack:** Next.js 14 app router, TypeScript strict, SCSS modules with design tokens (`@/styles/design-tokens`), Phosphor icons, Vitest + Testing Library. Everything runs via `docker compose` / `make`.

**Spec:** `docs/superpowers/specs/2026-07-05-header-menu-consolidation-design.md` — GitHub issue #219.

## Global Constraints

- All commands run in containers: `docker compose exec frontend <cmd>` (never bare `npm`/`npx` on host).
- All styling uses existing design tokens/mixins per `docs/DESIGN.md`; no hard-coded colors.
- TypeScript strict — no `any`.
- Frontend logging via `@/lib/logger`, never `console.log`.
- Work on branch `feat/header-menu-consolidation`; commits reference issue #219 in the final commit (`fixes #219`).
- Do NOT delete `hooks/useSettings.ts` (used by note pages) or `hooks/useResolvedTheme.ts` (read-only variant used elsewhere). Only the components listed in Task 4 are deleted.

---

### Task 1: `useTheme` hook + refactor `ThemeToggle` onto it

**Files:**
- Create: `frontend/src/hooks/useTheme.ts`
- Create: `frontend/src/__tests__/useTheme.test.tsx`
- Modify: `frontend/src/components/ThemeToggle.tsx`

**Interfaces:**
- Consumes: nothing new.
- Produces: `useTheme(): { theme: "light" | "dark" | null; setTheme: (t: "light" | "dark") => void }` and `export type Theme = "light" | "dark"` from `@/hooks/useTheme`. `theme` is `null` until mounted (SSR-safe). `setTheme` writes `document.documentElement.dataset.theme` and `localStorage["theme"]`.

- [ ] **Step 1: Create the branch**

```bash
git checkout -b feat/header-menu-consolidation
```

- [ ] **Step 2: Write the failing test**

Create `frontend/src/__tests__/useTheme.test.tsx`:

```tsx
import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { useTheme } from "../hooks/useTheme";

describe("useTheme", () => {
  beforeEach(() => {
    delete document.documentElement.dataset.theme;
    localStorage.clear();
  });

  it("resolves explicit data-theme after mount", async () => {
    document.documentElement.dataset.theme = "dark";
    const { result } = renderHook(() => useTheme());
    await waitFor(() => expect(result.current.theme).toBe("dark"));
  });

  it("falls back to light when no explicit theme and no dark OS preference", async () => {
    // jsdom matchMedia (mocked in setup) reports no dark preference
    const { result } = renderHook(() => useTheme());
    await waitFor(() => expect(result.current.theme).toBe("light"));
  });

  it("setTheme updates state, dataset, and localStorage", async () => {
    const { result } = renderHook(() => useTheme());
    await waitFor(() => expect(result.current.theme).not.toBeNull());

    act(() => result.current.setTheme("dark"));

    expect(result.current.theme).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem("theme")).toBe("dark");
  });
});
```

Note: if `window.matchMedia` is not already mocked in the Vitest setup file, check `frontend/vitest.setup.ts` (or the file named in `vitest.config.ts` `setupFiles`) and add the standard stub there if missing:

```ts
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      onchange: null,
      dispatchEvent: () => false,
    }) as MediaQueryList;
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `docker compose exec frontend npx vitest run src/__tests__/useTheme.test.tsx`
Expected: FAIL — cannot resolve `../hooks/useTheme`.

- [ ] **Step 4: Write the hook**

Create `frontend/src/hooks/useTheme.ts`:

```ts
/**
 * useTheme - read/write access to the light/dark theme.
 *
 * Resolution order: explicit choice (localStorage "theme", applied to
 * <html data-theme> by an inline script in the root layout before first
 * paint) wins, otherwise the OS preference applies. `theme` is null until
 * mounted because the server doesn't know the theme.
 *
 * For read-only live tracking (incl. OS changes), see useResolvedTheme.
 */

"use client";

import { useEffect, useState } from "react";

export type Theme = "light" | "dark";

function resolveInitialTheme(): Theme {
  const explicit = document.documentElement.dataset.theme;
  if (explicit === "light" || explicit === "dark") return explicit;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function useTheme(): { theme: Theme | null; setTheme: (next: Theme) => void } {
  const [theme, setThemeState] = useState<Theme | null>(null);

  useEffect(() => {
    setThemeState(resolveInitialTheme());
  }, []);

  const setTheme = (next: Theme): void => {
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Private browsing or blocked storage - the choice just won't persist
    }
    setThemeState(next);
  };

  return { theme, setTheme };
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker compose exec frontend npx vitest run src/__tests__/useTheme.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 6: Refactor `ThemeToggle` onto the hook**

Replace the body of `frontend/src/components/ThemeToggle.tsx` (keep the file header comment, styles import, and JSX) so state logic comes from the hook:

```tsx
/**
 * ThemeToggle - switches between light and dark ("phosphor") themes.
 *
 * Used standalone on the homepage (which has no TopNavigation). Theme
 * resolution/persistence lives in the useTheme hook.
 */

"use client";

import { Moon, Sun } from "@phosphor-icons/react";
import { useTheme } from "@/hooks/useTheme";
import styles from "./ThemeToggle.module.scss";

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const toggle = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  return (
    <button
      type="button"
      onClick={toggle}
      className={styles.toggle}
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
    >
      {theme === "dark" ? (
        <Sun size={18} aria-hidden="true" />
      ) : (
        <Moon size={18} aria-hidden="true" />
      )}
    </button>
  );
}
```

- [ ] **Step 7: Run full frontend test suite + typecheck**

Run: `make test-frontend && make typecheck-frontend`
Expected: PASS, no type errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/hooks/useTheme.ts frontend/src/__tests__/useTheme.test.tsx frontend/src/components/ThemeToggle.tsx frontend/vitest.setup.ts
git commit -m "refactor: extract theme state into useTheme hook (#219)"
```

(Omit `vitest.setup.ts` from the add if it wasn't modified.)

---

### Task 2: `HeaderMenu` component

**Files:**
- Create: `frontend/src/components/HeaderMenu.tsx`
- Create: `frontend/src/components/HeaderMenu.module.scss`
- Create: `frontend/src/__tests__/HeaderMenu.test.tsx`

**Interfaces:**
- Consumes: `useTheme` from Task 1; existing `useUserPreferences()` → `{ preferences: { aiMode: AiMode }, updatePreferences({ aiMode }) }`; `useFeatureFlags()` → `{ llmFeaturesEnabled: boolean, loaded: boolean }`; `isAuthenticated()`, `clearAdminToken()` from `@/lib/api/client`; `AiMode` type from `@/lib/settings`.
- Produces: `HeaderMenu` default-export React component, no props. Rendered by TopNavigation in Task 3.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/__tests__/HeaderMenu.test.tsx`:

```tsx
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec frontend npx vitest run src/__tests__/HeaderMenu.test.tsx`
Expected: FAIL — cannot resolve `../components/HeaderMenu`.

- [ ] **Step 3: Write the styles**

Create `frontend/src/components/HeaderMenu.module.scss`:

```scss
/**
 * HeaderMenu Component Styles
 * Single consolidated header dropdown: account, theme, AI settings.
 */

@use "@/styles/design-tokens" as *;
@use "@/styles/mixins" as *;

.container {
  position: relative;
}

// Borderless ghost icon button, 36x36 (40x40 touch target on mobile)
.menuButton {
  @include flex-center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: none;
  border-radius: $border-radius-md;
  background-color: transparent;
  color: $color-text-secondary;
  cursor: pointer;
  @include transition-default;

  &:hover {
    background-color: $neutral-50;
    color: $neutral-900;
  }

  &[aria-expanded="true"] {
    background-color: $neutral-100;
    color: $neutral-900;
  }

  &:focus-visible {
    outline: 2px solid $color-interactive-primary-focus;
    outline-offset: 2px;
  }

  @media (max-width: 640px) {
    width: 40px;
    height: 40px;
  }
}

.dropdown {
  position: absolute;
  top: calc(100% + $spacing-2);
  right: 0;
  width: 280px;
  max-width: calc(100vw - 2 * #{$spacing-4});
  background-color: $white;
  border: 1px solid $neutral-200;
  border-radius: $border-radius-lg;
  box-shadow: $shadow-dropdown;
  z-index: 50;
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdownContent {
  padding: $spacing-3;
}

.section {
  & + .section {
    margin-top: $spacing-3;
    padding-top: $spacing-3;
    border-top: 1px solid $neutral-200;
  }
}

.sectionLabel {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: $color-text-tertiary;
  margin: 0 0 $spacing-2;
}

.userName {
  font-size: 0.9375rem;
  font-weight: 600;
  color: $neutral-900;
  padding: $spacing-1 0 $spacing-2;
}

// Shared row style for Admin Settings / Sign In links (>=40px touch target)
.menuLink {
  display: flex;
  align-items: center;
  min-height: 40px;
  padding: $spacing-2 $spacing-3;
  font-size: 0.9375rem;
  color: $neutral-900;
  text-decoration: none;
  border-radius: $border-radius-md;
  @include transition-colors;

  &:hover {
    background-color: $neutral-50;
  }
}

.signOutButton {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 40px;
  padding: $spacing-2 $spacing-3;
  font-size: 0.9375rem;
  background: none;
  border: none;
  border-radius: $border-radius-md;
  color: $red-600;
  text-align: left;
  cursor: pointer;
  @include transition-colors;

  &:hover {
    background-color: $red-50;
    color: $red-700;
  }
}

.segmentedControl {
  @include flex-start;
  background-color: $neutral-100;
  border-radius: $border-radius-md;
  padding: $spacing-1;
  gap: $spacing-1;
}

.segmentButton {
  flex: 1;
  min-height: 32px;
  padding: $spacing-1 $spacing-2;
  font-size: 0.875rem;
  white-space: nowrap; // "On-demand" must not wrap (issue #219)
  border: none;
  border-radius: $border-radius-sm;
  cursor: pointer;
  @include transition-default;

  &.active {
    background-color: $white;
    color: $neutral-900;
    box-shadow: $shadow-card-sm;
    font-weight: 500;
  }

  &.inactive {
    background-color: transparent;
    color: $neutral-600;

    &:hover {
      color: $neutral-900;
    }
  }
}

.modeDescription {
  margin-top: $spacing-2;

  p {
    font-size: 0.8125rem;
    color: $neutral-600;
    margin: 0;
    line-height: 1.5;
  }
}

.warmupIndicator {
  font-size: 0.75rem;
  color: $color-text-secondary;
  margin-bottom: $spacing-2;
}
```

- [ ] **Step 4: Write the component**

Create `frontend/src/components/HeaderMenu.tsx`:

```tsx
/**
 * HeaderMenu - single consolidated header dropdown.
 *
 * Sections:
 * - Account: Sign In (logged out) OR name + Admin Settings + Sign Out (logged in)
 * - Appearance: Light/Dark theme segmented control
 * - AI Suggestions: Off / On-demand / Automatic (feature-flag gated)
 *
 * Replaces the former ThemeToggle + Settings + UserMenu header cluster.
 */

"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { User, GearSix } from "@phosphor-icons/react";
import { useTheme, type Theme } from "@/hooks/useTheme";
import { useUserPreferences } from "@/hooks/useUserPreferences";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import type { AiMode } from "@/lib/settings";
import { logger } from "@/lib/logger";
import { isAuthenticated, clearAdminToken } from "@/lib/api/client";
import styles from "./HeaderMenu.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function HeaderMenu() {
  const { llmFeaturesEnabled, loaded: flagsLoaded } = useFeatureFlags();
  const { preferences, updatePreferences } = useUserPreferences();
  const { theme, setTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [isUserAuthenticated, setIsUserAuthenticated] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Check authentication status on mount and when dropdown opens
  useEffect(() => {
    setIsUserAuthenticated(isAuthenticated());
  }, [isOpen]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  const warmupOllama = async () => {
    setIsWarmingUp(true);
    try {
      const response = await fetch(`${API_URL}/api/ollama/warmup`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Warmup failed");
      }

      logger.info("Ollama warmed up successfully");
    } catch (err) {
      logger.error("Failed to warm up Ollama", err);
      // Don't block the setting change - warmup will happen on first use
    } finally {
      setIsWarmingUp(false);
    }
  };

  const handleModeChange = async (newMode: AiMode) => {
    const oldMode = preferences.aiMode;
    updatePreferences({ aiMode: newMode });

    // Warmup if switching from "off" to an AI-enabled mode
    if (oldMode === "off" && (newMode === "on-demand" || newMode === "real-time")) {
      await warmupOllama();
    }
  };

  const handleLogout = () => {
    clearAdminToken();
    logger.info("User logged out");
    setIsOpen(false);
    router.push("/login");
  };

  const themeSegment = (value: Theme, label: string) => (
    <button
      onClick={() => setTheme(value)}
      className={`${styles.segmentButton} ${theme === value ? styles.active : styles.inactive}`}
    >
      {label}
    </button>
  );

  const aiSegment = (value: AiMode, label: string) => (
    <button
      onClick={() => handleModeChange(value)}
      className={`${styles.segmentButton} ${preferences.aiMode === value ? styles.active : styles.inactive}`}
    >
      {label}
    </button>
  );

  return (
    <div className={styles.container} ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={styles.menuButton}
        aria-label="Menu"
        aria-expanded={isOpen}
      >
        {isUserAuthenticated ? (
          <User size={18} aria-hidden="true" />
        ) : (
          <GearSix size={18} aria-hidden="true" />
        )}
      </button>

      {isOpen && (
        <div className={styles.dropdown}>
          <div className={styles.dropdownContent}>
            {/* Account */}
            <div className={styles.section}>
              {isUserAuthenticated ? (
                <>
                  <div className={styles.userName}>Admin User</div>
                  <Link
                    href="/admin"
                    className={styles.menuLink}
                    onClick={() => setIsOpen(false)}
                  >
                    Admin Settings
                  </Link>
                  <button onClick={handleLogout} className={styles.signOutButton}>
                    Sign Out
                  </button>
                </>
              ) : (
                <Link href="/login" className={styles.menuLink} onClick={() => setIsOpen(false)}>
                  Sign In
                </Link>
              )}
            </div>

            {/* Appearance */}
            <div className={styles.section}>
              <h3 className={styles.sectionLabel}>Theme</h3>
              <div className={styles.segmentedControl}>
                {themeSegment("light", "Light")}
                {themeSegment("dark", "Dark")}
              </div>
            </div>

            {/* AI Suggestions */}
            <div className={styles.section}>
              <h3 className={styles.sectionLabel}>AI Suggestions</h3>
              {!flagsLoaded ? null : llmFeaturesEnabled ? (
                <>
                  {isWarmingUp && <div className={styles.warmupIndicator}>Warming up...</div>}
                  <div className={styles.segmentedControl}>
                    {aiSegment("off", "Off")}
                    {aiSegment("on-demand", "On-demand")}
                    {aiSegment("real-time", "Automatic")}
                  </div>
                  <div className={styles.modeDescription}>
                    {preferences.aiMode === "off" && (
                      <p>
                        No AI suggestions. Fast, minimal overhead. Pure Zettelkasten experience.
                      </p>
                    )}
                    {preferences.aiMode === "on-demand" && (
                      <p>
                        Click &quot;Get Suggestions&quot; when you want AI help. Balanced approach
                        with no overhead while writing.
                      </p>
                    )}
                    {preferences.aiMode === "real-time" && (
                      <p>
                        Automatically generate suggestions in the background as you type. Panel
                        stays collapsed until you open it.
                      </p>
                    )}
                  </div>
                </>
              ) : (
                <div className={styles.modeDescription}>
                  <p>AI features are not available in this environment.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker compose exec frontend npx vitest run src/__tests__/HeaderMenu.test.tsx`
Expected: PASS (7 tests).

- [ ] **Step 6: Typecheck and lint**

Run: `make typecheck-frontend && make lint-frontend`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/HeaderMenu.tsx frontend/src/components/HeaderMenu.module.scss frontend/src/__tests__/HeaderMenu.test.tsx
git commit -m "feat: add consolidated HeaderMenu dropdown (#219)"
```

---

### Task 3: Wire `HeaderMenu` into `TopNavigation`

**Files:**
- Modify: `frontend/src/components/TopNavigation.tsx` (imports at lines 33-35, right cluster at lines 123-125)
- Modify: `frontend/src/__tests__/TopNavigation.test.tsx` (component mocks at lines 38-45, "Right Section" tests at lines 209-221)

**Interfaces:**
- Consumes: `HeaderMenu` from Task 2.
- Produces: header right cluster is `Search + HeaderMenu` only.

- [ ] **Step 1: Update the TopNavigation test mocks (failing first)**

In `frontend/src/__tests__/TopNavigation.test.tsx`, replace the `Settings` and `UserMenu` mocks:

```tsx
// Mock child components to simplify testing
vi.mock("../components/HeaderMenu", () => ({
  default: () => <div data-testid="header-menu">HeaderMenu</div>,
}));
```

and replace the "Right Section" describe block:

```tsx
  describe("Right Section", () => {
    it("renders HeaderMenu component", () => {
      render(<TopNavigation />);

      expect(screen.getByTestId("header-menu")).toBeInTheDocument();
    });
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec frontend npx vitest run src/__tests__/TopNavigation.test.tsx`
Expected: FAIL — `header-menu` testid not found (TopNavigation still renders Settings/UserMenu).

- [ ] **Step 3: Update TopNavigation**

In `frontend/src/components/TopNavigation.tsx`:

Replace imports:

```tsx
import HeaderMenu from "./HeaderMenu";
```

(removing `import Settings from "./Settings";`, `import ThemeToggle from "./ThemeToggle";`, `import UserMenu from "./UserMenu";`)

Replace in the right cluster:

```tsx
            <ThemeToggle />
            <Settings />
            <UserMenu />
```

with:

```tsx
            <HeaderMenu />
```

Also update the component's doc comment (lines 8-9) to describe the single menu:

```tsx
 * - Header menu (theme, AI settings, account actions incl. Admin link)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose exec frontend npx vitest run src/__tests__/TopNavigation.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/TopNavigation.tsx frontend/src/__tests__/TopNavigation.test.tsx
git commit -m "feat: use consolidated HeaderMenu in top navigation (#219)"
```

---

### Task 4: Delete dead components

**Files:**
- Delete: `frontend/src/components/Settings.tsx`, `frontend/src/components/Settings.module.scss`
- Delete: `frontend/src/components/UserMenu.tsx`, `frontend/src/components/UserMenu.module.scss`
- Delete: `frontend/src/components/SettingsDropdown.tsx`, `frontend/src/components/SettingsDropdown.module.scss`

**Interfaces:**
- Consumes: Task 3 (nothing may reference these components anymore).
- Produces: nothing — removal only. Do NOT touch `hooks/useSettings.ts` or `hooks/useResolvedTheme.ts`.

- [ ] **Step 1: Verify nothing references the components**

Run: `grep -rn "components/Settings\"\|components/UserMenu\|components/SettingsDropdown\|from \"./Settings\"\|from \"./UserMenu\"\|from \"./SettingsDropdown\"" frontend/src`
Expected: no output. If there is output, fix those references before deleting.

- [ ] **Step 2: Delete the files**

```bash
git rm frontend/src/components/Settings.tsx frontend/src/components/Settings.module.scss \
       frontend/src/components/UserMenu.tsx frontend/src/components/UserMenu.module.scss \
       frontend/src/components/SettingsDropdown.tsx frontend/src/components/SettingsDropdown.module.scss
```

- [ ] **Step 3: Run full frontend CI**

Run: `make test-frontend && make lint-frontend && make typecheck-frontend && make build-frontend`
Expected: all pass, production build succeeds.

**WARNING (memory: build-frontend-breaks-dev):** `make build-frontend` clobbers the dev `.next` volume. After it succeeds, restore the dev server:

```bash
docker compose exec frontend sh -c "rm -rf .next/*"
docker compose restart frontend
```

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove Settings, UserMenu, and dead SettingsDropdown components (#219)"
```

---

### Task 5: Visual verification (desktop + mobile, light + dark)

**Files:** none (verification only; fix-ups as needed).

**Interfaces:**
- Consumes: running dev stack (`make up`), completed Tasks 1-4.
- Produces: verified UI; screenshots for the PR.

- [ ] **Step 1: Ensure the stack is running**

Run: `make up && make status`
Expected: backend, frontend, neo4j healthy. Frontend at `http://localhost:3000`.

- [ ] **Step 2: Browser check — desktop, logged out**

Using Chrome DevTools MCP: open `http://localhost:3000/knowledge-base/articles` at 1280px width. Verify:
- Right cluster is exactly two controls: Search pill + gear ghost button, vertically centered.
- Menu opens with Sign In / Theme / AI Suggestions sections; "On-demand" label does not wrap.
- Theme control switches light↔dark instantly and persists on reload.

- [ ] **Step 3: Browser check — desktop, logged in**

Sign in at `/login` (dev admin credentials — ask the user if unknown). Verify:
- Menu button icon becomes the User icon.
- Dropdown shows Admin User / Admin Settings / Sign Out; Admin Settings navigates to `/admin`.
- Sign Out clears session and redirects to `/login`.

- [ ] **Step 4: Browser check — mobile widths**

Resize to 375px and 768px. Verify:
- No horizontal page scroll; nav links row scrolls horizontally as before (issue #195 behavior intact).
- Dropdown fits within the viewport (no overflow past the right edge).
- Menu button touch target is 40px at ≤640px.

- [ ] **Step 5: Dark theme sweep**

Repeat steps 2-4 spot-checks in dark theme; confirm dropdown surfaces/borders use theme-aware colors (no white flashes).

- [ ] **Step 6: Homepage regression check**

Open `http://localhost:3000/`. Verify the standalone ThemeToggle still works (Task 1 refactor).

- [ ] **Step 7: Fix anything found, run `make ci`, then final commit**

Run: `make ci`
Expected: full pipeline passes.

```bash
git add -A
git commit -m "fix: header menu polish from visual verification (fixes #219)"
```

(If verification found nothing to fix, skip this commit — the issue closes via `fixes #219` in the PR description instead.)

- [ ] **Step 8: Offer PR**

Do not push without the user's explicit approval. Present branch summary and offer to open a PR referencing #219.
