# GitHub Issues Guide

This document explains how to use GitHub Issues for tracking work on the Mongado project.

## Overview

We use GitHub Issues to track:
- Article ideas and content planning
- Feature development
- Infrastructure improvements
- Bug fixes
- Documentation tasks

## Label System

### Status Labels (Workflow)

Track where work is in the development lifecycle:

- **`status: idea`** - Initial brainstorming, not ready to start
- **`status: todo`** - Ready to be worked on (backlog)
- **`status: in-progress`** - Currently being worked on
- **`status: done`** - Completed work (close issue when done)

**Workflow**: `idea` → `todo` → `in-progress` → `done` (close)

### Category Labels (Type of Work)

Classify the type of work:

- **`feature`** - New feature or enhancement
- **`bug`** - Something isn't working
- **`infrastructure`** - Infrastructure, deployment, DevOps
- **`documentation`** - Documentation improvements
- **`article-idea`** - Future article topics to develop

### Topic Labels (Content Area)

Tag content-related work:

- **`saas`** - SaaS-related topics (billing, revenue, etc.)
- **`management`** - Engineering management and leadership
- **`sre`** - Site Reliability Engineering

### Default GitHub Labels

Standard labels (can be used but not required):

- `enhancement` - New feature or request
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention is needed
- `question` - Further information is requested

## Usage Examples

### Creating an Article Idea

```bash
gh issue create \
  --title "Article: Your Article Title" \
  --label "article-idea,management,status: idea" \
  --body "Description of the article..."
```

**Labels**: Always include `article-idea`, a topic label (saas/management/sre), and `status: idea`

### Creating a Feature Request

```bash
gh issue create \
  --title "Feature: Your Feature Name" \
  --label "feature,status: todo" \
  --body "Description of the feature..."
```

**Labels**: Include `feature`, optionally `infrastructure` or topic labels, and appropriate status

### Creating a Bug Report

```bash
gh issue create \
  --title "Bug: Description of the bug" \
  --label "bug,status: todo" \
  --body "Steps to reproduce..."
```

**Labels**: Always include `bug` and `status: todo` (bugs start ready to work)

## Updating Issue Status

As you work on issues, update the status label:

```bash
# Start working on an issue
gh issue edit 123 --remove-label "status: todo" --add-label "status: in-progress"

# Complete and close an issue
gh issue edit 123 --remove-label "status: in-progress" --add-label "status: done"
gh issue close 123
```

## Finding Issues

### View all article ideas
```bash
gh issue list --label "article-idea"
```

### View ready-to-work items
```bash
gh issue list --label "status: todo"
```

### View work in progress
```bash
gh issue list --label "status: in-progress"
```

### View by topic
```bash
gh issue list --label "management"
gh issue list --label "sre"
gh issue list --label "saas"
```

## Best Practices

### 1. Always Use Status Labels

Every issue should have exactly one status label:
- New issues: `status: idea` or `status: todo`
- Active work: `status: in-progress`
- Completed: `status: done` + close the issue

### 2. Use Descriptive Titles

- **Good**: "Article: SRE Golden Signals - The Four Key Metrics"
- **Good**: "Feature: Note Templates for Book/Person/Concept"
- **Bad**: "Fix the thing"
- **Bad**: "New article"

### 3. Include Context in Description

Every issue should have:
- **Goal**: What are we trying to achieve?
- **Context**: Why is this important?
- **Tasks**: Checklist of specific work items (if applicable)
- **Priority**: When should this be done?

### 4. Close Issues When Done

When work is complete:
1. Update status to `status: done`
2. Close the issue with a comment linking to the PR or commit
3. Reference the issue in commit messages: `fixes #123`

### 5. Link Related Issues

Use GitHub's linking syntax in descriptions:
- `Relates to #123` - Related work
- `Depends on #123` - Blocking dependency
- `Closes #123` - Automatically closes when merged

## Projects and Milestones

### Using GitHub Projects (Optional)

You can create GitHub Projects to organize issues into boards:
- Kanban board with columns: Ideas / To Do / In Progress / Done
- Drag issues between columns to update status
- Visualize work pipeline

### Using Milestones (Optional)

Group related issues into milestones:
- Q1 2025
- Q2 2025
- Homepage Launch
- Authentication System

## Mobile Workflow

Since you wanted to brainstorm article ideas away from your laptop:

### GitHub Mobile App
1. Download GitHub mobile app
2. Browse issues, create new ones
3. Update labels and status
4. Add comments and ideas

### Web Browser
- https://github.com/DEGoodman/mongado/issues
- Fully functional on mobile
- Create, edit, and manage issues

## Current Issues

As of 2025-10-24, we have:

- **7 article ideas** (#1-7) - All `status: idea`
- **Authentication system** (#8) - `status: todo`
- **Neo4j backups** (#9) - `status: todo` (high priority!)
- **Ollama upgrade** (#10) - `status: idea`
- **Homepage development** (#11) - `status: todo`
- **Database migration** (#12) - `status: idea`
- **Note templates** (#13) - `status: idea`
- **Testing coverage** (#14) - `status: todo`
- **AI auto-tagging** (#15) - `status: idea`

## Tips

1. **Create issues liberally** - Better to capture ideas than forget them
2. **Update status regularly** - Helps track progress
3. **Close completed work** - Keeps issue list clean
4. **Use search and filters** - GitHub issue search is powerful
5. **Reference in commits** - `fixes #123` in commit messages auto-closes issues

---

For more on GitHub Issues: https://docs.github.com/en/issues
