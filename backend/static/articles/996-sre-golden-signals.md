---
id: 996
title: "[DEMO] SRE Golden Signals: The Four Key Metrics"
url: "https://sre.google/sre-book/monitoring-distributed-systems/"
tags: ["sre", "monitoring", "observability", "golden-signals", "demo"]
created_at: "2025-01-22T11:45:00"
---

## The Golden Signals provide comprehensive service health monitoring.

### 1. Latency
Time to service a request. Track both successful and failed request latency separately.

**Key considerations:**
- 50th, 95th, 99th percentile tracking
- Distinguish between fast failures and slow successes
- Set SLOs based on user experience

### 2. Traffic
Measure of demand on your system (requests/second, transactions/day, etc.)

**Monitor:**
- Request rate patterns
- Seasonal variations
- Growth trends

### 3. Errors
Rate of failed requests (explicit failures, wrong content, policy violations)

**Track:**
- HTTP 5xx errors
- Application exceptions
- Timeouts and circuit breaker trips

### 4. Saturation
How "full" your service is (CPU, memory, disk, network)

**Watch for:**
- Resource utilization approaching limits
- Queue depths
- Thread pool exhaustion

**Implementation tip:** Start with these four metrics before adding more observability. They cover most failure modes.
