---
id: 5
title: "Software Delivery Performance Framework"
url: "https://itrevolution.com/product/accelerate/"
tags: ["operations", "management"]
draft: false
published_date: "2025-10-14T10:00:00"
created_at: "2025-10-14T10:00:00"
---

## Intro

People have been trying to measure the efficiency and productivity of software developers decades. Most of the obvious metrics are at best poor indicators and at worst reward detrimental behaviors. This document serves two objectives: to identify common anti-patterns and to propose a framework for effective, concrete measurements of productivity that enables rapid feedback while providing direct insight for improvements.

## Definitions

Lead Time: a measure of how fast work can be completed

- for us, "fuzzy frontend" (while issues are identified, planned, and prioritized) plus the time it takes to implement, test, and deliver

Tempo:

1. Time from code being committed to running live in production
2. Batch Size of code merged and/or deployed

## Bad Measurements of Performance

1. Lines of Code
2. Velocity
3. Utilization

### Lines of Code

- 1 complex line is worse than 10 clear lines, but 10 clear lines is better than 1000 lines of bloat
- "customer value" ≠ "how much code it took to implement"
- Disincentivizes maintainability, performance, and scalability of code base

### Velocity

- Velocity is a capacity planning tool, used e.g. extrapolating time to complete planned and estimated work
- measurements are relative only to themselves and meaningless outside context
- inhibits collaboration as developers/teams optimize for their own numbers

### Utilization

- Utilization is only good up to a point
- Queue Theory: as utilization approaches 100%, lead times approach infinity
    - i.e. higher levels of utilization means it takes longer to get anything done

## Good Measurements

1. Tempo
    1. ⏱️  from code being committed to running live in production
    2. Batch Size of changes
2. Mean Time To Restore (MTTR)
3. Fail Rate

For the purposes of this document, I am primarily interested in **Tempo** (a function of metrics 1 and 2 below), though MTTR and Fail Rate are worth brief asides

### Metric 1: Time from code committed to live in production

Principles

- WIP is a known blocker to productivity. People cannot effectively multitask and the more work you are trying to do in parallel, the longer each task will take and the less diligently they will be performed.
- Hypothesis: Minimizing Work In Progress will lead to more efficient turnaround of issues
- We consider Work In Progress to be any task that has been started by a developer and has not yet been merged in to master. Coding, testing, blocked, and open Merge Requests all count against WIP.
- Developers should aim to have no more than two issues in WIP at any time.

Caveats

- With daily builds we are at a hard limit for how much we can reduce this metric. Increasing the deployment frequency to several times per day would have numerous benefits including those discussed in Metric 2.

Deployment Frequency is measured in **# of deployments per developer per day**

### Metric 2: Batch Size

Principles

Smaller batches lead to:

- Reduced cycle time and variance in flow
- accelerated feedback of deployed features
- reduced risk and overhead of deployments
- improved efficiency across the organization
- increased motivation and urgency
- reduced cost and schedule growth

Caveats

- Until we have a true CD Pipeline, we will always be at a hard limit of deployments thus limiting the effectiveness of this metric.
- As we cannot optimize for deployment frequency beyond daily, the best metric here is on size of Merge Requests

Merge Requests

- What we are looking for here is the volume of changes. This means we are aggregating both lines added and lines removed as both are a change to the system.
- Smaller merge requests introduce less changes. The primary differences felt by average developers in day to day work are that it is easier to review (and get reviewed!) smaller MRs thus reducing WIP, and that it is easier to identify bugs that arise in production as the scope of potential locations are smaller.

Batch Size is (un-intuitively) measured by how long it takes to merge in changes to production branch. It is impossible to prescribe an optimal batch size, but we can use the length of time that a merge request stays open as a proxy measurement.

## Metric 3: MTTR

Mean Time to Restore is a great metric for system reliability, though is outside the scope of this discussion

## Metric 4: Fail Rate

Definition: Percentage of changes to production that

- experience degraded service or those where substantial remediation is required
    - service impairment or outage
    - hotfix/rollback/patch
    

| High Performance Teams | Medium Performance Teams |
|------------------------|-------------------------|
| M1: Multiple deployments per day | M1: 1 deployment per week to 1 per month |
| M2: < 1 hour | M2: 1 week to 1 month
| M3: < 1 hour | M3: < 1 day |
| M4: 0-15% | M4: 0-15% |


---

## References

[Accelerate: The Science of Lean Software and DevOps: Building and Scaling High Performing Technology Organizations](https://itrevolution.com/product/accelerate/)