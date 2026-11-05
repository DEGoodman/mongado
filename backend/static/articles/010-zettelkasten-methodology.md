---
id: 10
title: "Zettelkasten: Building a Personal Knowledge Graph"
summary: "How the Zettelkasten method turns note-taking into a thinking tool through atomic notes and bidirectional links, and how this site's Notes system implements it."
description: "How the Zettelkasten method turns note-taking into a thinking tool, with examples from this site's implementation."
category: knowledge-management
draft: false
published_date: "2025-10-25T10:00:00"
created_at: "2025-10-25T10:00:00"
updated_date: "2026-11-04T00:00:00"
tags:
  - knowledge-management
  - zettelkasten
  - productivity
  - pkm
  - ai
---

## Intro

Most note systems are good at storing information and bad at helping you think with it. Notes go into folders, rarely get reread, and never connect to each other.

Zettelkasten (German for "slip box") is Niklas Luhmann's method for fixing that. You write small notes, one idea each, and link them directly to related notes. The links do the organizing. Over time you get a graph of ideas where new connections show up when you browse it.

This covers the method, the mistakes to avoid, and how the [Notes](/knowledge-base/notes) section of this site implements it.

## Definitions

- **Atomic note**: one idea, stated so it makes sense on its own
- **Note ID**: a permanent, unique identifier used for linking
- **Wikilink**: an inline link to another note, written `[[note-id]]`
- **Backlink**: a link *to* this note from another note, shown automatically
- **Orphan**: a note with no links in or out

## The Method

### 1. One idea per note

A note holds a single claim, not a topic.

- Too broad: "Systems Thinking"
- Atomic: "Feedback loops amplify or dampen changes in a system"

Atomic notes are:

- **Self-contained**: readable without opening another note
- **Specific**: one claim, stated plainly
- **Durable**: still worth reading in a year

### 2. Permanent IDs

Luhmann numbered notes by position (1a, 1a1, 1a2). This site uses random adjective-noun pairs like `wise-mountain` or `curious-elephant`. They're easier to remember and type than numbers, and they don't change when a note's title does.

### 3. Links instead of folders

Link a note to any note it relates to: `[[wise-mountain]]`. Each note shows its outbound links and its backlinks, so following a link works from either end.

A note on systems thinking might link out like this:

```markdown
Key mechanisms:
- [[swift-river]] (reinforcing vs balancing feedback loops)
- [[calm-harbor]] (second-order effects)

Where it applies:
- [[bold-falcon]] (postmortems: look past the proximate cause)

Watch out for [[quiet-meadow]]: local optimization often hurts the whole system.
```

The parenthetical says *why* the link exists. A bare list of links is much less useful when you come back to it six months later.

### 4. Write small, refine later

Write a short note and link the obvious connections. You'll return to it when another note links to it or when you're browsing nearby.

There's no need to decide where a note belongs. Clusters of related notes form as you link, and you see them in the graph.

## How This Site Implements It

**Storage**: Notes live in Neo4j as nodes, with links as edges, so backlinks are a graph query rather than a text search.

**IDs**: 78 adjectives × 70 nouns = 5,460 combinations. The generator retries on collision and falls back to a numeric suffix if every combination is taken.

**Editing**: Markdown with `[[note-id]]` links. Typing `[[` autocompletes against existing notes.

**Graph view**: The [graph](/knowledge-base/notes/graph) shows every note and link. "View in Graph" on any note opens the graph centered on that note.

**AI assistance** (off by default):

- **Link suggestions**: related notes ranked by embedding similarity, each with a short reason
- **Tag suggestions**: 2–4 tags with confidence scores
- **Modes**: off, on-demand (click for suggestions), or real-time (suggestions update as you type)

The AI finds candidate links. I still decide whether each one belongs, and write why it's there.

**Maintenance**: The [Inspire](/knowledge-base/inspire) page lists orphaned notes, notes long enough that they should probably be split, and notes developed enough to become articles.

## Pitfalls

- **Notes that are too broad.** If a note makes several claims, split it. "Continuous Integration" might become "Fast builds shorten the feedback loop", "A green main branch reduces integration pain", and "Feature flags decouple deploy from release."
- **Linking everything.** Link notes that explain each other, not every note that shares a word. A "systems thinking" link on every note that mentions "system" is noise.
- **Polishing on the first pass.** Write the idea, link what's obvious, move on. Most refinement happens on later visits.
- **Writing a wiki.** These notes record your own understanding, including open questions. Write in first person when it helps.
- **Ignoring orphans.** A note you can't connect to anything is usually unclear or too abstract. Rewrite it or delete it.

## Measuring Success

- **Links per note go up over time.** Early notes have one or two links; a working system keeps adding connections to old notes.
- **Backlinks surprise you.** You open a note and find it referenced from somewhere you didn't expect.
- **Writing gets faster.** When you start an article, the relevant notes already exist and are already linked.
- **Orphans stay rare.** New notes get connected soon after they're written.

## Conclusion

Write one idea per note, give each note a permanent ID, and link notes directly instead of filing them. The structure comes from the links. AI suggestions can speed up finding connections, but you still decide which ones to keep.

## References

- Ahrens, Sönke. *How to Take Smart Notes*. 2017.
- Luhmann, Niklas. "Communicating with Slip Boxes." 1981.
- [Notes system guide](https://github.com/DEGoodman/mongado/blob/main/docs/knowledge-base/NOTES.md): implementation details
- [Multi-LLM Integration](/knowledge-base/articles/9): how the AI features work
