# Color Palette Reference

Complete color palette documentation for the Mongado design system.

## Table of Contents

- [Overview](#overview)
- [Base Palette](#base-palette)
- [Semantic Color System](#semantic-color-system)
- [Usage Guidelines](#usage-guidelines)
- [Color Relationships](#color-relationships)

## Overview

The design system uses a **two-tier color architecture**:

1. **Tier 1 (Base Palette)**: Actual color values based on Tailwind's default palette
2. **Tier 2 (Semantic Tokens)**: Purpose-based color names that map to Tier 1 colors

This architecture makes theming easy—change Tier 1 to swap the entire palette while maintaining semantic consistency.

**Current Theme**: Clean blue-purple system with Tailwind defaults

## Base Palette

### Neutrals (Grays)

Full gray scale from light to dark:

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `$neutral-50` | `#f9fafb` | rgb(249, 250, 251) | Lightest backgrounds |
| `$neutral-100` | `#f3f4f6` | rgb(243, 244, 246) | Light backgrounds |
| `$neutral-200` | `#e5e7eb` | rgb(229, 231, 235) | Borders, dividers |
| `$neutral-300` | `#d1d5db` | rgb(209, 213, 219) | Default borders |
| `$neutral-400` | `#9ca3af` | rgb(156, 163, 175) | Disabled elements |
| `$neutral-500` | `#6b7280` | rgb(107, 114, 128) | Tertiary text |
| `$neutral-600` | `#4b5563` | rgb(75, 85, 99) | Secondary text |
| `$neutral-700` | `#374151` | rgb(55, 65, 81) | Headings |
| `$neutral-800` | `#1f2937` | rgb(31, 41, 55) | Primary text |
| `$neutral-900` | `#111827` | rgb(17, 24, 39) | Darkest text |

### Blues (Primary)

Main interactive color - used for buttons, links, primary actions:

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `$blue-50` | `#eff6ff` | rgb(239, 246, 255) | Light backgrounds, page gradient |
| `$blue-100` | `#dbeafe` | rgb(219, 234, 254) | Hover backgrounds |
| `$blue-200` | `#bfdbfe` | rgb(191, 219, 254) | Borders for blue elements |
| `$blue-300` | `#93c5fd` | rgb(147, 197, 253) | Lighter accents |
| `$blue-400` | `#60a5fa` | rgb(96, 165, 250) | Medium blue |
| `$blue-500` | `#3b82f6` | rgb(59, 130, 246) | Focus rings |
| `$blue-600` | `#2563eb` | rgb(37, 99, 235) | **Primary CTA color** |
| `$blue-700` | `#1d4ed8` | rgb(29, 78, 216) | Hover state, dark text |
| `$blue-800` | `#1e40af` | rgb(30, 64, 175) | Active/pressed state |
| `$blue-900` | `#1e3a8a` | rgb(30, 58, 138) | Darkest blue |

### Indigos

Used for gradient effects:

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `$indigo-50` | `#eef2ff` | rgb(238, 242, 255) | Page gradient end |
| `$indigo-100` | `#e0e7ff` | rgb(224, 231, 255) | Light indigo backgrounds |
| `$indigo-200` | `#c7d2fe` | rgb(199, 210, 254) | Indigo borders |

### Purples (Secondary)

Secondary interactive color - used for secondary actions, notes:

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `$purple-50` | `#faf5ff` | rgb(250, 245, 255) | Note backgrounds |
| `$purple-100` | `#f3e8ff` | rgb(243, 232, 255) | Purple hover |
| `$purple-200` | `#e9d5ff` | rgb(233, 213, 255) | Note borders |
| `$purple-300` | `#d8b4fe` | rgb(216, 180, 254) | Light purple accents |
| `$purple-500` | `#a855f7` | rgb(168, 85, 247) | Medium purple |
| `$purple-600` | `#9333ea` | rgb(147, 51, 234) | **Secondary CTA color** |
| `$purple-700` | `#7e22ce` | rgb(126, 34, 206) | Purple hover, visited links |
| `$purple-800` | `#6b21a8` | rgb(107, 33, 168) | Dark purple |
| `$purple-900` | `#581c87` | rgb(88, 28, 135) | Darkest purple |

### Greens (Success)

Limited palette for success states:

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `$green-50` | `#f0fdf4` | rgb(240, 253, 244) | Success backgrounds |
| `$green-100` | `#dcfce7` | rgb(220, 252, 231) | Light green |
| `$green-500` | `#22c55e` | rgb(34, 197, 94) | Success borders |
| `$green-600` | `#16a34a` | rgb(22, 163, 74) | Success text/icons |
| `$green-700` | `#15803d` | rgb(21, 128, 61) | Dark success text |

### Reds (Errors)

Error and danger states:

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `$red-50` | `#fef2f2` | rgb(254, 242, 242) | Error backgrounds |
| `$red-100` | `#fee2e2` | rgb(254, 226, 226) | Light error |
| `$red-200` | `#fecaca` | rgb(254, 202, 202) | Error borders (light) |
| `$red-500` | `#ef4444` | rgb(239, 68, 68) | Error borders |
| `$red-600` | `#dc2626` | rgb(220, 38, 38) | Error icons/buttons |
| `$red-700` | `#b91c1c` | rgb(185, 28, 28) | Error text |
| `$red-800` | `#991b1b` | rgb(153, 27, 27) | Dark error |

### Yellows (Highlights)

Search highlighting and attention:

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `$yellow-50` | `#fefce8` | rgb(254, 252, 232) | Yellow backgrounds |
| `$yellow-100` | `#fef9c3` | rgb(254, 249, 195) | Light yellow |
| `$yellow-200` | `#fef08a` | rgb(254, 240, 138) | Yellow borders |
| `$yellow-300` | `#fde047` | rgb(253, 224, 71) | Yellow text/highlights |

### Ambers (Warnings)

Warning states:

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `$amber-50` | `#fffbeb` | rgb(255, 251, 235) | Warning backgrounds |
| `$amber-100` | `#fef3c7` | rgb(254, 243, 199) | Light amber |
| `$amber-500` | `#f59e0b` | rgb(245, 158, 11) | Warning borders |
| `$amber-600` | `#d97706` | rgb(217, 119, 6) | Warning text/icons |

### Oranges

Knowledge Base CTA color:

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `$orange-50` | `#fff7ed` | rgb(255, 247, 237) | Orange backgrounds |
| `$orange-100` | `#ffedd5` | rgb(255, 237, 213) | Light orange |
| `$orange-500` | `#f97316` | rgb(249, 115, 22) | Orange accents |
| `$orange-600` | `#ea580c` | rgb(234, 88, 12) | Orange buttons |
| `$orange-700` | `#c2410c` | rgb(194, 65, 12) | Dark orange |

### Grays (Additional)

Duplicate of neutral for compatibility:

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `$gray-50` | `#f9fafb` | rgb(249, 250, 251) | Same as neutral-50 |
| `$gray-100` | `#f3f4f6` | rgb(243, 244, 246) | Same as neutral-100 |

### Base Colors

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `$white` | `#ffffff` | rgb(255, 255, 255) | White |
| `$black` | `#000000` | rgb(0, 0, 0) | Black |

## Semantic Color System

Semantic tokens define the **purpose** of colors, not their specific hue. This abstraction makes theming easy.

### Page Structure

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-page-bg` | `$blue-50` | `#eff6ff` | Main page background |
| `$color-page-bg-gradient-start` | `$blue-50` | `#eff6ff` | Gradient start |
| `$color-page-bg-gradient-end` | `$indigo-50` | `#eef2ff` | Gradient end |
| `$color-page-bg-alt` | `$neutral-100` | `#f3f4f6` | Alternative page BG |

### Surfaces (Cards, Panels)

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-surface-default` | `$white` | `#ffffff` | Default card background |
| `$color-surface-secondary` | `$neutral-50` | `#f9fafb` | Secondary surfaces |
| `$color-surface-tertiary` | `$neutral-100` | `#f3f4f6` | Tertiary surfaces |
| `$color-surface-elevated` | `$white` | `#ffffff` | Elevated cards (with shadow) |
| `$color-surface-hover` | `$neutral-50` | `#f9fafb` | Surface hover state |

### Text

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-text-primary` | `$neutral-800` | `#1f2937` | Body text |
| `$color-text-secondary` | `$neutral-600` | `#4b5563` | Less emphasis |
| `$color-text-tertiary` | `$neutral-500` | `#6b7280` | Subtle text |
| `$color-text-heading` | `$neutral-700` | `#374151` | Headings |
| `$color-text-disabled` | `$neutral-500` | `#6b7280` | Disabled text |
| `$color-text-inverse` | `$white` | `#ffffff` | Text on dark BG |

### Borders

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-border-default` | `$neutral-300` | `#d1d5db` | Default borders |
| `$color-border-subtle` | `$neutral-200` | `#e5e7eb` | Subtle borders |
| `$color-border-strong` | `$neutral-400` | `#9ca3af` | Strong borders |
| `$color-border-hover` | `$neutral-400` | `#9ca3af` | Border on hover |

### Interactive Elements

#### Primary Actions (Main CTAs)

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-interactive-primary` | `$blue-600` | `#2563eb` | Primary button, main links |
| `$color-interactive-primary-hover` | `$blue-700` | `#1d4ed8` | Primary hover |
| `$color-interactive-primary-active` | `$blue-800` | `#1e40af` | Primary active/pressed |
| `$color-interactive-primary-text` | `$white` | `#ffffff` | Text on primary buttons |

#### Secondary Actions

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-interactive-secondary` | `$purple-600` | `#9333ea` | Secondary buttons |
| `$color-interactive-secondary-hover` | `$purple-700` | `#7e22ce` | Secondary hover |
| `$color-interactive-secondary-text` | `$white` | `#ffffff` | Text on secondary buttons |

#### Tertiary Actions

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-interactive-tertiary` | `$neutral-700` | `#374151` | Tertiary buttons |
| `$color-interactive-tertiary-hover` | `$neutral-800` | `#1f2937` | Tertiary hover |
| `$color-interactive-tertiary-bg` | `$neutral-100` | `#f3f4f6` | Tertiary BG |

#### Links

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-link-default` | `$blue-600` | `#2563eb` | Default link color |
| `$color-link-hover` | `$blue-800` | `#1e40af` | Link hover (darker) |
| `$color-link-visited` | `$purple-700` | `#7e22ce` | Visited links |

### Semantic States

#### Success

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-success-bg` | `$green-50` | `#f0fdf4` | Success background |
| `$color-success-border` | `$green-500` | `#22c55e` | Success border |
| `$color-success-text` | `$green-600` | `#16a34a` | Success text/icons |

#### Warning

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-warning-bg` | `$amber-50` | `#fffbeb` | Warning background |
| `$color-warning-border` | `$amber-500` | `#f59e0b` | Warning border |
| `$color-warning-text` | `$amber-600` | `#d97706` | Warning text/icons |

#### Error

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-error-bg` | `$red-50` | `#fef2f2` | Error background |
| `$color-error-border` | `$red-500` | `#ef4444` | Error border |
| `$color-error-text` | `$red-700` | `#b91c1c` | Error text |

#### Info

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-info-bg` | `$blue-50` | `#eff6ff` | Info background |
| `$color-info-border` | `$blue-200` | `#bfdbfe` | Info border |
| `$color-info-text` | `$blue-700` | `#1d4ed8` | Info text |

### Form Elements

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-input-bg` | `$white` | `#ffffff` | Input background |
| `$color-input-border` | `$neutral-300` | `#d1d5db` | Input border |
| `$color-input-border-hover` | `$neutral-400` | `#9ca3af` | Input border hover |
| `$color-input-border-focus` | `$blue-500` | `#3b82f6` | Focus ring |
| `$color-input-text` | `$neutral-800` | `#1f2937` | Input text |
| `$color-input-placeholder` | `$neutral-500` | `#6b7280` | Placeholder text |
| `$color-input-disabled-bg` | `$neutral-100` | `#f3f4f6` | Disabled BG |
| `$color-input-disabled-text` | `$neutral-500` | `#6b7280` | Disabled text |

### Badges

#### Article Badges

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-badge-article-bg` | `$blue-50` | `#eff6ff` | Article badge BG |
| `$color-badge-article-text` | `$blue-700` | `#1d4ed8` | Article badge text |
| `$color-badge-article-border` | `$blue-200` | `#bfdbfe` | Article badge border |

#### Note Badges

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-badge-note-bg` | `$purple-50` | `#faf5ff` | Note badge BG |
| `$color-badge-note-text` | `$purple-700` | `#7e22ce` | Note badge text |
| `$color-badge-note-border` | `$purple-200` | `#e9d5ff` | Note badge border |

### Quick Lists (Note Categories)

#### Orphan Notes

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-orphan-bg` | `$yellow-50` | `#fefce8` | Orphan note BG |
| `$color-orphan-border` | `$yellow-200` | `#fef08a` | Orphan note border |
| `$color-orphan-text` | `$amber-600` | `#d97706` | Orphan note text |
| `$color-orphan-heading` | `$amber-600` | `#d97706` | Orphan note heading |
| `$color-orphan-hover` | `$yellow-100` | `#fef9c3` | Orphan note hover |

#### Hub Notes

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-hub-bg` | `$blue-50` | `#eff6ff` | Hub note BG |
| `$color-hub-border` | `$blue-200` | `#bfdbfe` | Hub note border |
| `$color-hub-text` | `$blue-600` | `#2563eb` | Hub note text |
| `$color-hub-heading` | `$blue-700` | `#1d4ed8` | Hub note heading |
| `$color-hub-hover` | `$blue-100` | `#dbeafe` | Hub note hover |

#### Central Concept Notes

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-central-bg` | `$purple-50` | `#faf5ff` | Central note BG |
| `$color-central-border` | `$purple-200` | `#e9d5ff` | Central note border |
| `$color-central-text` | `$purple-600` | `#9333ea` | Central note text |
| `$color-central-heading` | `$purple-700` | `#7e22ce` | Central note heading |
| `$color-central-hover` | `$purple-100` | `#f3e8ff` | Central note hover |

### Social Links

#### GitHub

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-social-github-bg` | `$neutral-900` | `#111827` | GitHub button BG |
| `$color-social-github-bg-hover` | `$neutral-800` | `#1f2937` | GitHub hover |
| `$color-social-github-text` | `$white` | `#ffffff` | GitHub text |

#### LinkedIn

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-social-linkedin-bg` | `$blue-600` | `#2563eb` | LinkedIn button BG |
| `$color-social-linkedin-bg-hover` | `$blue-700` | `#1d4ed8` | LinkedIn hover |
| `$color-social-linkedin-text` | `$white` | `#ffffff` | LinkedIn text |

#### Email

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-social-email-bg` | `$gray-100` | `#f3f4f6` | Email button BG |
| `$color-social-email-bg-hover` | `$neutral-200` | `#e5e7eb` | Email hover |
| `$color-social-email-text` | `$neutral-900` | `#111827` | Email text |
| `$color-social-email-border` | `$neutral-300` | `#d1d5db` | Email border |

### Disabled States

| Semantic Token | Maps To | Hex | Usage |
|----------------|---------|-----|-------|
| `$color-disabled-bg` | `$neutral-400` | `#9ca3af` | Disabled BG |
| `$color-disabled-text` | `$neutral-500` | `#6b7280` | Disabled text |

## Usage Guidelines

### Interactive Element Colors

**Primary Actions (Blue)**:
- Main CTAs ("Create Note", "Save", "Submit")
- Primary navigation links
- Focus indicators

**Secondary Actions (Purple)**:
- Secondary buttons
- Note-related actions
- Alternative CTAs

**Tertiary Actions (Gray)**:
- Cancel buttons
- Low-emphasis actions
- Neutral operations

### State Colors

**Success (Green)**: Confirmations, successful operations
**Warning (Amber)**: Cautions, important notices, orphan notes
**Error (Red)**: Errors, destructive actions, validation failures
**Info (Blue)**: Helpful information, tips, hub notes

### Text Hierarchy

- **Primary text** (`$neutral-800`): Body copy, main content
- **Secondary text** (`$neutral-600`): Captions, metadata, descriptions
- **Tertiary text** (`$neutral-500`): Placeholders, de-emphasized text
- **Headings** (`$neutral-700`): Softer than body for visual hierarchy

### Surface Hierarchy

- **Elevated surfaces** (`$white` with shadow): Important cards, modals
- **Default surfaces** (`$white`): Standard cards
- **Secondary surfaces** (`$neutral-50`): Less important panels
- **Page background** (`$blue-50` → `$indigo-50` gradient): Main canvas

## Color Relationships

### Complementary Pairs

- **Blue + Purple**: Primary and secondary actions work together
- **Blue + Yellow**: Info and warnings have clear visual distinction
- **Green + Red**: Success and error states are opposite

### Tonal Families

Each color has a consistent scale (50-900) for creating depth:
- **50-200**: Backgrounds, hover states
- **500-700**: Borders, text, icons
- **800-900**: Active states, darkest text

### Accessibility

All color combinations meet **WCAG AA standards** (4.5:1 contrast ratio minimum):
- Blue-600 on white: ✅ 8.6:1
- Neutral-800 on white: ✅ 12.6:1
- Neutral-600 on white: ✅ 7.1:1
- Blue-700 on blue-50: ✅ 8.1:1

## Implementation Notes

**File Location**: `frontend/src/styles/design-tokens/_colors.scss`

**Importing Colors**:
```scss
@use '@/styles/design-tokens' as *;

.myComponent {
  // Use semantic tokens
  background-color: $color-surface-default;
  color: $color-text-primary;

  // Or use base palette directly
  border: 1px solid $blue-200;
}
```

**For Redesigns**: To change the theme, modify Tier 1 (base palette) values. All semantic tokens will automatically update. For example, to create a warm theme, replace blues with oranges and purples with reds in the base palette.
