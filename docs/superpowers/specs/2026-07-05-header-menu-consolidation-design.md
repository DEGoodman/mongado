# Header Menu Consolidation — Design

**Date:** 2026-07-05
**Status:** Approved

## Problem

The Knowledge Base header's right cluster is four separately-styled controls (Search, ThemeToggle, Settings gear, UserMenu) with inconsistent padding, borders, and icon treatment. The user button uses a raw 👤 emoji next to an SVG chevron, which misaligns. There is no header path to the `/admin` page — it requires manually typing the URL. The AI-settings dropdown's "On-demand" segment label wraps to two lines. `SettingsDropdown.tsx` is dead code duplicating `Settings.tsx`.

## Solution

Consolidate ThemeToggle + Settings + UserMenu into a single `HeaderMenu` dropdown. The header right cluster becomes two controls: Search and the menu button.

### Header controls

- **Search**: unchanged behavior — bordered pill, `MagnifyingGlass` icon + "Search" label + `⌘K` kbd; label hides ≤640px, kbd hides ≤768px.
- **Menu button**: borderless ghost icon button, 36×36, subtle hover background (`$neutral-50` token). Icon: Phosphor `User` (18px) when authenticated, `GearSix` (18px) when not. No chevron. `aria-label="Menu"`, `aria-expanded`.

### Dropdown contents (top → bottom, divider between sections)

1. **Account**
   - Signed in: "Admin User" name label, **Admin Settings** link (`/admin`), **Sign Out** button (existing `clearAdminToken` + redirect to `/login`).
   - Signed out: **Sign In** link (`/login`).
2. **Appearance**
   - "Theme" row with Light / Dark segmented control, reusing the existing segmented-control visual pattern. Backed by the existing logic (localStorage `theme`, `document.documentElement.dataset.theme`, OS-preference fallback) extracted into a `useTheme` hook.
3. **AI Suggestions**
   - Off / On-demand / Automatic segmented control + mode description, moved from `Settings.tsx` as-is (including Ollama warmup on off→enabled transition and `useFeatureFlags` gating). Segment buttons get `white-space: nowrap` to fix label wrapping. When `llmFeaturesEnabled` is false, section shows the "not available" note instead.

Dropdown: right-aligned, ~280px wide, `max-width: calc(100vw - 2 * $spacing-4)` so it never overflows on mobile. Tighter padding than the current 320px UserMenu dropdown. Existing slide-down animation and click-outside-to-close behavior.

### Mobile (≤640px)

- Right cluster shrinks from 4 controls to 2; row 1 (logo + search + menu) fits without wrapping pressure. The two-row layout with scrollable nav links (issue #195 fix) is unchanged.
- Touch targets ≥40px inside the dropdown.
- Verify visually at 375px, 768px, and desktop widths.

### Code changes

| File | Change |
|---|---|
| `components/HeaderMenu.tsx` + `.module.scss` | New — consolidated menu |
| `hooks/useTheme.ts` | New — theme state extracted from `ThemeToggle` |
| `components/TopNavigation.tsx` | Replace `<ThemeToggle /> <Settings /> <UserMenu />` with `<HeaderMenu />` |
| `components/ThemeToggle.tsx` | Keep (used standalone on homepage `app/page.tsx`); refactor onto `useTheme` |
| `components/Settings.tsx` + `.module.scss` | Delete |
| `components/UserMenu.tsx` + `.module.scss` | Delete |
| `components/SettingsDropdown.tsx` + `.module.scss` | Delete (dead code) |
| `__tests__/TopNavigation.test.tsx` | Update for new structure |

All styling uses existing design tokens per `docs/DESIGN.md` (grey/orange palette, theme-aware tokens). No backend changes.

### Trade-offs accepted

- Theme toggle becomes two clicks instead of one (user approved).
- Signed-out users see a gear icon whose menu contains Sign In — acceptable since settings (AI mode, theme) are available to everyone.

### Testing

- Component test: menu opens/closes, shows Sign In when unauthenticated, shows Admin Settings + Sign Out when authenticated, theme and AI-mode controls render.
- Existing `useTheme` behavior covered by refactored ThemeToggle usage.
- Manual browser verification (light + dark themes, 375/768/desktop widths) before completion.
