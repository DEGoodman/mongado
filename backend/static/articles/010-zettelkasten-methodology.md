---
id: 10
title: "Zettelkasten: Building a Personal Knowledge Graph"
description: "How the Zettelkasten method transforms note-taking from information storage into idea generation, with practical examples from this site's implementation."
category: knowledge-management
published: true
date: 2025-10-25
tags:
  - knowledge-management
  - zettelkasten
  - productivity
  - pkm
  - ai
---

# Zettelkasten: Building a Personal Knowledge Graph

## What This Is

Zettelkasten (German for "slip box") is a note-taking methodology that transforms scattered thoughts into a connected knowledge network. Instead of creating isolated notes in folders or notebooks, you create atomic ideas that link to each other, forming a graph of related concepts.

This article explains:
- What makes Zettelkasten different from traditional note-taking
- How I implemented it in this site's Notes system
- How AI features enhance the core methodology
- Real examples from my knowledge base

## The Core Problem

Traditional note-taking fails in two ways:

1. **Information silos**: Notes live in folders, notebooks, or documents. Finding connections requires remembering where you filed things.
2. **Passive storage**: You dump information and rarely revisit it. The act of writing becomes an end in itself, not a tool for thinking.

The result? You accumulate notes but generate few insights. Your notes become a graveyard of unconnected ideas.

## How Zettelkasten Works

### 1. Atomic Notes

Each note contains **one idea**. Not a topic, not a category—a single, complete thought.

**Bad**: "Systems Thinking" (too broad)
**Good**: "Feedback loops amplify or dampen changes in systems"

Atomic notes are:
- **Self-contained**: Readable without context
- **Specific**: One concept, clearly stated
- **Permanent**: Worth keeping long-term

### 2. Unique IDs

Every note gets a unique identifier. Traditional Zettelkasten used sequential numbering (1a, 1a1, 1a2). I use **adjective-noun pairs** for readability:

- `golden-tower` (Systems Thinking)
- `curious-phoenix` (Rocks and Barnacles)
- `giant-tower` (Observability)

Human-readable IDs make linking intuitive. You remember "link to golden-tower" better than "link to note 1234."

### 3. Wikilinks

Connect ideas with `[[note-id]]` syntax. Links are bidirectional—when you link A → B, you can also see that B is referenced by A.

Example from my `golden-tower` note (Systems Thinking):

```markdown
Key concepts:
- [[feedback-loops]] (reinforcing and balancing)
- [[second-order-effects]]
- [[leverage-points]] for change

Applications:
- [[postmortems]] (look beyond proximate cause)
- [[architecture-decisions]] (anticipate consequences)

Beware: [[local-optimization]] often hurts global performance
```

This creates a web of interconnected ideas. When you view a note, you see:
- **Outbound links**: Ideas this note references
- **Backlinks**: Notes that reference this idea

### 4. Progressive Elaboration

Start with a brief note. Return later to expand, link, and refine. Your knowledge base grows organically as you make connections.

Unlike hierarchical systems (folders, tags), there's no pressure to "file correctly" upfront. You discover structure through linking.

## Implementation: The Notes System

My implementation combines Zettelkasten principles with modern tooling:

### Core Features

**Persistent Notes** (Neo4j graph database):
- Bidirectional links between notes
- Graph visualization showing connections
- Full-text search across all notes

**Ephemeral Notes** (session-based):
- Visitors can create notes without authentication
- Temporary workspace for experimenting with ideas
- Automatically cleaned up after session expires

**Adjective-Noun IDs**:
- Generated from 78 adjectives × 70 nouns = 5,460 combinations
- Memorable: `wise-mountain`, `calm-eagle`, `curious-phoenix`
- Collision-resistant: Auto-retry on duplicates

**Markdown + Wikilinks**:
- Standard markdown for formatting
- `[[note-id]]` creates bidirectional links
- Missing notes become placeholders (create when needed)

### Example Workflow

1. **Capture an idea**: "Psychological safety enables teams to surface problems early"
2. **Create atomic note** with ID `calm-eagle`
3. **Link to related concepts**: `[[feedback-loops]]`, `[[postmortems]]`, `[[rocks-and-barnacles]]`
4. **View graph**: See how this connects to systems thinking, continuous delivery, tech debt

Over time, clusters emerge:
- Engineering management concepts
- Systems thinking frameworks
- Software delivery practices

You didn't plan these categories—they emerged from the connections.

## AI-Powered Enhancements

Traditional Zettelkasten requires manual discovery of connections. AI accelerates this by suggesting links and tags based on semantic similarity.

### Completed Features (Phase 1 MVP)

**1. Tag Suggestions**

POST `/api/notes/{note_id}/suggest-tags` returns AI-generated tags:

```json
{
  "suggestions": [
    {
      "tag": "systems-thinking",
      "confidence": 0.75,
      "reason": "Focuses on understanding interactions of system components"
    },
    {
      "tag": "feedback-loops",
      "confidence": 0.85,
      "reason": "Key concept related to how actions affect systems"
    }
  ]
}
```

**2. Link Suggestions**

POST `/api/notes/{note_id}/suggest-links` finds related notes:

```json
{
  "suggestions": [
    {
      "note_id": "giant-tower",
      "title": "Observability",
      "confidence": 0.9,
      "reason": "Observability applies systems thinking to understanding behavior from external outputs"
    },
    {
      "note_id": "curious-phoenix",
      "title": "Rocks and Barnacles",
      "confidence": 0.85,
      "reason": "Addresses technical debt using leverage points and second-order thinking"
    }
  ]
}
```

**3. Article Concept Extraction**

POST `/api/articles/{id}/extract-concepts` identifies ideas that should become notes:

From my "Rocks and Barnacles" article, AI suggested:
- Technical Debt Framework
- Barnacles (slow performance drag)
- Rocky Shoals (catastrophic risks)
- Psychological Safety
- Feature Prioritization

Each becomes a candidate for an atomic note.

**4. Settings Toggle**

Users opt-in to AI suggestions via settings. Default is OFF—AI assists but doesn't intrude.

**5. Suggestions Panel**

When editing a note, click "Get Suggestions" to see:
- Recommended tags (one-click to add)
- Related notes (one-click to insert wikilink)
- Confidence scores and reasoning

### In Development (Phase 2)

**Real-time suggestions while typing**:
- Suggest wikilinks as you type `[[`
- Auto-complete existing note IDs
- Suggest tags based on current content

**Graph intelligence**:
- Identify orphaned notes (no links)
- Find concept clusters (groups of related notes)
- Suggest missing connections (high semantic similarity, no link)

## Measuring Success

How do you know if your Zettelkasten is working?

**1. You generate new ideas**

You revisit old notes and discover connections you didn't see before. Example:

I wrote notes on "continuous delivery" and "psychological safety" months apart. Later, while writing about "postmortems," the backlinks showed both were relevant—leading to insight: blameless postmortems require both practices.

**2. Backlinks grow organically**

Popular notes accumulate backlinks naturally. My "systems-thinking" note has 12 backlinks—not because I planned it, but because the concept appears everywhere.

**3. Writing becomes faster**

When writing an article, I check related notes for ideas. The Rocks & Barnacles article referenced 6+ existing notes, providing structure and examples I'd already refined.

**4. Graph density increases**

Early on, most notes have 1-2 links. Over time, average links per note grows as you discover connections. My current average: 3.2 links/note (target: 5+).

## Common Pitfalls

**1. Notes too broad**

If your note covers multiple ideas, split it. "Continuous Integration" should become "Fast builds enable quick feedback" + "Green main branch reduces integration pain" + "Feature flags decouple deploy from release."

**2. Over-linking**

Don't link everything. Link concepts that **illuminate each other**. Linking "systems thinking" to every note that mentions "systems" creates noise.

**3. Perfectionism**

Don't spend 20 minutes crafting the perfect note. Write the idea, link what's obvious, move on. You'll refine later when connections become clear.

**4. Treating it like a wiki**

Zettelkasten isn't documentation. It's a thinking tool. Notes should reflect **your understanding**, not objective facts. Write in first person. Include questions and uncertainties.

**5. Ignoring orphans**

Notes with no links are probably too abstract or unclear. If you can't connect an idea to anything else, either clarify the idea or delete the note.

## Try It Yourself

You can explore my Zettelkasten implementation:

1. **Browse notes**: [mongado.com/knowledge-base/notes](https://mongado.com/knowledge-base/notes)
2. **View the graph**: [mongado.com/knowledge-base/notes/graph](https://mongado.com/knowledge-base/notes/graph)
3. **Create ephemeral notes**: No login required—experiment with wikilinks and see backlinks in action
4. **Enable AI suggestions**: Toggle in settings, edit a note, click "Get Suggestions"

The code is open source: [github.com/DEGoodman/mongado](https://github.com/DEGoodman/mongado)

## Key Takeaways

- **Atomic notes**: One idea per note
- **Wikilinks**: Create bidirectional connections
- **Progressive elaboration**: Start simple, refine over time
- **Emergent structure**: Categories appear through linking
- **AI assistance**: Accelerates connection discovery
- **Graph thinking**: Knowledge is relationships, not files

Zettelkasten transforms note-taking from **information storage** into **idea generation**. The more you link, the more connections you discover. AI suggestions amplify this effect by surfacing relationships you might have missed.

Start with a single note. Link it to another. Repeat. Your knowledge graph will grow.

## References

- Ahrens, Sönke. *How to Take Smart Notes*. 2017.
- Luhmann, Niklas. "Communicating with Slip Boxes." Original Zettelkasten archive.
- [Notes Implementation Guide](/knowledge-base/notes) - Technical details of this system
- [Multi-LLM Integration](/knowledge-base/articles/9) - How AI features work under the hood
