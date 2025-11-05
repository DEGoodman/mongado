# Design Tokens Reference

Complete reference for all design tokens in the Mongado design system.

## Table of Contents

- [Overview](#overview)
- [Colors](#colors)
- [Typography](#typography)
- [Spacing](#spacing)
- [Shadows](#shadows)
- [Borders](#borders)
- [Implementation](#implementation)

## Overview

Design tokens are the fundamental visual building blocks of the design system. They provide:

- **Consistency**: Reusable values across all components
- **Maintainability**: Change once, update everywhere
- **Theming**: Easy color scheme swaps
- **Accessibility**: Built-in contrast and spacing standards

**Token files location**: `frontend/src/styles/design-tokens/`

## Colors

See **[COLOR_PALETTE.md](COLOR_PALETTE.md)** for the complete color system documentation, including:
- Base palette (Tier 1)
- Semantic tokens (Tier 2)
- Usage guidelines
- Accessibility standards

**Quick reference**:
- Primary: Blue (`$blue-600` = `#2563eb`)
- Secondary: Purple (`$purple-600` = `#9333ea`)
- Neutrals: Gray scale (`$neutral-50` to `$neutral-900`)
- States: Green (success), Red (error), Amber (warning), Yellow (highlights)

## Typography

**File**: `frontend/src/styles/design-tokens/_typography.scss`

### Font Families

The design uses a **retro-modern** font stack with geometric sans-serif fonts:

| Token | Value | Usage |
|-------|-------|-------|
| `$font-family-primary` | Space Grotesk + fallbacks | Body text, headings, UI |
| `$font-family-mono` | Space Mono + fallbacks | Code blocks, technical content |

**Font loading**: Fonts are loaded via Next.js font loader in `app/layout.tsx`:
```typescript
const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  weight: ["400", "500", "600", "700"],
});
```

### Font Sizes

| Token | Size | Pixels | Usage |
|-------|------|--------|-------|
| `$font-size-xs` | 0.75rem | 12px | Captions, badges, small labels |
| `$font-size-sm` | 0.875rem | 14px | Secondary text, metadata |
| `$font-size-base` | 1rem | 16px | **Default body text** |
| `$font-size-lg` | 1.125rem | 18px | Large body, emphasized text |
| `$font-size-xl` | 1.25rem | 20px | H4, large labels |
| `$font-size-2xl` | 1.5rem | 24px | H3 |
| `$font-size-3xl` | 1.875rem | 30px | H2 |
| `$font-size-4xl` | 2.25rem | 36px | H1 |
| `$font-size-5xl` | 3rem | 48px | Hero text, marketing |

### Font Weights

| Token | Value | Usage |
|-------|-------|-------|
| `$font-weight-normal` | 400 | Body text |
| `$font-weight-medium` | 500 | Subtle emphasis, labels |
| `$font-weight-semibold` | 600 | Subheadings, important text |
| `$font-weight-bold` | 700 | Headings, strong emphasis |

### Line Heights

| Token | Value | Usage |
|-------|-------|-------|
| `$line-height-tight` | 1.25 | Headings, compact text |
| `$line-height-normal` | 1.5 | Standard text |
| `$line-height-relaxed` | 1.6 | **Body text** (comfortable reading) |
| `$line-height-loose` | 1.7 | Very spacious text |

### Letter Spacing

**Retro-inspired wider letter spacing** for that 80s geometric look:

| Token | Value | Usage |
|-------|-------|-------|
| `$letter-spacing-tight` | -0.01em | Tight spacing (rare) |
| `$letter-spacing-normal` | 0.01em | **Body text** (slightly wide) |
| `$letter-spacing-wide` | 0.025em | Headings H2-H6 |
| `$letter-spacing-wider` | 0.04em | Large headings (H1) |

### Heading Scales

Each heading level has predefined size, weight, line-height, and letter-spacing:

| Heading | Size | Weight | Line Height | Letter Spacing |
|---------|------|--------|-------------|----------------|
| H1 | `$font-size-4xl` (36px) | Bold (700) | Tight (1.25) | Wider (0.04em) |
| H2 | `$font-size-3xl` (30px) | Bold (700) | Tight (1.25) | Wide (0.025em) |
| H3 | `$font-size-2xl` (24px) | Semibold (600) | Normal (1.5) | Normal (0.01em) |
| H4 | `$font-size-xl` (20px) | Semibold (600) | Normal (1.5) | Normal (0.01em) |
| H5 | `$font-size-lg` (18px) | Medium (500) | Normal (1.5) | Normal (0.01em) |
| H6 | `$font-size-base` (16px) | Medium (500) | Normal (1.5) | Normal (0.01em) |

### Body Text

| Token | Value |
|-------|-------|
| `$body-size` | `$font-size-base` (16px) |
| `$body-weight` | `$font-weight-normal` (400) |
| `$body-line-height` | `$line-height-relaxed` (1.6) |
| `$body-letter-spacing` | `$letter-spacing-normal` (0.01em) |

**Why 1.6 line-height?** Provides generous breathing room for comfortable reading, matching modern best practices.

## Spacing

**File**: `frontend/src/styles/design-tokens/_spacing.scss`

### Base Spacing Scale

Built on **4px base unit** for consistency:

| Token | Size | Pixels | Visual |
|-------|------|--------|--------|
| `$spacing-1` | 0.25rem | 4px | ▪ |
| `$spacing-2` | 0.5rem | 8px | ▪▪ |
| `$spacing-3` | 0.75rem | 12px | ▪▪▪ |
| `$spacing-4` | 1rem | 16px | ▪▪▪▪ |
| `$spacing-5` | 1.25rem | 20px | ▪▪▪▪▪ |
| `$spacing-6` | 1.5rem | 24px | ▪▪▪▪▪▪ |
| `$spacing-8` | 2rem | 32px | ▪▪▪▪▪▪▪▪ |
| `$spacing-10` | 2.5rem | 40px | Large spacing |
| `$spacing-12` | 3rem | 48px | Section spacing |
| `$spacing-16` | 4rem | 64px | Large sections |
| `$spacing-20` | 5rem | 80px | Hero spacing |
| `$spacing-24` | 6rem | 96px | Page sections |

### Semantic Spacing

Purpose-based spacing tokens for common use cases:

| Token | Maps To | Pixels | Usage |
|-------|---------|--------|-------|
| `$spacing-xs` | `$spacing-1` | 4px | Tight spacing |
| `$spacing-sm` | `$spacing-2` | 8px | Small gaps |
| `$spacing-md` | `$spacing-4` | 16px | **Default spacing** |
| `$spacing-lg` | `$spacing-6` | 24px | Large gaps |
| `$spacing-xl` | `$spacing-8` | 32px | Extra large spacing |
| `$spacing-2xl` | `$spacing-12` | 48px | Section spacing |
| `$spacing-3xl` | `$spacing-16` | 64px | Page section spacing |

### Component-Specific Spacing

#### Container Padding

| Token | Value | Pixels |
|-------|-------|--------|
| `$container-padding-mobile` | `$spacing-4` | 16px |
| `$container-padding-tablet` | `$spacing-6` | 24px |
| `$container-padding-desktop` | `$spacing-8` | 32px |

#### Card Padding

| Token | Value | Pixels | Usage |
|-------|-------|--------|-------|
| `$card-padding-sm` | `$spacing-3` | 12px | Compact cards |
| `$card-padding-md` | `$spacing-4` | 16px | **Default cards** |
| `$card-padding-lg` | `$spacing-6` | 24px | Spacious cards |

#### Button Padding

| Size | Vertical | Horizontal | Pixels |
|------|----------|------------|--------|
| Small | `$button-padding-y-sm` | `$button-padding-x-sm` | 4px × 12px |
| Medium | `$button-padding-y-md` | `$button-padding-x-md` | 8px × 16px |
| Large | `$button-padding-y-lg` | `$button-padding-x-lg` | 12px × 24px |

#### Gap Spacing (Flex/Grid)

| Token | Value | Pixels | Usage |
|-------|-------|--------|-------|
| `$gap-xs` | `$spacing-1` | 4px | Tight layouts |
| `$gap-sm` | `$spacing-2` | 8px | Small gaps |
| `$gap-md` | `$spacing-4` | 16px | **Default gap** |
| `$gap-lg` | `$spacing-6` | 24px | Large gaps |
| `$gap-xl` | `$spacing-8` | 32px | Extra large gaps |

## Shadows

**File**: `frontend/src/styles/design-tokens/_shadows.scss`

The shadow system uses **warm orange-tinted shadows** for a retro aesthetic, combined with charcoal for depth.

### Base Shadow Colors

| Token | Value | Description |
|-------|-------|-------------|
| `$shadow-color-warm` | `rgba(230, 126, 66, 0.08)` | Light orange tint |
| `$shadow-color-warm-md` | `rgba(230, 126, 66, 0.12)` | Medium orange tint |
| `$shadow-color-warm-lg` | `rgba(230, 126, 66, 0.16)` | Strong orange tint |
| `$shadow-color-charcoal` | `rgba(45, 45, 40, 0.12)` | Warm charcoal |
| `$shadow-color-charcoal-md` | `rgba(45, 45, 40, 0.15)` | Medium charcoal |
| `$shadow-color-charcoal-lg` | `rgba(45, 45, 40, 0.2)` | Strong charcoal |

### Card Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `$shadow-card-sm` | `0 2px 8px $shadow-color-warm` | Resting cards |
| `$shadow-card-md` | `0 4px 16px $shadow-color-warm-md` | Hover/elevated cards |
| `$shadow-card-lg` | `0 8px 24px $shadow-color-warm-lg` | Modals, popovers |

### Button Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `$shadow-button` | `0 1px 3px $shadow-color-charcoal` | Default state |
| `$shadow-button-hover` | `0 2px 6px $shadow-color-charcoal-md` | Hover state |
| `$shadow-button-active` | `inset 0 2px 4px $shadow-color-charcoal` | Active/pressed |

### Dropdown/Popover Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `$shadow-dropdown` | `0 4px 20px $shadow-color-charcoal-md` | Dropdown menus |
| `$shadow-popover` | `0 8px 32px $shadow-color-charcoal-lg` | Popovers, tooltips |

### Dual-Tone Shadows

**Retro aesthetic**: Combines orange warmth with charcoal depth:

| Token | Value | Usage |
|-------|-------|-------|
| `$shadow-dual-sm` | Warm + charcoal (2px + 2px) | Subtle dual-tone |
| `$shadow-dual-md` | Warm + charcoal (4px + 4px) | Medium dual-tone |
| `$shadow-dual-lg` | Warm + charcoal (8px + 8px) | Strong dual-tone |

### Focus Shadows

For keyboard navigation accessibility:

| Token | Value | Usage |
|-------|-------|-------|
| `$shadow-focus` | `0 0 0 2px $shadow-color-warm-lg` | Generic focus |
| `$shadow-focus-primary` | `0 0 0 2px rgba(230, 126, 66, 0.3)` | Primary elements |

### Inset Shadows

For inputs and pressed states:

| Token | Value | Usage |
|-------|-------|-------|
| `$shadow-inset` | `inset 0 2px 4px rgba(45, 45, 40, 0.06)` | Inputs |
| `$shadow-inset-strong` | `inset 0 2px 6px rgba(45, 45, 40, 0.1)` | Pressed buttons |

## Borders

**File**: `frontend/src/styles/design-tokens/_borders.scss`

### Border Radius

| Token | Size | Pixels | Usage |
|-------|------|--------|-------|
| `$border-radius-sm` | 0.25rem | 4px | Tags, small badges |
| `$border-radius-md` | 0.375rem | 6px | Buttons |
| `$border-radius-lg` | 0.5rem | 8px | Cards |
| `$border-radius-xl` | 0.625rem | 10px | Large cards |
| `$border-radius-2xl` | 0.75rem | 12px | Sections, modals |
| `$border-radius-full` | 9999px | Fully rounded | Pills, avatars |

### Semantic Border Radius

| Token | Maps To | Pixels | Usage |
|-------|---------|--------|-------|
| `$border-radius-tag` | `$border-radius-sm` | 4-6px | Tags |
| `$border-radius-button` | `$border-radius-md` | 6-8px | Buttons |
| `$border-radius-card` | `$border-radius-lg` | 8-10px | **Cards** |
| `$border-radius-section` | `$border-radius-2xl` | 12px | Sections |

### Border Widths

| Token | Value | Usage |
|-------|-------|-------|
| `$border-width-thin` | 1px | **Default borders** |
| `$border-width-medium` | 2px | Focus states, emphasis |
| `$border-width-thick` | 3px | Strong emphasis |

### Border Styles

Predefined border declarations:

| Token | Value | Usage |
|-------|-------|-------|
| `$border-default` | `1px solid $color-border` | Default borders |
| `$border-card` | `1px solid $color-border` | Card borders |
| `$border-focus` | `2px solid $color-primary` | Focus states |
| `$border-divider` | `1px solid $color-border` | Horizontal rules |

### Quick Lists Borders

Colored borders for note categories:

| Token | Value | Usage |
|-------|-------|-------|
| `$border-orphan` | `1px solid $color-orphan-border` | Orphan notes (yellow) |
| `$border-hub` | `1px solid $color-hub-border` | Hub notes (blue) |
| `$border-central` | `1px solid $color-central-border` | Central notes (purple) |

## Implementation

### Using Design Tokens

**In SCSS files:**

```scss
// Import design tokens
@use '@/styles/design-tokens' as *;

.myComponent {
  // Colors
  background-color: $color-surface-default;
  color: $color-text-primary;

  // Typography
  font-family: $font-family-primary;
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  line-height: $line-height-relaxed;

  // Spacing
  padding: $spacing-md;
  margin-bottom: $spacing-lg;
  gap: $gap-md;

  // Borders
  border: $border-default;
  border-radius: $border-radius-card;

  // Shadows
  box-shadow: $shadow-card-sm;

  // Hover state
  &:hover {
    box-shadow: $shadow-card-md;
    transform: translateY(-2px);
  }
}
```

**CSS Modules pattern:**

```scss
// MyComponent.module.scss
@use '@/styles/design-tokens' as *;
@use '@/styles/mixins' as *;

.container {
  @include flex-column;
  gap: $gap-lg;
  padding: $container-padding-desktop;
}

.heading {
  @include heading-h2;
  color: $color-text-heading;
  margin-bottom: $spacing-md;
}

.card {
  background: $color-surface-elevated;
  border: $border-card;
  border-radius: $border-radius-card;
  box-shadow: $shadow-card-sm;
  padding: $card-padding-md;
}
```

### Token Hierarchies

**Use semantic tokens over base palette:**

```scss
// ❌ Avoid base palette directly
.button {
  background-color: $blue-600;
}

// ✅ Use semantic tokens
.button {
  background-color: $color-interactive-primary;
}
```

**Why?** Semantic tokens make theming easy—changing `$color-interactive-primary` from blue to orange updates all primary buttons automatically.

### Responsive Spacing

Spacing tokens work with responsive design:

```scss
.container {
  padding: $container-padding-mobile;

  @media (min-width: 768px) {
    padding: $container-padding-tablet;
  }

  @media (min-width: 1024px) {
    padding: $container-padding-desktop;
  }
}
```

### Design Token Files

| File | Purpose | Exports |
|------|---------|---------|
| `_colors.scss` | Color palette and semantic tokens | All color variables |
| `_typography.scss` | Font families, sizes, weights, spacing | Typography scales |
| `_spacing.scss` | Spacing scale, gaps, padding | Spacing variables |
| `_shadows.scss` | Shadow styles for depth | Shadow declarations |
| `_borders.scss` | Border radius, widths, styles | Border variables |
| `_index.scss` | Barrel export file | Forwards all tokens |

### Import Pattern

**Always import from the index:**

```scss
// ✅ Correct - import all tokens at once
@use '@/styles/design-tokens' as *;

// ❌ Avoid - importing individual files
@use '@/styles/design-tokens/colors' as *;
@use '@/styles/design-tokens/spacing' as *;
```

## Related Documentation

- **[COLOR_PALETTE.md](COLOR_PALETTE.md)** - Complete color system reference
- **[COMPONENT_REFERENCE.md](COMPONENT_REFERENCE.md)** - Component usage and patterns
- **[THEME_CUSTOMIZATION.md](THEME_CUSTOMIZATION.md)** - Creating and swapping themes

---

**Questions or suggestions?** Open an issue on GitHub or refer to the design system documentation.
