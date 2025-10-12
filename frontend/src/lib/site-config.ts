/**
 * Site-wide configuration and constants
 * Centralizes common data for DRY principle and easy maintenance
 */

export const siteConfig = {
  name: "Mongado",
  author: {
    name: "D. Erik Goodman",
    fullTitle: "D. Erik Goodman",
    location: "Birmingham, AL",
    title: "Engineering Leader & Builder",
    bio: "Engineering leader with deep expertise in mission-critical SaaS product, infrastructure, and billing systems. I combine technical depth across multiple technology stacks with strategic business acumen to build engineering cultures that consistently deliver measurable results.",
  },
  links: {
    github: "https://github.com/DEGoodman",
    linkedin: "https://www.linkedin.com/in/d-erik-goodman/",
    email: "mailto:webmaster@mongado.com",
  },
  metadata: {
    title: "Mongado | D. Erik Goodman",
    description:
      "Personal website and knowledge base of D. Erik Goodman - Engineering leader and builder.",
  },
} as const;

export type SiteConfig = typeof siteConfig;
