# Mongado Frontend

Next.js-based frontend for the Mongado knowledge base application with rich text editing capabilities.

## Tech Stack

- **Next.js 14.2** - React framework with App Router
- **React 18.3** - UI library
- **TypeScript 5.9** - Type-safe JavaScript
- **Tailwind CSS 3.4** - Utility-first CSS framework
- **Tiptap 3.6** - Headless rich text editor
- **Vitest** - Fast unit testing framework
- **Playwright** - E2E testing

## Quick Start

### Development

```bash
# Install dependencies
npm install

# Run development server (with hot reload)
npm run dev

# Run tests
npm test

# Run all quality checks
npm run test:all
```

The app will be available at http://localhost:3000.

### Docker

```bash
# From project root
docker compose up

# Or build and run frontend only
docker build -t mongado-frontend -f frontend/Dockerfile frontend/
docker run -p 3000:3000 mongado-frontend
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js App Router pages
│   │   ├── layout.tsx      # Root layout
│   │   └── page.tsx        # Home page
│   ├── components/          # React components
│   │   ├── RichTextEditor.tsx   # Tiptap rich text editor
│   │   └── RichTextDisplay.tsx  # Render formatted content
│   ├── lib/                 # Utilities
│   │   └── logger.ts       # Frontend logging utility
│   └── __tests__/          # Unit tests
├── tests/e2e/              # Playwright E2E tests
├── public/                 # Static assets
└── package.json           # Dependencies & scripts
```

## Development Commands

### Running & Development
```bash
npm run dev             # Start dev server (http://localhost:3000)
npm install             # Install dependencies
```

### Testing
```bash
npm test                # Run unit tests (Vitest)
npm run test:ui         # Tests with UI viewer
npm run test:coverage   # Tests with coverage report
npm run test:e2e        # E2E tests (Playwright)
npm run test:e2e:ui     # E2E with Playwright UI
npm run test:all        # Full suite (typecheck + lint + tests)
```

### Code Quality
```bash
npm run lint            # ESLint
npm run lint:fix        # ESLint with auto-fix
npm run format          # Prettier formatting
npm run type-check      # TypeScript type checking
```

### Build & Deploy
```bash
npm run build           # Production build
npm run build:analyze   # Bundle size analysis
npm run start           # Serve production build
```

## Key Features

### Rich Text Editing

The app uses **Tiptap**, a modern headless rich text editor built on ProseMirror.

**Features:**
- Bold, italic, strikethrough formatting
- Headings (H1, H2, H3)
- Bulleted and numbered lists
- Blockquotes and code blocks
- Image uploads with preview
- Hyperlinks
- Undo/redo

**Components:**
- `RichTextEditor` (`src/components/RichTextEditor.tsx`) - Editor with toolbar
- `RichTextDisplay` (`src/components/RichTextDisplay.tsx`) - Render HTML content

**Usage Example:**
```tsx
import RichTextEditor from "@/components/RichTextEditor";

function MyComponent() {
  const [content, setContent] = useState("");
  const [html, setHtml] = useState("");

  const handleChange = (htmlContent: string, markdown: string) => {
    setHtml(htmlContent);
    setContent(markdown);
  };

  return (
    <RichTextEditor
      content={html}
      onChange={handleChange}
      placeholder="Start typing..."
    />
  );
}
```

### Logging

**Never use `console.log()`** in production code. Use the custom logger:

```tsx
import { logger } from "@/lib/logger";

// Basic logging
logger.info("Resource created", { id: resource.id });
logger.error("Failed to fetch", error);
logger.debug("Debug info", { data });

// Contextual logging
const apiLogger = logger.withContext("API");
apiLogger.info("Request sent", { endpoint: "/api/resources" });
```

**Features:**
- Auto-filters debug logs in production
- Pretty console output in development
- Context support for organized logs
- TypeScript-safe

### Styling

Using **Tailwind CSS** with the **Typography plugin** for prose styling:

```tsx
// Rich text content uses prose classes
<div className="prose prose-sm sm:prose lg:prose-lg max-w-none">
  {/* Formatted content here */}
</div>

// Custom styling
<button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
  Click me
</button>
```

## Environment Variables

Create a `.env.local` file in the frontend directory:

```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional: Analytics, feature flags, etc.
```

**Important:** Only variables prefixed with `NEXT_PUBLIC_` are exposed to the browser.

## Testing

### Unit Tests (Vitest)

Located in `src/__tests__/`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import MyComponent from "@/components/MyComponent";

describe("MyComponent", () => {
  it("renders correctly", () => {
    render(<MyComponent title="Test" />);
    expect(screen.getByText("Test")).toBeInTheDocument();
  });
});
```

**Run specific test:**
```bash
npm test src/__tests__/Component.test.tsx
```

### E2E Tests (Playwright)

Located in `tests/e2e/`:

```tsx
import { test, expect } from "@playwright/test";

test("create resource flow", async ({ page }) => {
  await page.goto("http://localhost:3000");
  await page.click('text="Add Resource"');
  await page.fill('input[type="text"]', "Test Resource");
  // ... more interactions
});
```

**Run with UI:**
```bash
npm run test:e2e:ui
```

### Mocking the Logger

In tests, mock the logger to avoid console noise:

```tsx
import { vi } from "vitest";

vi.mock("@/lib/logger", () => ({
  logger: {
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  },
}));
```

## Common Tasks

### Add a New Component

1. Create component file in `src/components/`
2. Use TypeScript for props
3. Add unit tests in `src/__tests__/`
4. Export from component file

Example:
```tsx
interface MyComponentProps {
  title: string;
  onSubmit: (value: string) => void;
}

export default function MyComponent({ title, onSubmit }: MyComponentProps) {
  const [value, setValue] = useState("");

  return (
    <div>
      <h2>{title}</h2>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button onClick={() => onSubmit(value)}>Submit</button>
    </div>
  );
}
```

### Add a New Page

1. Create file in `src/app/` (App Router)
2. File name determines route: `src/app/about/page.tsx` → `/about`
3. Export default component

Example:
```tsx
// src/app/about/page.tsx
export default function AboutPage() {
  return (
    <div>
      <h1>About Mongado</h1>
      <p>Knowledge base application</p>
    </div>
  );
}
```

### Add API Integration

```tsx
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchResources() {
  try {
    const response = await fetch(`${API_URL}/api/resources`);
    if (!response.ok) throw new Error("Failed to fetch");
    const data = await response.json();
    return data.resources;
  } catch (error) {
    logger.error("Error fetching resources", error);
    throw error;
  }
}
```

### Update Dependencies

```bash
# Check for outdated packages
npm outdated

# Update specific package
npm install <package>@latest

# Update all minor/patch versions
npm update

# Run tests after updates
npm run test:all
```

## Performance Optimization

### Bundle Analysis

```bash
npm run build:analyze
```

This opens an interactive bundle analyzer showing what's in your production bundle.

### Image Optimization

Use Next.js `Image` component for automatic optimization:

```tsx
import Image from "next/image";

<Image
  src="/logo.png"
  alt="Logo"
  width={500}
  height={300}
  priority  // For above-the-fold images
/>
```

### Code Splitting

Next.js automatically code-splits by page. For component-level splitting:

```tsx
import dynamic from "next/dynamic";

const HeavyComponent = dynamic(() => import("./HeavyComponent"), {
  loading: () => <p>Loading...</p>,
});
```

## Before Committing

Always run the full test suite:

```bash
npm run test:all
```

This runs:
1. TypeScript type checking
2. ESLint linting
3. All unit tests with coverage

All checks must pass before committing.

## Common Pitfalls

1. ❌ Don't use `console.log()` → ✅ Use `logger` from `@/lib/logger`
2. ❌ Don't skip TypeScript types → ✅ Define interfaces for all props
3. ❌ Don't fetch in components → ✅ Use proper data fetching patterns
4. ❌ Don't ignore accessibility → ✅ Use semantic HTML and ARIA labels
5. ❌ Don't commit without tests → ✅ Add tests for new components

## Browser Support

- Chrome (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- Edge (last 2 versions)

## Troubleshooting

### Build Errors

```bash
# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Hot Reload Not Working

1. Check that you're running `npm run dev`
2. Verify file is in `src/` directory
3. Restart dev server

### Type Errors

```bash
# Run type checker for detailed errors
npm run type-check
```

## Future Enhancements

- Server-side rendering for better SEO
- Advanced search with filters
- Markdown export/import
- Collaborative editing
- Dark mode
- Mobile-responsive improvements

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Tiptap Documentation](https://tiptap.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
