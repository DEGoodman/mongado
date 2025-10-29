/**
 * Typography and spacing constants for consistent UI
 * Based on accessibility guidelines and standard responsive design
 */

export const typography = {
  // Font sizes (in px, will be converted to rem in Tailwind)
  sizes: {
    breadcrumb: "14px", // 0.875rem
    slug: "12px", // 0.75rem
    metadata: "14px", // 0.875rem
    tag: "14px", // 0.875rem
    // Responsive title sizes
    title: {
      mobile: "24px", // 1.5rem - h1 on mobile
      tablet: "28px", // 1.75rem - h1 on tablet
      desktop: "36px", // 2.25rem - h1 on desktop
    },
  },

  // Spacing (in px, will be converted to rem/units in Tailwind)
  spacing: {
    titleVertical: {
      mobile: "32px", // 2rem - vertical space around title on mobile
      desktop: "48px", // 3rem - vertical space around title on desktop
    },
    titleToMetadata: "16px", // 1rem - space between title and metadata
    metadataToTags: "16px", // 1rem - space between metadata and tags
  },

  // Font weights
  weights: {
    title: 700, // Bold for titles
    metadata: 400, // Regular for metadata
    breadcrumb: 400, // Regular for breadcrumbs
  },
} as const;

// Tailwind CSS classes for common typography patterns
export const typographyClasses = {
  // Page title (h1)
  title: "text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 leading-tight",

  // Breadcrumb navigation
  breadcrumb: "text-sm text-gray-600",

  // Metadata text (dates, authors)
  metadata: "text-sm text-gray-500",

  // Slug/ID text
  slug: "text-xs text-gray-400 font-mono",

  // Tag text
  tag: "text-sm",
} as const;
