# Theme Customization Guide

Complete guide for customizing and creating themes in the Mongado design system.

## Table of Contents

- [Overview](#overview)
- [Two-Tier Architecture](#two-tier-architecture)
- [Creating a New Theme](#creating-a-new-theme)
- [Theme Examples](#theme-examples)
- [Shadow System Customization](#shadow-system-customization)
- [Dark Mode Implementation](#dark-mode-implementation)
- [Accessibility Guidelines](#accessibility-guidelines)

## Overview

The Mongado design system uses a **two-tier color architecture** that makes theming straightforward:

1. **Tier 1 (Base Palette)**: Actual color values
2. **Tier 2 (Semantic Tokens)**: Purpose-based mappings to Tier 1

**To change themes**: Modify Tier 1 colors, and all semantic tokens automatically update.

**Current theme**: Clean blue-purple system with warm orange-tinted shadows

## Two-Tier Architecture

### Tier 1: Base Palette

Defined in `frontend/src/styles/design-tokens/_colors.scss`:

```scss
// Blues (Primary)
$blue-50: #eff6ff;
$blue-600: #2563eb;   // Primary CTA
$blue-700: #1d4ed8;   // Hover state

// Purples (Secondary)
$purple-50: #faf5ff;
$purple-600: #9333ea;  // Secondary CTA
$purple-700: #7e22ce;  // Hover state

// Neutrals (Grays)
$neutral-50: #f9fafb;
$neutral-800: #1f2937;  // Primary text
```

### Tier 2: Semantic Tokens

Map to Tier 1 colors by **purpose**, not hue:

```scss
// === INTERACTIVE ELEMENTS ===
$color-interactive-primary: $blue-600;             // Primary buttons
$color-interactive-primary-hover: $blue-700;       // Hover state
$color-interactive-primary-text: $white;           // Text on buttons

// === TEXT ===
$color-text-primary: $neutral-800;
$color-text-secondary: $neutral-600;

// === SURFACES ===
$color-surface-default: $white;
$color-surface-elevated: $white;
```

**Key insight**: Change `$blue-600` to orange, and all primary buttons become orange automatically.

## Creating a New Theme

### Step 1: Choose Your Palette

Pick a primary color, secondary color, and neutral scale. Ensure:
- **Contrast ratio** meets WCAG AA (4.5:1 minimum)
- **Color harmony**: Use complementary or analogous colors
- **Neutral scale**: 9 shades from light to dark

**Tools**:
- [Tailwind Color Generator](https://uicolors.app/create)
- [Coolors](https://coolors.co/)
- [Adobe Color](https://color.adobe.com/create/color-wheel)

### Step 2: Update Base Palette (Tier 1)

Edit `frontend/src/styles/design-tokens/_colors.scss`:

```scss
// BEFORE (Blue theme)
$blue-600: #2563eb;

// AFTER (Orange theme)
$blue-600: #ea580c;  // Now "blue-600" contains orange (rename if desired)
```

**Tip**: You can rename variables (e.g., `$primary-600` instead of `$blue-600`) for clarity.

### Step 3: Update Shadows (Optional)

Shadows use orange tints. Update to match your primary color in `_shadows.scss`:

```scss
// BEFORE (Orange shadows)
$shadow-color-warm: rgba(230, 126, 66, 0.08);

// AFTER (Blue shadows)
$shadow-color-warm: rgba(37, 99, 235, 0.08);  // Blue tint
```

### Step 4: Test Accessibility

Run contrast checks:

```bash
# Install contrast checker
npm install -g wcag-contrast

# Test primary color on white
wcag-contrast "#ea580c" "#ffffff"  # Should be ≥4.5:1
```

**Critical combinations** to test:
- Primary button text on primary background
- Body text on page background
- Link color on white
- Error/success text on respective backgrounds

### Step 5: Verify Components

Check that all components look good:

1. Buttons (primary, secondary, tertiary)
2. Cards (default, elevated)
3. Badges (article, note)
4. Links (default, visited, hover)
5. Forms (inputs, focus states)
6. Toasts and notifications

## Theme Examples

### Example 1: Warm Orange Theme

**Goal**: Retro 80s vibe with warm orange and terracotta.

**Changes**:

```scss
// frontend/src/styles/design-tokens/_colors.scss

// Primary: Orange (was blue)
$blue-50: #fff7ed;
$blue-100: #ffedd5;
$blue-600: #ea580c;    // Primary CTA (orange)
$blue-700: #c2410c;    // Hover state
$blue-800: #9a3412;    // Active state

// Secondary: Terracotta (was purple)
$purple-50: #fef2f2;
$purple-100: #fee2e2;
$purple-600: #dc2626;  // Secondary CTA (terracotta/red)
$purple-700: #b91c1c;  // Hover state

// Keep neutrals the same
// (no changes needed)
```

**Shadows** (match orange primary):

```scss
// frontend/src/styles/design-tokens/_shadows.scss

// Already orange-tinted! No changes needed.
$shadow-color-warm: rgba(230, 126, 66, 0.08);
```

**Result**: Warm, retro aesthetic with orange buttons and terracotta accents.

---

### Example 2: Cool Teal & Purple Theme

**Goal**: Modern, tech-focused with teal and purple.

**Changes**:

```scss
// frontend/src/styles/design-tokens/_colors.scss

// Primary: Teal
$blue-50: #f0fdfa;
$blue-100: #ccfbf1;
$blue-600: #0d9488;    // Primary CTA (teal)
$blue-700: #0f766e;    // Hover state
$blue-800: #115e59;    // Active state

// Secondary: Purple (keep existing or adjust)
$purple-50: #faf5ff;
$purple-600: #9333ea;  // Secondary CTA (purple)
$purple-700: #7e22ce;

// Neutrals: Cooler grays
$neutral-50: #f8fafc;   // Slate-50
$neutral-100: #f1f5f9;  // Slate-100
$neutral-800: #1e293b;  // Slate-800
$neutral-900: #0f172a;  // Slate-900
```

**Shadows** (update to teal tint):

```scss
// frontend/src/styles/design-tokens/_shadows.scss

// Change orange to teal
$shadow-color-warm: rgba(13, 148, 136, 0.08);      // Teal tint
$shadow-color-warm-md: rgba(13, 148, 136, 0.12);
$shadow-color-warm-lg: rgba(13, 148, 136, 0.16);
```

**Result**: Fresh, modern tech feel with teal and purple.

---

### Example 3: Monochrome (Gray Scale)

**Goal**: Minimalist black-and-white aesthetic.

**Changes**:

```scss
// frontend/src/styles/design-tokens/_colors.scss

// Primary: Dark Gray
$blue-50: #f9fafb;
$blue-600: #374151;    // Primary CTA (dark gray)
$blue-700: #1f2937;    // Hover state (darker)
$blue-800: #111827;    // Active state

// Secondary: Medium Gray
$purple-50: #f3f4f6;
$purple-600: #6b7280;  // Secondary CTA (medium gray)
$purple-700: #4b5563;

// Neutrals: Keep the same
// (already gray)
```

**Shadows** (neutral gray):

```scss
// frontend/src/styles/design-tokens/_shadows.scss

// Change to neutral gray
$shadow-color-warm: rgba(0, 0, 0, 0.08);
$shadow-color-warm-md: rgba(0, 0, 0, 0.12);
$shadow-color-warm-lg: rgba(0, 0, 0, 0.16);
```

**Result**: Elegant, minimalist monochrome design.

---

## Shadow System Customization

### Current Shadow System

Shadows use **warm orange tints** (`rgba(230, 126, 66, ...)`) for a retro feel:

```scss
// frontend/src/styles/design-tokens/_shadows.scss

$shadow-color-warm: rgba(230, 126, 66, 0.08);      // Orange tint
$shadow-color-charcoal: rgba(45, 45, 40, 0.12);    // Warm charcoal

$shadow-card-sm: 0 2px 8px $shadow-color-warm;
```

### Matching Shadows to Your Theme

**Option 1: Match Primary Color**

Use your primary color's RGB values:

```scss
// For teal primary (#0d9488)
$shadow-color-warm: rgba(13, 148, 136, 0.08);

// For orange primary (#ea580c)
$shadow-color-warm: rgba(234, 88, 12, 0.08);
```

**Option 2: Neutral Shadows**

Use black/gray for universal shadows:

```scss
$shadow-color-warm: rgba(0, 0, 0, 0.08);
$shadow-color-warm-md: rgba(0, 0, 0, 0.12);
$shadow-color-warm-lg: rgba(0, 0, 0, 0.16);
```

**Option 3: Dual-Tone Shadows**

Combine primary color + charcoal for depth:

```scss
// Teal + charcoal
$shadow-dual-md:
  0 4px 8px rgba(13, 148, 136, 0.12),   // Teal tint
  0 4px 16px rgba(45, 45, 40, 0.15);    // Charcoal depth
```

### Shadow Opacity Guidelines

| Opacity | Usage | Visual Weight |
|---------|-------|---------------|
| 0.04-0.08 | Subtle hints, resting cards | Very light |
| 0.10-0.15 | Hover states, elevated elements | Medium |
| 0.16-0.25 | Modals, popovers, dropdowns | Strong |

## Dark Mode Implementation

### Approach: CSS Variables

Convert tokens to CSS custom properties for runtime theme switching.

### Step 1: Define Light & Dark Palettes

```scss
// _colors.scss

// Light mode (current)
$light-bg: $white;
$light-text: $neutral-800;
$light-surface: $white;

// Dark mode
$dark-bg: $neutral-900;
$dark-text: $neutral-100;
$dark-surface: $neutral-800;
```

### Step 2: Create CSS Variables

```scss
// globals.scss

:root {
  // Light mode (default)
  --color-bg: #{$light-bg};
  --color-text: #{$light-text};
  --color-surface: #{$light-surface};
}

[data-theme="dark"] {
  // Dark mode
  --color-bg: #{$dark-bg};
  --color-text: #{$dark-text};
  --color-surface: #{$dark-surface};
}
```

### Step 3: Use CSS Variables

```scss
// Component.module.scss

.container {
  background-color: var(--color-bg);
  color: var(--color-text);
}

.card {
  background-color: var(--color-surface);
}
```

### Step 4: Toggle Dark Mode

```typescript
// ThemeToggle.tsx

function toggleTheme() {
  const root = document.documentElement;
  const current = root.getAttribute('data-theme');
  root.setAttribute('data-theme', current === 'dark' ? 'light' : 'dark');
}
```

### Dark Mode Color Adjustments

**Invert lightness, keep hue**:

| Light Mode | Dark Mode | Note |
|------------|-----------|------|
| `$blue-600` (primary) | `$blue-400` | Lighter for contrast |
| `$neutral-800` (text) | `$neutral-100` | Inverted |
| `$white` (bg) | `$neutral-900` | Inverted |
| `$neutral-200` (border) | `$neutral-700` | Subtle borders |

**Reduce saturation**: Dark mode colors should be slightly desaturated for comfort.

## Accessibility Guidelines

### Contrast Requirements

**WCAG AA standards** (minimum):
- **Normal text**: 4.5:1 contrast ratio
- **Large text** (18px+ or 14px+ bold): 3:1 contrast ratio
- **UI components**: 3:1 contrast ratio

**Test your colors**:
```bash
# Primary button (blue-600 on white)
wcag-contrast "#2563eb" "#ffffff"
# Result: 8.6:1 ✅ Pass

# Body text (neutral-800 on white)
wcag-contrast "#1f2937" "#ffffff"
# Result: 12.6:1 ✅ Pass
```

### Color Blindness

**Test with simulators**:
- [Color Oracle](https://colororacle.org/) (desktop app)
- [Coolors Contrast Checker](https://coolors.co/contrast-checker)

**Guidelines**:
- Don't rely on color alone (use icons, labels, patterns)
- Ensure red/green states have additional indicators
- Test with protanopia, deuteranopia, tritanopia filters

### Focus Indicators

Always provide visible focus states for keyboard navigation:

```scss
.button {
  &:focus-visible {
    outline: 2px solid $color-primary;
    outline-offset: 2px;
  }
}
```

**Minimum**: 2px outline with 2:1 contrast against background.

## Theme Checklist

Before deploying a new theme, verify:

- [ ] **Contrast**: All text meets WCAG AA (4.5:1 minimum)
- [ ] **Color blindness**: Tested with simulators
- [ ] **Focus states**: Visible on all interactive elements
- [ ] **Shadows**: Match or complement primary color
- [ ] **Components**: All components tested (buttons, cards, badges, etc.)
- [ ] **States**: Hover, active, disabled states have proper contrast
- [ ] **Error/success**: Semantic colors are distinguishable
- [ ] **Responsive**: Theme works on mobile, tablet, desktop
- [ ] **Performance**: No layout shifts from theme change

## Advanced: Multi-Theme System

### Directory Structure

```
styles/
├── themes/
│   ├── _default.scss     # Blue theme (current)
│   ├── _orange.scss      # Orange retro theme
│   ├── _teal.scss        # Teal modern theme
│   └── _dark.scss        # Dark mode theme
└── design-tokens/
    ├── _colors.scss      # Imports active theme
    └── _index.scss
```

### Theme Files

**themes/_default.scss:**
```scss
// Default blue theme
$theme-primary-50: #eff6ff;
$theme-primary-600: #2563eb;
$theme-primary-700: #1d4ed8;
// ... etc
```

**themes/_orange.scss:**
```scss
// Orange retro theme
$theme-primary-50: #fff7ed;
$theme-primary-600: #ea580c;
$theme-primary-700: #c2410c;
// ... etc
```

### Switching Themes

**_colors.scss:**
```scss
// Import active theme
@use '../themes/default' as theme;
// @use '../themes/orange' as theme;  // Swap to switch

// Map theme to base palette
$blue-50: theme.$theme-primary-50;
$blue-600: theme.$theme-primary-600;
// ... etc
```

Change one line to switch the entire site theme.

## Resources

- **[COLOR_PALETTE.md](COLOR_PALETTE.md)** - Complete color reference
- **[DESIGN_TOKENS.md](DESIGN_TOKENS.md)** - All design tokens
- **[COMPONENT_REFERENCE.md](COMPONENT_REFERENCE.md)** - Component patterns
- **Accessibility**: [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- **Color tools**: [Coolors](https://coolors.co/), [Adobe Color](https://color.adobe.com/)

---

**Questions or need help?** Open an issue on GitHub or consult the design system documentation.
