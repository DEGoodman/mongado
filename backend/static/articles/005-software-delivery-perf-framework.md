---
id: 5
title: "Software Delivery Performance Framework"
summary: "A framework for measuring software delivery performance using four key metrics: lead time, deployment frequency, mean time to recovery, and change failure rate. Avoids common anti-patterns like velocity and utilization."
url: "https://itrevolution.com/product/accelerate/"
tags: ["operations", "management"]
draft: false
published_date: "2025-10-14T10:00:00"
created_at: "2025-10-14T10:00:00"
---

## Intro

People have been trying to measure the productivity of software developers for decades. Most of the obvious metrics are poor indicators at best, and at worst they reward harmful behavior. This document does two things: identifies common anti-patterns, and proposes concrete measurements that give fast feedback and point directly at what to improve.

## Definitions

**Lead Time**: how fast work gets completed.

- For us: the "fuzzy front end" (while issues are identified, planned, and prioritized) plus the time to implement, test, and deliver.

**Tempo**:

1. Time from code being committed to running live in production
2. Batch size of code merged and/or deployed

## Bad Measurements of Performance

1. Lines of Code
2. Velocity
3. Utilization

### Lines of Code

- 1 complex line is worse than 10 clear lines, but 10 clear lines are better than 1,000 lines of bloat
- "Customer value" ≠ "how much code it took to implement"
- Disincentivizes maintainability, performance, and scalability of the codebase

### Velocity

- Velocity is a capacity planning tool, e.g. for extrapolating time to complete planned and estimated work
- Measurements are relative only to themselves and meaningless outside their context
- Inhibits collaboration as developers and teams optimize for their own numbers

### Utilization

- Utilization is only good up to a point
- Queueing theory: as utilization approaches 100%, lead time approaches infinity
    - i.e. the busier everyone is, the longer it takes to get anything done

## Good Measurements

1. Tempo
    1. Time from code committed to running live in production
    2. Batch size of changes
2. Mean Time To Restore (MTTR)
3. Change Fail Rate

I'm primarily interested in **Tempo** (metrics 1 and 2 below). MTTR and fail rate get brief asides.

### Metric 1: Time from code committed to live in production

Principles

- Work in progress (WIP) is a known blocker to productivity. People can't multitask effectively: the more work in parallel, the longer each task takes and the less carefully it's done.
- Hypothesis: minimizing WIP leads to faster turnaround on issues.
- WIP is any task a developer has started that hasn't been merged into master. Coding, testing, blocked, and open merge requests all count.
- Developers should aim for no more than two issues in WIP at any time.

Caveats

- With daily builds, there's a hard floor on how far we can reduce this metric. Deploying several times per day would have many benefits, including those under Metric 2.

Deployment frequency is measured in **deployments per developer per day**.

### Metric 2: Batch Size

Principles

Smaller batches lead to:

- Reduced cycle time and less variance in flow
- Faster feedback on deployed features
- Lower risk and overhead per deployment
- Better efficiency across the organization
- More motivation and urgency
- Less cost and schedule growth

Caveats

- Until we have a real CD pipeline, deployment frequency is capped, which limits this metric.
- Since we can't deploy more than daily, the best proxy is merge request size.

Merge Requests

- We care about volume of change, so count lines added and lines removed. Both change the system.
- Smaller merge requests introduce fewer changes. Day to day, that means they're easier to review (and get reviewed), which reduces WIP. When something breaks in production, there are fewer places to look.

Batch size is (unintuitively) measured by how long a change takes to merge into the production branch. There's no single optimal batch size, but how long a merge request stays open is a good proxy.

### Metric 3: MTTR

Mean Time to Restore is a good measure of system reliability, but it's outside the scope of this document.

### Metric 4: Change Fail Rate

The percentage of changes to production that result in degraded service or need substantial remediation:

- Service impairment or outage
- Hotfix, rollback, or patch

## Benchmarks

From *Accelerate* (Forsgren, Humble, Kim):

| Metric | High performers | Medium performers |
|--------|-----------------|-------------------|
| Deployment frequency | Multiple per day | Once per week to once per month |
| Lead time for changes | < 1 hour | 1 week to 1 month |
| Time to restore | < 1 hour | < 1 day |
| Change fail rate | 0–15% | 0–15% |

---

## References

[Accelerate: The Science of Lean Software and DevOps: Building and Scaling High Performing Technology Organizations](https://itrevolution.com/product/accelerate/)
