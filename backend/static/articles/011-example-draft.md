---
id: 11
title: "Example Draft Article - Work in Progress"
tags: ["draft", "example"]
draft: true
published_date: "2025-10-29T00:00:00"
created_at: "2025-10-29T00:00:00"
---

## This is a Draft Article

This article is marked as `draft: true` in the frontmatter, which means:

- ✅ **Visible in local development** (when `DEBUG=true`)
- ❌ **Hidden in production** (when `DEBUG=false`)

## Use Cases

Draft articles are perfect for:

1. **Work in Progress**: Content you're still writing
2. **Review Required**: Articles waiting for review before publication
3. **Future Content**: Articles scheduled for future publication
4. **Experimental**: Testing new content formats or ideas

## How to Publish

When ready to publish, simply change the frontmatter:

```yaml
draft: false  # Change from true to false
published_date: "2025-10-29T00:00:00"  # Set to actual publish date
```

## Dates

Articles now support three date fields:

- `published_date`: When the article was first published
- `updated_date`: When the article was last updated (optional)
- `created_at`: Legacy field for backwards compatibility

The frontend will display:
- "Published [date]" on initial publication
- "Last updated [date]" when updated_date differs from published_date
