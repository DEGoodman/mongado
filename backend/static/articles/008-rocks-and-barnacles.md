---
id: 8
title: "Rocks & Barnacles: Surfacing Technical Debt"
tags: ["Engineering Management", "Technical Debt", "Operations"]
created_at: "2025-10-24T10:00:00"
---

## Intro

Technical debt and infrastructure problems rarely make it onto roadmaps. Teams suffer through long build times, flaky tests, and deployment headaches, accepting them as "just how things are." This framework provides a structured approach to surface hidden problems, democratically prioritize them, and get them addressed alongside feature work.

## Definitions

If your team is a pirate ship navigating to treasure island, certain factors propel you forward while others slow you down or threaten to sink you entirely.

**Barnacles**: Problems that gradually slow the team down day after day, creating drag and reducing velocity.

Examples: long build times, daily-only deployments, flaky tests, manual processes, poor documentation, difficult local setup

**Rocky Shoals**: Catastrophic risks lurking in the future that could halt all progress if you collide with them.

Examples: no backup strategy, security vulnerabilities, approaching scalability limits, single points of failure, deprecated dependencies with no migration plan, lack of disaster recovery

## The Framework

### Process (90-120 minutes)

**Phase 1: Silent Brainstorming (15-20 min)**

- Everyone works silently
- One problem per sticky note (physical or digital)
- Be specific with measurements where possible
- Place in "Barnacles" or "Rocky Shoals" column
- No discussion yet

**Phase 2: Share Out (30-40 min)**

- Round-robin presentation (2-3 min per person)
- Clarifying questions only - no solutions or debates
- Group similar items
- Capture all items verbatim

**Phase 3: Voting (10 min)**

- Each person gets 3 votes
- Can distribute however desired (3 on one item, 1 each on 3 items, etc.)
- Vote for impact, not ease of fix
- Silent voting

**Phase 4: Discussion (30-40 min)**

For top 3 voted items, discuss:

- **Impact**: Quantified cost (time, money, morale, risk)
- **Root cause**: Why does this exist?
- **Potential solutions**: Multiple options
- **Rough effort**: Days? Weeks? Months?
- **Dependencies**: What needs to happen first?

Timebox: ~10 minutes per item. Capture unknowns. Don't commit to solutions yet.

**Phase 5: Follow-up (Post-meeting)**

Manager responsibilities:

1. Document all items, create GitHub issues for top 3
2. Present to Product Manager with business case
3. Negotiate roadmap space
4. Report back to team within 1-2 weeks
5. Show progress and celebrate fixes

## Setup

**In-person:**
- Two wall sections: "Barnacles" and "Rocky Shoals"
- Sticky notes, markers
- 3 voting dots per person

**Remote:**
- Digital whiteboard (Miro, Mural, FigJam)
- Two columns with sticky note capability
- Test access beforehand

**Pre-work:**
- Send framework and pirate ship metaphor in meeting invite
- Ask people to come with 2-3 items
- Emphasize psychological safety

## Cadence

Run this exercise twice per year:

1. **Pre-annual planning** (November): Surface issues before H1 planning begins
2. **Pre-H2 planning** (April/May): Reset priorities and identify new problems

This timing ensures technical debt gets visibility during roadmap planning cycles.

## Common Pitfalls

**Jumping to solutions during brainstorming**
Fix: "Capture that for Phase 4. Right now just write the problem."

**Manager shares first, everyone anchors on it**
Fix: Go last or don't share. This is about team perspective.

**No follow-through**
Fix: Address at least ONE item within next sprint. Build trust.

**Groupthink during brainstorming**
Fix: Enforce silent generation. No talking.

**Voting for easy wins instead of important wins**
Fix: Remind to vote for biggest difference, not easiest fix.

**Vague problem statements**
Fix: During share-out ask "Can you quantify that?" Get numbers.

## Variations

**Time-constrained (60 min)**: 10 min brainstorm, 20 min share (30 sec each), 5 min vote, 25 min discuss top 3

**Async (remote/timezone-distributed)**: 2-3 days to add items, 1 day voting window, 1 hour sync to discuss top 3

**Focus version**: Just Barnacles OR just Rocky Shoals for deeper exploration

## Why This Works

**Psychological safety**: Framing as "barnacles" and "rocky shoals" makes it safe to voice frustrations without sounding negative. Teams find the pirate ship metaphor amusing and disarming.

**Democratic prioritization**: Team's collective wisdom surfaces most impactful issues, not just loudest voices.

**Data for roadmap negotiation**: Product managers need evidence to prioritize tech debt. This provides concrete data.

**Visible progress**: When barnacles get scraped off, whole team feels the ship move faster.

**Ownership**: Team identified and voted on problems, creating buy-in when solutions ship.

## Example: Real Session Output

**Top Barnacles (by votes):**

1. "CI takes 25 minutes, blocks all PR merges" - 12 votes
   - Impact: 10 engineers × 3 PRs/day × 25 min = 12.5 hours/day waiting
   - Solutions: Parallelization (2-3 days), split fast/slow suites (1 week), smart test selection (2 weeks)

2. "Local dev setup takes 4 hours, half the time it fails" - 9 votes
   - Impact: Every new hire, every machine refresh, developer re-clones
   - Solutions: Docker-based setup (1 week), better docs (2 days), setup script (3 days)

3. "Deploy happens once daily at 6pm, blocks urgent fixes" - 7 votes
   - Impact: Customer-facing bugs sit for 24 hours
   - Solutions: Multi-deploy pipeline (2 weeks), hotfix process (3 days)

**Top Rocky Shoals:**

1. "Database backups exist but never tested restore" - 11 votes
   - Impact: Unknown if we can actually recover from disaster
   - Solutions: Quarterly restore drill (1 day setup + recurring), automated restore testing (1 week)

## Measuring Success

- Team morale improves (retro feedback, surveys)
- Concrete items get addressed (track completion rate)
- Velocity increases (sprint velocity trends up)
- Incident rate decreases (fewer rocky shoal collisions)
- Team proactively raises issues (culture shift)

## Integration with Existing Processes

**Sprint planning**: Reserve 10-20% capacity for barnacle/rocky shoal backlog

**Retrospectives**: Celebrate fixed items, identify new ones

**Semi-annual planning**: Bring top-voted items with impact data to H1/H2 planning

**1-on-1s**: Ask "Any new barnacles or rocky shoals?" Keep running list.

**Incident reviews**: Check if rocky shoals were previously surfaced

## Timeline Example

- **Week 1**: Schedule, send framework, set up workspace
- **Week 2**: Run 90-min session, capture results, create issues
- **Week 3**: Present to PM, make business case, get buy-in
- **Week 4**: Report to team, start work on top item
- **Within 1-2 sprints**: Ship first fix, celebrate, show metrics

## Conclusion

Technical debt doesn't manage itself. Without structured surfacing and prioritization, issues compound until they either sink the ship or slow it to a crawl.

Run this twice a year before planning cycles. Reserve roadmap capacity for the output. Close the feedback loop by showing progress. Build a culture where keeping the ship fast and seaworthy matters as much as reaching the next island.

## References

Based on practices from high-performing engineering teams and concepts from lean manufacturing (reducing WIP, continuous improvement) adapted for software delivery.
