# UI Migration Guide

Guide for migrating from Tailwind CSS to CSS Modules + SCSS with the new retro-modern design system.

## Table of Contents

- [Migration Strategy](#migration-strategy)
- [Color Palette Reference](#color-palette-reference)
- [Component Conversion Examples](#component-conversion-examples)
- [Using Design Tokens](#using-design-tokens)
- [Common Patterns](#common-patterns)

## Migration Strategy

### Parallel Implementation

We're using a **parallel implementation** strategy where new CSS Modules coexist with existing Tailwind during the transition:

1. **Phase 0**: Set up SCSS infrastructure and design tokens ✅
2. **Phase 1**: Migrate foundation components (Badge, Button, Card)
3. **Phase 2**: Build Quick Lists system with new colors
4. **Phase 3**: Migrate all pages component-by-component
5. **Phase 4**: Refine typography and spacing
6. **Phase 5**: Polish and optimize

### Component-Level Migration

When migrating a component:

1. Create a `.module.scss` file alongside the component
2. Import design tokens: `@use '@/styles/design-tokens' as *;`
3. Replace Tailwind classes with semantic SCSS classes
4. Test thoroughly before removing Tailwind classes
5. Update component tests if needed

## Color Palette Reference

### Warm Neutrals (Foundation)

| Usage | Variable | Hex | Example |
|-------|----------|-----|---------|
| Canvas background | `$color-bg-canvas` | `#FAFAF8` | Main page background |
| Secondary background | `$color-bg-secondary` | `#F5F5F2` | Sections, alternating rows |
| Card background | `$color-bg-card` | `#EEEEEA` | Cards, panels |
| Borders | `$color-border` | `#E5E5E0` | Dividers, card borders |
| Primary text | `$color-text-primary` | `#2D2D28` | Body text |
| Heading text | `$color-text-heading` | `#3D3D35` | H1-H2 (softer) |
| Secondary text | `$color-text-secondary` | `#8B8B82` | Captions, metadata |
| Tertiary text | `$color-text-tertiary` | `#B8B8B0` | Placeholders |

### Orange Spectrum (Primary Accent)

| Usage | Variable | Hex | Example |
|-------|----------|-----|---------|
| Primary CTA | `$color-primary` | `#E67E42` | Buttons, links |
| Hover | `$color-primary-hover` | `#F39552` | Interactive states |
| Active/Focus | `$color-primary-active` | `#D96D32` | Pressed states |
| Light background | `$color-primary-light` | `#FFE5D4` | Article badges |
| Dark text | `$color-primary-dark` | `#C95D28` | On light backgrounds |

### Terracotta (Secondary Accent)

| Usage | Variable | Hex | Example |
|-------|----------|-----|---------|
| Secondary actions | `$color-secondary` | `#C4624F` | Note badges, alt buttons |
| Hover | `$color-secondary-hover` | `#D97763` | Interactive states |
| Light background | `$color-secondary-light` | `#FFE8E3` | Note backgrounds |

### Retro Accents

**Mustard Yellow** (Warnings, Orphan Notes):
- Primary: `$color-accent-mustard` (#D4A748)
- Light: `$color-accent-mustard-light` (#FFF4D6)

**Sage Green** (Success):
- Primary: `$color-accent-sage` (#7B9E7A)
- Light: `$color-accent-sage-light` (#E8F2E8)

**Dusty Blue** (Info, Hub Notes):
- Primary: `$color-accent-blue` (#6B8B9E)
- Light: `$color-accent-blue-light` (#E3EBF0)

## Component Conversion Examples

### Before: Tailwind

```tsx
// Badge.tsx (Tailwind)
export function Badge({ type, children }: BadgeProps) {
  return (
    <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded bg-orange-100 text-orange-800">
      {children}
    </span>
  );
}
```

### After: CSS Modules + SCSS

```tsx
// Badge.tsx (CSS Modules)
import styles from './Badge.module.scss';

export function Badge({ type, children }: BadgeProps) {
  return (
    <span className={styles.badge} data-type={type}>
      {children}
    </span>
  );
}
```

```scss
// Badge.module.scss
@use '@/styles/design-tokens' as *;

.badge {
  display: inline-flex;
  align-items: center;
  padding: $spacing-1 $spacing-2;
  font-size: $font-size-xs;
  font-weight: $font-weight-medium;
  border-radius: $border-radius-tag;

  &[data-type='article'] {
    background-color: $color-primary-light;
    color: $color-primary-dark;
  }

  &[data-type='note'] {
    background-color: $color-secondary-light;
    color: $color-secondary;
  }
}
```

## Using Design Tokens

### Importing Tokens

```scss
// At the top of any .module.scss file
@use '@/styles/design-tokens' as *;
```

### Using Tokens

```scss
.myComponent {
  // Colors
  background-color: $color-bg-card;
  color: $color-text-primary;
  border: $border-card;

  // Spacing
  padding: $spacing-md;
  margin-bottom: $spacing-lg;
  gap: $gap-md;

  // Typography
  font-size: $font-size-base;
  font-weight: $font-weight-medium;
  line-height: $line-height-relaxed;

  // Shadows & borders
  box-shadow: $shadow-card-sm;
  border-radius: $border-radius-card;
}
```

### Using Mixins

```scss
@use '@/styles/mixins' as *;

.card {
  @include card; // Applies all card styles

  &:hover {
    @include hover-lift; // Lift on hover
  }
}

.heading {
  @include heading-h2; // H2 typography
}

.link {
  @include link-default; // Link styles with hover
}
```

## Common Patterns

### Tailwind → SCSS Conversions

| Tailwind | SCSS Token |
|----------|------------|
| `bg-gray-50` | `background-color: $color-bg-canvas;` |
| `text-gray-900` | `color: $color-text-primary;` |
| `text-gray-600` | `color: $color-text-secondary;` |
| `border-gray-200` | `border: $border-default;` |
| `rounded-lg` | `border-radius: $border-radius-card;` |
| `shadow-md` | `box-shadow: $shadow-card-md;` |
| `p-4` | `padding: $spacing-md;` (16px) |
| `m-6` | `margin: $spacing-lg;` (24px) |
| `gap-4` | `gap: $gap-md;` (16px) |
| `text-sm` | `font-size: $font-size-sm;` (14px) |
| `font-medium` | `font-weight: $font-weight-medium;` (500) |

### Layout Patterns

```scss
// Container
.container {
  @include container; // Max-width, auto margins, responsive padding
}

// Flexbox
.flexContainer {
  @include flex-between; // Space-between with centered items
}

// Grid
.grid {
  @include grid-auto-fill(250px); // Responsive grid
}

// Vertical stack
.stack {
  @include stack($spacing-lg); // Vertical spacing
}
```

### Interactive States

```scss
.button {
  @include transition-default; // Smooth transitions

  &:hover {
    background-color: $color-primary-hover;
  }

  &:active {
    background-color: $color-primary-active;
  }

  &:focus-visible {
    @include focus-outline; // Keyboard focus
  }

  &:disabled {
    @include disabled; // Disabled state
  }
}
```

## Accessibility Checklist

When migrating components:

- [ ] Ensure text meets WCAG AA contrast ratio (4.5:1 minimum)
- [ ] Add `:focus-visible` styles for keyboard navigation
- [ ] Use semantic HTML elements
- [ ] Test with keyboard navigation
- [ ] Verify screen reader compatibility

## Testing

After migrating a component:

1. **Visual verification**: Check in browser at multiple screen sizes
2. **Interactive states**: Test hover, focus, active, disabled
3. **Accessibility**: Keyboard navigation, screen reader
4. **Unit tests**: Update any tests that reference className
5. **Cross-browser**: Verify in Chrome, Firefox, Safari

## Resources

- [Design Tokens](../frontend/src/styles/design-tokens/)
- [Mixins](../frontend/src/styles/mixins/)
- [Global Styles](../frontend/src/styles/globals.scss)
- [Epic #94](https://github.com/DEGoodman/mongado/issues/94)
