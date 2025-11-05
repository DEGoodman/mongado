# UI Migration Guide

Complete guide for the SCSS module system that replaced Tailwind CSS.

## Table of Contents

- [Overview](#overview)
- [Design System Architecture](#design-system-architecture)
- [Using Design Tokens](#using-design-tokens)
- [Using Mixins](#using-mixins)
- [Component Examples](#component-examples)
- [Best Practices](#best-practices)
- [Migration History](#migration-history)

## Overview

This project uses **SCSS Modules** for all component styling with a centralized design system. Tailwind CSS has been completely removed.

### Key Benefits

- **Type-safe styles**: CSS Modules provide scoped, type-safe class names
- **Centralized design tokens**: Single source of truth for colors, spacing, typography
- **Reusable mixins**: DRY patterns for layouts, transitions, and common styles
- **Better performance**: No runtime CSS generation, smaller bundle size
- **Full control**: Complete ownership of the design system

### Directory Structure

```
frontend/src/styles/
├── _design-tokens.scss   # Colors, spacing, typography, shadows
├── _mixins.scss          # Layout patterns, utilities, transitions
├── _animations.scss      # Keyframe animations
└── README.md            # Design system documentation

frontend/src/components/
└── ComponentName.module.scss  # Component-specific styles
```

## Design System Architecture

### Design Tokens

All design values are defined in `frontend/src/styles/_design-tokens.scss`:

#### Color System

Standard color scales with consistent naming:

```scss
// Neutral grays (50-900)
$neutral-50, $neutral-100, ..., $neutral-900

// Blue (50-900)
$blue-50, $blue-100, ..., $blue-900

// Red (50-900)
$red-50, $red-100, ..., $red-900

// Green (50, 100, 500, 600, 700)
$green-50, $green-100, $green-500, $green-600, $green-700

// Yellow (50, 100, 200, 300)
$yellow-50, $yellow-100, $yellow-200, $yellow-300

// Semantic colors
$white, $black
```

#### Spacing Scale

```scss
$spacing-1: 0.25rem;  // 4px
$spacing-2: 0.5rem;   // 8px
$spacing-3: 0.75rem;  // 12px
$spacing-4: 1rem;     // 16px
$spacing-5: 1.25rem;  // 20px
$spacing-6: 1.5rem;   // 24px
$spacing-8: 2rem;     // 32px
$spacing-10: 2.5rem;  // 40px
$spacing-12: 3rem;    // 48px
$spacing-16: 4rem;    // 64px
```

#### Typography

```scss
// Font sizes
$font-size-xs: 0.75rem;   // 12px
$font-size-sm: 0.875rem;  // 14px
$font-size-base: 1rem;    // 16px
$font-size-lg: 1.125rem;  // 18px
$font-size-xl: 1.25rem;   // 20px
$font-size-2xl: 1.5rem;   // 24px
$font-size-3xl: 1.875rem; // 30px
$font-size-4xl: 2.25rem;  // 36px

// Font weights
$font-weight-normal: 400;
$font-weight-medium: 500;
$font-weight-semibold: 600;
$font-weight-bold: 700;

// Line heights
$line-height-tight: 1.25;
$line-height-normal: 1.5;
$line-height-relaxed: 1.75;
```

#### Borders & Radii

```scss
// Border widths
$border-width-thin: 1px;
$border-width-medium: 2px;

// Border styles
$border-default: $border-width-thin solid $neutral-200;

// Border radii
$border-radius-sm: 0.25rem;  // 4px
$border-radius-md: 0.5rem;   // 8px
$border-radius-lg: 0.75rem;  // 12px
$border-radius-full: 9999px;
```

#### Shadows

```scss
$shadow-button: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
$shadow-card-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
$shadow-card-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
$shadow-card-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
$shadow-popover: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
```

### Mixins

Reusable style patterns in `frontend/src/styles/_mixins.scss`:

#### Layout Mixins

```scss
@mixin flex-start;           // Flex row, align start
@mixin flex-center;          // Flex row, center all
@mixin flex-between;         // Flex row, space-between
@mixin stack($gap);          // Flex column with gap
@mixin grid-auto-fill($min); // Responsive grid
```

#### Typography Mixins

```scss
@mixin text-primary;    // Base text size + line height
@mixin text-secondary;  // Smaller text (14px)
@mixin text-tertiary;   // Smallest text (12px)
```

#### Transition Mixins

```scss
@mixin transition-default;  // all 0.2s ease
@mixin transition-colors;   // color, background-color 0.2s ease
@mixin transition-slow;     // all 0.3s ease
```

#### Animation Mixins

```scss
@mixin animate-fade-in;           // Fade from 0 to 1 opacity
@mixin animate-slide-in-bottom;   // Slide up from bottom
@mixin animate-slide-in-right;    // Slide in from right
```

## Using Design Tokens

### Basic Usage

```scss
// Import tokens at the top of every .module.scss file
@use '@/styles/design-tokens' as *;

.myComponent {
  // Colors
  background-color: $white;
  color: $neutral-900;
  border: $border-default;

  // Spacing
  padding: $spacing-4;
  margin-bottom: $spacing-6;
  gap: $spacing-3;

  // Typography
  font-size: $font-size-base;
  font-weight: $font-weight-medium;
  line-height: $line-height-normal;

  // Shadows & radii
  box-shadow: $shadow-card-md;
  border-radius: $border-radius-md;
}
```

### Interactive States

```scss
.button {
  background-color: $blue-600;
  color: $white;

  &:hover {
    background-color: $blue-700;
  }

  &:active {
    background-color: $blue-800;
  }

  &:disabled {
    background-color: $neutral-200;
    color: $neutral-400;
    cursor: not-allowed;
  }
}
```

## Using Mixins

### Import Mixins

```scss
// Import at the top of .module.scss files
@use '@/styles/mixins' as *;
@use '@/styles/design-tokens' as *;
```

### Layout Patterns

```scss
// Horizontal flex layout
.header {
  @include flex-between;
  padding: $spacing-4;
}

// Vertical stack
.sidebar {
  @include stack($spacing-4);
}

// Responsive grid
.grid {
  @include grid-auto-fill(250px);
  gap: $spacing-4;
}
```

### Transitions & Animations

```scss
.card {
  @include transition-slow;  // Smooth transition for transform

  &:hover {
    transform: translateY(-4px);
  }
}

.link {
  @include transition-colors;  // Only animate colors
  color: $blue-600;

  &:hover {
    color: $blue-700;
  }
}

.toast {
  @include animate-slide-in-bottom;  // Slide up animation
}
```

## Component Examples

### Simple Component

```tsx
// Badge.tsx
import styles from './Badge.module.scss';

export function Badge({ children }: { children: React.ReactNode }) {
  return <span className={styles.badge}>{children}</span>;
}
```

```scss
// Badge.module.scss
@use '@/styles/design-tokens' as *;
@use '@/styles/mixins' as *;

.badge {
  display: inline-flex;
  align-items: center;
  padding: $spacing-1 $spacing-2;
  border-radius: $border-radius-sm;
  background-color: $blue-50;
  color: $blue-700;
  @include text-tertiary;
  font-weight: $font-weight-medium;
}
```

### Interactive Component

```tsx
// Button.tsx
import styles from './Button.module.scss';

interface ButtonProps {
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
}

export function Button({ variant = 'primary', children }: ButtonProps) {
  return (
    <button className={`${styles.button} ${styles[variant]}`}>
      {children}
    </button>
  );
}
```

```scss
// Button.module.scss
@use '@/styles/design-tokens' as *;
@use '@/styles/mixins' as *;

.button {
  @include flex-center;
  padding: $spacing-2 $spacing-4;
  border-radius: $border-radius-md;
  border: none;
  font-weight: $font-weight-medium;
  cursor: pointer;
  @include transition-default;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.primary {
  background-color: $blue-600;
  color: $white;

  &:hover:not(:disabled) {
    background-color: $blue-700;
  }
}

.secondary {
  background-color: $neutral-100;
  color: $neutral-900;

  &:hover:not(:disabled) {
    background-color: $neutral-200;
  }
}
```

### Layout Component

```tsx
// Card.tsx
import styles from './Card.module.scss';

export function Card({ children }: { children: React.ReactNode }) {
  return <div className={styles.card}>{children}</div>;
}
```

```scss
// Card.module.scss
@use '@/styles/design-tokens' as *;
@use '@/styles/mixins' as *;

.card {
  padding: $spacing-6;
  border: $border-default;
  border-radius: $border-radius-md;
  background-color: $white;
  box-shadow: $shadow-card-sm;
  @include transition-slow;

  &:hover {
    box-shadow: $shadow-card-md;
  }
}
```

## Best Practices

### 1. Always Import Design Tokens

```scss
// ✅ Good
@use '@/styles/design-tokens' as *;
@use '@/styles/mixins' as *;

.component {
  padding: $spacing-4;
}
```

```scss
// ❌ Bad - magic numbers
.component {
  padding: 16px;
}
```

### 2. Use Semantic Class Names

```scss
// ✅ Good - semantic names
.articleCard {
  .title { }
  .description { }
  .metadata { }
}
```

```scss
// ❌ Bad - utility names
.flex {
  .text-lg { }
  .text-gray-600 { }
}
```

### 3. Prefer Mixins for Repeated Patterns

```scss
// ✅ Good
.button {
  @include transition-default;
  @include flex-center;
}
```

```scss
// ❌ Bad - duplicated code
.button {
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

### 4. Use Available Color Tokens Only

Check `_design-tokens.scss` for available colors. Common mistakes:

```scss
// ❌ These don't exist
color: $green-800;   // Only 50, 100, 500, 600, 700 available
color: $yellow-500;  // Only 50, 100, 200, 300 available

// ✅ Use available tokens or neutral alternatives
color: $green-700;   // Available
color: $yellow-300;  // Available
color: $neutral-700; // Neutral fallback
```

### 5. Organize Styles Logically

```scss
.component {
  // 1. Layout & positioning
  display: flex;
  position: relative;

  // 2. Box model
  padding: $spacing-4;
  margin-bottom: $spacing-6;

  // 3. Visual styling
  background-color: $white;
  border: $border-default;
  border-radius: $border-radius-md;
  box-shadow: $shadow-card-sm;

  // 4. Typography
  font-size: $font-size-base;
  font-weight: $font-weight-medium;
  color: $neutral-900;

  // 5. Mixins & transitions
  @include transition-default;

  // 6. Nested elements & modifiers
  .child { }
  &:hover { }
}
```

## Migration History

### Completed Phases

**Phase 0: Infrastructure** ✅
- Set up SCSS module system
- Created design tokens
- Built mixin library

**Phase 1: Foundation Components** ✅
- Badge, Button, Card
- Established component patterns

**Phase 2: Knowledge Base Pages** ✅
- Migrated all KB pages
- Converted complex layouts

**Phase 3: Component Migration** ✅
- Migrated all remaining components
- Consolidated styles with mixins

**Phase 4: Cleanup & Optimization** ✅
- Refactored early components to use optimization mixins
- Replaced hardcoded transitions with transition mixins
- Replaced custom animations with animation mixins

**Phase 5: Remove Tailwind** ✅
- Removed all Tailwind packages (39 dependencies)
- Deleted tailwind.config.ts
- Updated postcss.config to use autoprefixer only
- Replaced Tailwind directives in globals.css

### Benefits Achieved

- **39 fewer dependencies**: Smaller bundle, faster installs
- **Faster builds**: No Tailwind processing overhead
- **Complete design control**: Pure SCSS with no framework constraints
- **Better maintainability**: Centralized design tokens and mixins
- **Type safety**: CSS Modules provide scoped class names

## Resources

- **Design Tokens**: `frontend/src/styles/_design-tokens.scss`
- **Mixins**: `frontend/src/styles/_mixins.scss`
- **Animations**: `frontend/src/styles/_animations.scss`
- **Epic**: [#103](https://github.com/DEGoodman/mongado/issues/103)
