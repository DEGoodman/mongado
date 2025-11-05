# Component Reference

Complete reference for all UI components in the Mongado design system.

## Table of Contents

- [Foundation Components](#foundation-components)
  - [Button](#button)
  - [Card](#card)
  - [Badge](#badge)
- [Navigation Components](#navigation-components)
  - [Breadcrumb](#breadcrumb)
  - [SettingsDropdown](#settingsdropdown)
- [Content Components](#content-components)
  - [ArticleTableOfContents](#articletableofcontents)
  - [MarkdownWithWikilinks](#markdownwithwikilinks)
  - [ProjectTile](#projecttile)
  - [TagPill](#tagpill)
- [Notification Components](#notification-components)
  - [Toast](#toast)
  - [AuthStatusBanner](#authstatusbanner)
- [AI Components](#ai-components)
  - [AIButton](#aibutton)
  - [AIPanel](#aipanel)
  - [AISuggestionsPanel](#aisuggestionsPanel)
  - [PostSaveAISuggestions](#postsaveaisuggestions)
- [Note Components](#note-components)
  - [NoteEditor](#noteeditor)
  - [QuickLists](#quicklists)

---

## Foundation Components

### Button

**Purpose**: Primary interactive element for actions and navigation

**File**: `frontend/src/components/Button/`

#### Variants

| Variant | Description | Visual Style | Usage |
|---------|-------------|--------------|-------|
| `primary` | Main CTAs | Solid blue (`$blue-600`) background, white text | Primary actions like "Create", "Save", "Submit" |
| `secondary` | Secondary actions | Outlined, blue border, transparent background | Secondary actions, alternative options |
| `tertiary` | Less prominent actions | Gray background (`$neutral-100`) | Cancel, dismiss, neutral actions |
| `ghost` | Subtle actions | Transparent background, blue text | In-context actions, low emphasis |

#### Sizes

| Size | Padding | Font Size | Usage |
|------|---------|-----------|-------|
| `sm` | 8px × 12px | 14px | Compact spaces, inline actions |
| `md` | 10px × 16px | 16px | **Default**, most common |
| `lg` | 12px × 20px | 18px | Hero sections, important CTAs |

#### Props

```typescript
interface ButtonProps {
  variant?: "primary" | "secondary" | "tertiary" | "ghost";
  size?: "sm" | "md" | "lg";
  fullWidth?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}
```

#### Examples

```tsx
// Primary CTA
<Button variant="primary">Create Note</Button>

// Secondary action
<Button variant="secondary">Cancel</Button>

// Ghost in-context action
<Button variant="ghost" size="sm">Edit</Button>

// Full width
<Button variant="primary" fullWidth>Continue</Button>
```

#### States

- **Default**: Base color
- **Hover**: Darker shade, slight lift (translateY -1px)
- **Active**: Darkest shade, no lift
- **Disabled**: 50% opacity, no-cursor
- **Focus**: Blue outline ring (2px solid `$blue-600`)

#### Colors

- **Primary**: `$blue-600` → `$blue-700` (hover) → `$blue-800` (active)
- **Secondary**: `$blue-600` border → `$blue-50` background (hover)
- **Tertiary**: `$neutral-100` → `$neutral-200` (hover)
- **Ghost**: Transparent → `$blue-50` (hover)

---

### Card

**Purpose**: Container component for grouping related content

**File**: `frontend/src/components/Card/`

#### Variants

| Variant | Description | Visual Style | Usage |
|---------|-------------|--------------|-------|
| `default` | Standard card | White background, subtle border | General content containers |
| `elevated` | Prominent card | White background, shadow | Important content, CTAs |
| `interactive` | Clickable card | Hover effects, cursor pointer | Links, navigation items |

#### Sizes

| Size | Padding | Usage |
|------|---------|-------|
| `sm` | 12px | Compact content |
| `md` | 16px | **Default**, most cards |
| `lg` | 24px | Spacious layouts |

#### Props

```typescript
interface CardProps {
  variant?: "default" | "elevated" | "interactive";
  size?: "sm" | "md" | "lg";
  noPadding?: boolean;
  fullWidth?: boolean;
  as?: "div" | "article" | "section";
  children: React.ReactNode;
}
```

#### Examples

```tsx
// Standard card
<Card>
  <h3>Title</h3>
  <p>Content goes here</p>
</Card>

// Elevated card for emphasis
<Card variant="elevated" size="lg">
  <h2>Important Content</h2>
</Card>

// Interactive clickable card
<Card variant="interactive" as="article">
  <h3>Article Title</h3>
  <p>Click to read more...</p>
</Card>
```

#### States

- **Default**: White background, `$neutral-200` border
- **Hover** (interactive only): Slight lift, shadow increase
- **Active** (interactive only): Pressed state

#### Colors

- Background: `$white` or `$neutral-50`
- Border: `$neutral-200` (subtle) to `$neutral-300` (default)
- Shadow: `$shadow-card-sm` to `$shadow-card-md` (elevated)

---

### Badge

**Purpose**: Indicator for content type (Article vs Note)

**File**: `frontend/src/components/Badge.tsx`

#### Types

| Type | Icon | Label | Colors |
|------|------|-------|--------|
| `article` | 📚 | "Article" | Blue: `$blue-50` background, `$blue-700` text, `$blue-200` border |
| `note` | 📝 | "Note" | Purple: `$purple-50` background, `$purple-700` text, `$purple-200` border |

#### Props

```typescript
interface BadgeProps {
  type: "article" | "note";
  className?: string;
}
```

#### Examples

```tsx
<Badge type="article" />
<Badge type="note" />
```

#### Visual Design

- **Size**: Compact inline element
- **Border radius**: Small (4px)
- **Font size**: 12px (tertiary)
- **Font weight**: Medium (500)
- **Padding**: 4px × 8px

---

## Navigation Components

### Breadcrumb

**Purpose**: Hierarchical navigation showing current page location

**File**: `frontend/src/components/Breadcrumb.tsx`

#### Visual Design

- Links: Blue (`$blue-600`), underline on hover
- Separator: Gray chevron (`›`) between items
- Current page: No link, regular text weight

#### Example Structure

```
Knowledge Base › Articles › Article Title
```

#### Colors

- Links: `$blue-600` → `$blue-800` (hover)
- Separators: `$neutral-400`
- Current: `$neutral-700`

---

### SettingsDropdown

**Purpose**: User settings menu with AI mode toggle and authentication

**File**: `frontend/src/components/SettingsDropdown.tsx`

#### Features

- Settings button with dropdown
- AI mode segmented control (Local / Global)
- Logout button
- Sign in link (unauthenticated state)

#### Visual Design

- **Button**: Neutral colors, gear icon
- **Dropdown**: White panel, shadow, 320px width
- **Segmented control**: Active segment has white background with shadow
- **Logout**: Red text (`$red-600`), red background on hover (`$red-50`)

#### States

- **Authenticated**: Shows settings button + dropdown
- **Unauthenticated**: Shows "Sign In" link

---

## Content Components

### ArticleTableOfContents

**Purpose**: Sticky sidebar navigation for article headings

**File**: `frontend/src/components/ArticleTableOfContents.tsx`

#### Visual Design

- **Container**: White card with border, sticky positioned
- **Title**: "ON THIS PAGE" in uppercase, small, gray
- **Links**:
  - Default: `$neutral-600`
  - Hover: `$blue-700` with `$blue-50` background
  - Active: `$blue-700` text, medium weight, `$blue-50` background

#### Behavior

- Sticky at top: 32px from viewport top
- Highlights active section as user scrolls
- Smooth scroll on click

---

### MarkdownWithWikilinks

**Purpose**: Renders markdown content with wikilink support

**File**: `frontend/src/components/MarkdownWithWikilinks.tsx`

#### Features

- Full markdown rendering
- Wikilink parsing: `[[note-id]]` → clickable link
- Syntax highlighting for code blocks
- Typography styles for headings, lists, etc.

#### Visual Design

- Wikilinks: Blue underlined links
- Code blocks: Dark background with syntax highlighting
- Headings: Consistent hierarchy with proper spacing

---

### ProjectTile

**Purpose**: Clickable card for featuring projects on homepage

**File**: `frontend/src/components/ProjectTile.tsx`

#### Visual Design

- **Layout**: Horizontal flex (icon + content + arrow)
- **Icon**: Large emoji/icon (36px)
- **Title**: Bold, `$neutral-900` → `$blue-600` (hover)
- **Description**: Secondary text, `$neutral-600`
- **Arrow**: Right-facing, `$neutral-400` → `$blue-600` (hover)

#### Interaction

- Hover: Lifts up (-4px), border becomes `$blue-400`, shadow increases
- Smooth transition (0.3s ease)

#### Colors

- Border: `$neutral-200` → `$blue-400` (hover)
- Title: `$neutral-900` → `$blue-600` (hover)
- Arrow: `$neutral-400` → `$blue-600` (hover)

---

### TagPill

**Purpose**: Small tag/label for categorization

**File**: `frontend/src/components/TagPill.tsx`

#### Visual Design

- **Background**: `$neutral-100`
- **Text**: `$neutral-700`, 14px
- **Border radius**: Full rounded (9999px)
- **Padding**: 4px × 12px

#### Variants

- **Static**: No hover effect
- **Interactive**: Clickable, hover darkens to `$neutral-200`

---

## Notification Components

### Toast

**Purpose**: Temporary notification message at bottom-right

**File**: `frontend/src/components/Toast.tsx`

#### Visual Design

- **Position**: Fixed bottom-right (16px from edges)
- **Background**: `$green-600` (success theme)
- **Text**: White
- **Icon**: Checkmark circle
- **Close button**: X button, lighter text (`$green-100`)

#### Animation

- Slides up from bottom with fade-in (0.3s ease-out)
- Auto-dismisses after timeout (default: 3s)
- Manual close with X button

#### Example

```tsx
<Toast message="Note saved successfully!" />
```

---

### AuthStatusBanner

**Purpose**: Displays authentication status and prompts

**File**: `frontend/src/components/AuthStatusBanner.tsx`

#### Variants

| State | Color | Icon | Message |
|-------|-------|------|---------|
| Success | Green (`$green-50` bg) | ✓ | Successful authentication |
| Warning | Yellow (`$yellow-50` bg) | ⚠ | Temporary note warning |

#### Warning Message (Unauthenticated)

Shows when user creates notes without authentication:
- Yellow background (`$yellow-50`)
- Amber border and text (`$yellow-300`, `$amber-600`)
- Icon: Warning triangle
- Message: "Your changes will be lost when you close this tab"
- Action: "Sign In" link

---

## AI Components

### AIButton

**Purpose**: Floating action button to open AI panel

**File**: `frontend/src/components/AIButton.tsx`

#### Visual Design

- **Position**: Fixed bottom-right (24px from edges)
- **Size**: 56px × 56px circle
- **Background**: `$blue-600`
- **Icon**: Sparkles (✨), white
- **Shadow**: Large (`$shadow-card-lg`)

#### Interaction

- Hover: Scales to 1.1, darker blue (`$blue-700`)
- Click: Opens AI panel

---

### AIPanel

**Purpose**: Slide-out panel for AI interactions

**File**: `frontend/src/components/AIPanel.tsx`

#### Visual Design

- **Position**: Fixed right side, full height
- **Width**: 400px (desktop), 100% (mobile)
- **Animation**: Slides in from right
- **Background**: White with shadow

#### Features

- Search input
- AI Q&A interface
- Related note suggestions
- Close button

---

### AISuggestionsPanel

**Purpose**: Displays AI-suggested related notes

**File**: `frontend/src/components/AISuggestionsPanel.tsx`

#### Visual Design

- White card with border
- List of suggested notes with titles
- Each suggestion is clickable
- Empty state: "No suggestions available"

---

### PostSaveAISuggestions

**Purpose**: Shows AI suggestions immediately after saving a note

**File**: `frontend/src/components/PostSaveAISuggestions.tsx`

#### Behavior

- Triggers after note save
- Fetches AI-suggested links
- Displays in modal/panel
- User can accept or dismiss suggestions

---

## Note Components

### NoteEditor

**Purpose**: Rich text editor for creating and editing notes

**File**: `frontend/src/components/NoteEditor.tsx`

#### Features

- Title input field
- Content textarea (markdown-capable)
- Wikilink creation support
- Auto-save functionality
- Character count
- Save/Cancel buttons

#### Visual Design

- Full-width form layout
- White background
- Border on inputs
- Blue focus rings
- Button bar at bottom

---

### QuickLists

**Purpose**: Categorized note lists (Orphans, Hubs, Central Concepts)

**File**: `frontend/src/components/QuickLists/`

#### Categories

| Category | Color | Icon | Description |
|----------|-------|------|-------------|
| **Orphan Notes** | Yellow (`$yellow-50` bg) | ⚠️ | Notes with no links |
| **Hub Notes** | Blue (`$blue-50` bg) | 🔗 | Notes with many connections |
| **Central Concepts** | Purple (`$purple-50` bg) | ⭐ | Important conceptual notes |

#### Visual Design

Each category:
- Colored background (light shade)
- Colored border (medium shade)
- Colored heading (dark shade)
- Hover effect: Darker background
- Count badge showing number of notes

#### Example Layout

```
⚠️ Orphan Notes (5)
──────────────────
- Note without links 1
- Note without links 2

🔗 Hub Notes (3)
──────────────────
- Highly connected note 1
- Highly connected note 2
```

---

## Design Patterns

### Spacing

- **Component padding**: 16px (md), 24px (lg)
- **Vertical rhythm**: 16px between sections
- **Card gaps**: 16px in grids

### Typography

- **Headings**: `$neutral-700`, semibold weight
- **Body**: `$neutral-800`, normal weight
- **Secondary**: `$neutral-600`, 14px
- **Tertiary**: `$neutral-500`, 12px

### Shadows

- **Cards**: `$shadow-card-sm` (1px 3px)
- **Elevated**: `$shadow-card-md` (4px 6px)
- **Popover**: `$shadow-card-lg` (10px 15px)

### Borders

- **Default**: 1px solid `$neutral-200`
- **Strong**: 1px solid `$neutral-300`
- **Radius**: 4px (sm), 8px (md), 12px (lg)

### Transitions

- **Default**: 0.2s ease
- **Slow**: 0.3s ease (for transforms)
- **Colors only**: color, background-color 0.2s ease

### Interactive States

1. **Default**: Base color
2. **Hover**: Darken 1 shade, add background
3. **Active**: Darken 2 shades
4. **Focus**: Blue outline ring
5. **Disabled**: 50% opacity

---

## Component Composition Examples

### Article Page

```tsx
<Breadcrumb items={["Knowledge Base", "Articles", "Title"]} />
<div style={{ display: "flex", gap: "24px" }}>
  <article>
    <Badge type="article" />
    <h1>Article Title</h1>
    <MarkdownWithWikilinks content={content} />
  </article>
  <ArticleTableOfContents headings={headings} />
</div>
```

### Note Page

```tsx
<Badge type="note" />
<NoteEditor note={note} onSave={handleSave} />
<PostSaveAISuggestions noteId={note.id} />
<QuickLists />
```

### Homepage

```tsx
<Card variant="elevated" size="lg">
  <h2>Featured Projects</h2>
  <ProjectTile
    icon="🧠"
    title="Knowledge Base"
    description="Personal notes and articles"
    href="/knowledge-base"
  />
</Card>
```

---

## Accessibility

All components follow accessibility best practices:

- **Keyboard navigation**: Tab order, Enter/Space for actions
- **Focus indicators**: Visible focus rings on all interactive elements
- **ARIA labels**: Proper labeling for screen readers
- **Color contrast**: WCAG AA compliance (4.5:1 minimum)
- **Semantic HTML**: Proper heading hierarchy, landmarks

---

## Resources

- **Component Files**: `frontend/src/components/`
- **Design Tokens**: `frontend/src/styles/design-tokens/`
- **Mixins**: `frontend/src/styles/mixins/`
- **Color Reference**: See `COLOR_PALETTE.md`
- **Migration Guide**: See `UI_MIGRATION_GUIDE.md`
