# Design System

Mongado's visual identity: **future-retro, grey and orange**. Warm paper-grey
surfaces, cool grey text, a single orange interactive accent, Space Grotesk
for prose, Space Mono as the "terminal layer" for metadata. Dark mode is a
warm dark-grey ground where the orange reads as amber phosphor.

Established in [#198](https://github.com/DEGoodman/mongado/issues/198) /
[PR #199](https://github.com/DEGoodman/mongado/pull/199).

## Token architecture

Three layers, defined in `frontend/src/styles/`:

```
design-tokens/_colors.scss   Tier 1: raw scales (hex) + Tier 2: semantic tokens
themes.scss                  CSS custom properties: light + dark values
mixins/                      Typography, buttons, cards built on Tier 2
```

**Tier 1 — scales** (`$orange-500`, `$slate-blue-200`, …) are plain Sass hex
values. Safe inside `rgba()` and other Sass color functions. The legacy
Tailwind names (`$blue-*`, `$purple-*`, `$yellow-*`, `$amber-*`, `$green-*`)
still exist but are **aliases** into the collapsed palette (slate-blue /
mustard / sage). Don't use them in new code.

**Tier 2 — semantic tokens** (`$color-text-primary`, `$color-surface-default`,
`$color-interactive-primary`, …) resolve to `var(--color-*)` and are
**theme-aware**. Always prefer these. Because they are CSS variables at
runtime, they cannot be passed to Sass color functions — `rgba($color-x, .2)`
will not compile. Use a Tier 1 hex there instead.

**Themes** (`themes.scss`) define every custom property twice: on `:root`
(light) and under `:root[data-theme="dark"]` plus a
`prefers-color-scheme: dark` block for users with no stored choice.

### The `$white` caveat

`$white` is a **surface** color: it resolves to `var(--white)` and flips to a
dark surface in dark mode. Use it for card/input backgrounds. For text that
must stay white regardless of theme (e.g. on an orange button), use
`$color-interactive-primary-text` or literal `#fff`.

### The neutral ramp flips

`$neutral-50 … $neutral-900` invert in dark mode (50 stays "background-ish",
900 stays "text-ish"). Code written as "light background, dark text" with
neutrals is automatically correct in both themes.

## Color roles

| Role | Token | Rule |
|---|---|---|
| Interactive accent | `$color-interactive-primary` (orange) | Orange means "interact here" — one primary CTA per view, everything else is a ghost |
| Links | `$color-link-default` / `-hover` | Orange; never blue |
| Cool accent | slate-blue | Informational surfaces only (KB headers, info panels) |
| States | sage = success, mustard = warning, red = error, dusty-blue = info | Semantic only, never decorative |
| Category identity | typography, not hue | See mono labels below |

Selected/active chips use `$orange-700` background with `#fff` text (≥4.5:1
in both themes).

## Typography

- **Space Grotesk** (`$font-family-primary`) — headings and body. 16px base
  (`$font-size-base`); long-form reading is the site's core job, don't shrink it.
- **Space Mono** (`$font-family-mono`) — the metadata voice. Dates, reading
  time, note IDs, wikilinks, eyebrows, category labels. Mixins:
  - `@include text-meta-mono` — small mono metadata (dates, counts)
  - `@include text-label-mono` — uppercase mono labels (eyebrows, badges)

## Labels and icons

- Content types are uppercase mono chips, not emoji: `ART` (orange outline),
  `NOTE` (grey outline), `REF` (grey **dashed** outline = reference material).
- Icons come from [`@phosphor-icons/react`](https://phosphoricons.com/)
  (weight: regular, ~16–18px). No emoji in UI chrome; emoji in prose content
  is fine.
- **Keep `optimizePackageImports: ['@phosphor-icons/react']` in both
  `next.config.mjs` and `next.config.production.mjs`.** Without it, the
  package's barrel import drags all ~9,000 icons into every route that
  renders the nav (10k+ webpack modules, 10s+ dev compiles). Import icons
  from the package root as usual — the config rewrites them to per-icon
  entry points.

## Dark mode / theme toggle

- `ThemeToggle` (in `TopNavigation` and the homepage corner) sets
  `data-theme="light" | "dark"` on `<html>` and persists to
  `localStorage("theme")`. No stored choice → OS preference applies.
- An inline script in `app/layout.tsx` applies the stored theme before first
  paint. `<html>` carries `suppressHydrationWarning` because that attribute
  intentionally differs from the server render — removing it resurfaces a
  hydration error whose dev overlay swallows all page clicks.
- KB page headers share one gradient via `--color-header-bg-start/mid/end`
  and `--color-header-border`.
- The notes graph draws with hex constants for node/tag colors (chosen from
  the Tier 1 scales) and CSS variables for labels; if you add graph colors,
  pick from the scales in `_colors.scss`.

## Accessibility baseline

- Focus: `$shadow-focus-primary` ring or `outline` on `:focus-visible` —
  orange, visible in both themes.
- `prefers-reduced-motion` globally disables transitions/animations
  (`globals.scss`).
- `mark` highlights pin dark text explicitly (their background stays light in
  both themes).
- Body text ≥16px; mono metadata ≥12px; touch targets ~38px+.

## Checklist for new UI

1. Colors: Tier 2 semantic tokens only; no `$blue-*`/`$purple-*`, no literal
   light hexes for surfaces (they strand light panels on dark backgrounds).
2. One orange primary action per view; secondary actions are ghosts.
3. Metadata in mono via the mixins; category identity via labels, not hue.
4. Icons from Phosphor; no emoji in chrome.
5. Verify in **both themes** (toggle or `--color-scheme=dark` in Playwright)
   and at 390px width.
