---
id: 4
title: "Weekly Department Update Template"
summary: "A short weekly update template for engineering departments: headline, per-project status, risks, asks, and metrics. Built to be skimmed in two minutes and written in fifteen."
url: ""
tags: ["operations"]
draft: false
published_date: "2025-10-14T10:00:00"
created_at: "2025-10-14T10:00:00"
updated_date: "2026-11-04T00:00:00"
---

## Intro

A weekly update keeps leadership, peers, and your own teams on the same page without a status meeting. Most updates fail by being long: readers skim, miss the one thing that needed their attention, and stop opening them.

This template puts the decisions and risks first and everything else after.

## Template

```markdown
# Engineering Update: Week of <date>

## TL;DR
<2–3 sentences. What changed this week, and anything the reader needs to act on.>

## Asks
- <Decision or help needed> — from <person/team>, by <date>
- (or "None this week")

## Projects

| Project | Status | Change since last week | Next milestone |
|---------|--------|------------------------|----------------|
| <name>  | 🟢 / 🟡 / 🔴 | <one line> | <milestone> — <date> |

### <Project needing explanation (🟡 or 🔴 only)>
- **What happened:** <one or two lines>
- **Impact:** <dates, scope, customers>
- **Plan:** <what we're doing, owner>

## Risks
- <Risk> — likelihood <low/med/high>, impact <low/med/high>, mitigation <...>

## Metrics
| Metric | This week | Last week | Target |
|--------|-----------|-----------|--------|
| Deploys / day | | | |
| Lead time (commit → prod) | | | |
| Change fail rate | | | |
| Open incidents (Sev 1–2) | | | |

## People & Coordination
- <Hires, departures, on-call changes, cross-team dependencies>

## Coming Up
- <Milestones, launches, or meetings next week that affect other teams>
```

## Guidelines

- **Lead with asks.** If you need a decision, put it in the second section with a name and a date. Asks buried at the bottom don't get answered.
- **Explain only 🟡 and 🔴.** Green projects get one line in the table. Readers trust the color if it's used honestly.
- **Report changes, not activity.** "Shipped payment retries; failed checkouts down from 2.1% to 0.4%" beats "Worked on payments."
- **Keep the metrics fixed.** Track the same 3–5 every week so trends are visible. The [delivery metrics](/knowledge-base/articles/5) are a good default.
- **Keep it short.** If it takes more than two minutes to read, cut it. Link to detail instead of pasting it in.
- **Send it at the same time every week.** Readers start to rely on it, and a late update gets noticed.

## Pitfalls

- **Everything is green.** If nothing is ever yellow, readers stop believing the colors. Mark a project yellow as soon as it's at risk.
- **Copy-paste drift.** Last week's text carried forward unchanged. If a line didn't change, delete it.
- **Writing for your own team.** They already know the details. Write for someone two levels up or one team over.
