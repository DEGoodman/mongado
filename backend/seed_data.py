"""Seed data for development with sample knowledge base articles."""

from datetime import datetime
from typing import Any

# Demo resources stored in markdown format
DEMO_RESOURCES: list[dict[str, Any]] = [
    {
        "id": 1,
        "title": "[DEMO] Understanding SaaS Billing Models",
        "content": """## Understanding different billing models is crucial for SaaS success.

**Common models include:**
- Usage-based billing
- Tiered pricing
- Per-seat pricing
- Freemium models

**Key considerations:**
1. Revenue predictability
2. Customer acquisition cost
3. Lifetime value calculation
4. Churn prevention strategies

Each model has trade-offs between simplicity and revenue optimization.""",
        "content_type": "markdown",
        "url": "https://stripe.com/billing",
        "tags": ["saas", "billing", "pricing", "demo"],
        "created_at": datetime(2025, 1, 15, 10, 0, 0).isoformat(),
    },
    {
        "id": 2,
        "title": "[DEMO] Implementing Usage-Based Billing",
        "content": """## Usage-based billing aligns costs with customer value.

**Implementation steps:**
1. Define measurable units
2. Track usage accurately
3. Set up metering infrastructure
4. Handle billing edge cases
5. Provide usage visibility to customers

### Technical considerations:
- Event streaming for real-time tracking
- Idempotency for duplicate events
- Data aggregation strategies
- Billing reconciliation processes

### Best practices:
- Set usage alerts for customers
- Offer spending caps
- Provide detailed usage breakdowns
- Consider prepaid credits

Usage-based billing requires robust infrastructure but can significantly improve customer satisfaction and revenue.""",
        "content_type": "markdown",
        "url": "https://aws.amazon.com/pricing/",
        "tags": ["saas", "billing", "usage-based", "implementation", "demo"],
        "created_at": datetime(2025, 1, 18, 14, 30, 0).isoformat(),
    },
    {
        "id": 3,
        "title": "[DEMO] Engineering Management: 1-on-1s Best Practices",
        "content": """## Effective 1-on-1 meetings are crucial for team success.

**Structure:**
- 30 minutes weekly or 1 hour biweekly
- Employee-driven agenda
- Private, consistent time
- Document action items

### Key topics to cover:
1. Career development and growth
2. Current project progress
3. Team dynamics and concerns
4. Feedback (both directions)
5. Work-life balance

### Common mistakes to avoid:
- Using 1-on-1s only for status updates
- Canceling or rescheduling frequently
- Not taking notes
- Doing all the talking
- Avoiding difficult conversations

### Questions to ask:
- What's energizing you right now?
- What's blocking you?
- How can I better support you?
- What would you like to learn next?

The best 1-on-1s are conversations, not status reports.""",
        "content_type": "markdown",
        "tags": ["management", "1-on-1s", "leadership", "team", "demo"],
        "created_at": datetime(2025, 1, 20, 9, 15, 0).isoformat(),
    },
    {
        "id": 4,
        "title": "[DEMO] SRE Golden Signals: The Four Key Metrics",
        "content": """## The Golden Signals provide comprehensive service health monitoring.

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

**Implementation tip:** Start with these four metrics before adding more observability. They cover most failure modes.""",
        "content_type": "markdown",
        "url": "https://sre.google/sre-book/monitoring-distributed-systems/",
        "tags": ["sre", "monitoring", "observability", "golden-signals", "demo"],
        "created_at": datetime(2025, 1, 22, 11, 45, 0).isoformat(),
    },
    {
        "id": 5,
        "title": "[DEMO] Building an Effective On-Call Rotation",
        "content": """## On-call rotations are essential for 24/7 service reliability.

### Rotation structure:
- **Primary and secondary** responders
- **Week-long** rotations (avoid daily swaps)
- **Handoff meetings** at rotation changes
- **Follow-the-sun** for global teams

### Essential components:

**1. Runbooks and playbooks**
- Clear escalation paths
- Common issue resolution steps
- Links to dashboards and logs

**2. Alert hygiene**
- Every alert must be actionable
- Clear severity levels
- Include context in alert messages

**3. Post-incident reviews**
- Blameless retrospectives
- Action items to prevent recurrence
- Share learnings across teams

### Reducing on-call burden:
- Automate common responses
- Improve monitoring and alerting
- Address root causes, not just symptoms
- Rotate fairly across team members

### Compensation and support:
- On-call pay or time off
- Clear expectations and boundaries
- Mental health resources
- Escalation to management when needed

**Remember:** A sustainable on-call rotation is a sign of system maturity and team health.""",
        "content_type": "markdown",
        "url": "https://increment.com/on-call/",
        "tags": ["sre", "on-call", "operations", "incident-response", "demo"],
        "created_at": datetime(2025, 1, 25, 16, 20, 0).isoformat(),
    },
    {
        "id": 6,
        "title": "[DEMO] Subscription Revenue Recognition in SaaS",
        "content": """## Revenue recognition for subscriptions follows ASC 606 framework.

### Key principles:

**1. Identify the contract**
- Written agreement with customer
- Commercial substance
- Payment terms defined

**2. Identify performance obligations**
- Distinct goods or services
- Separately identifiable
- Customer can benefit independently

**3. Determine transaction price**
- Fixed fees
- Variable consideration (usage charges)
- Discounts and incentives

**4. Allocate price to obligations**
- Based on standalone selling prices
- Proportional allocation

**5. Recognize revenue when obligations are satisfied**
- Over time for subscriptions
- Point in time for one-time fees

### Common SaaS scenarios:

**Monthly subscriptions:**
- Recognize ratably over subscription period
- Upfront payments = deferred revenue

**Annual contracts with monthly billing:**
- Recognize as service is delivered
- Invoice in advance ≠ revenue recognition

**Usage-based fees:**
- Recognize as usage occurs
- Estimate variable consideration

**Setup fees:**
- Typically recognized ratably over expected customer lifetime
- Unless distinct service provided

### Best practices:
- Use subscription management software
- Automate revenue schedules
- Regular reconciliation
- Work closely with accounting team

**Note:** This is educational content. Consult with accounting professionals for specific guidance.""",
        "content_type": "markdown",
        "url": "https://www.fasb.org/",
        "tags": ["saas", "billing", "accounting", "revenue-recognition", "demo"],
        "created_at": datetime(2025, 1, 28, 13, 10, 0).isoformat(),
    },
    {
        "id": 7,
        "title": "[DEMO] Engineering Ladders: Creating Clear Career Paths",
        "content": """## Engineering career ladders provide clarity and growth opportunities.

### Typical ladder structure:

**Junior Engineer (L3)**
- Executes on well-defined tasks
- Learning team processes and codebase
- Receives close mentorship

**Mid-level Engineer (L4)**
- Owns features end-to-end
- Mentors junior engineers
- Makes sound technical decisions
- Reduces ambiguity in requirements

**Senior Engineer (L5)**
- Leads large projects
- Defines technical strategy
- Influences team standards
- Cross-team collaboration

**Staff Engineer (L6)**
- Sets technical direction for multiple teams
- Solves complex, ambiguous problems
- Drives architectural decisions
- Multiplies team effectiveness

**Principal/Distinguished Engineer (L7+)**
- Organization-wide technical leadership
- Industry influence
- Critical project oversight
- Strategic technical vision

### Key dimensions to evaluate:

1. **Technical skill** - Depth and breadth of expertise
2. **Impact** - Scope and significance of contributions
3. **Leadership** - Influence without authority
4. **Communication** - Clarity and effectiveness
5. **Autonomy** - Self-direction and judgment

### Creating your ladder:

**Best practices:**
- Clear expectations at each level
- Examples of behaviors at each level
- Multiple paths (IC and management)
- Regular calibration across teams
- Public documentation

**Avoid:**
- Time-based promotions
- Single dimension evaluation
- Vague criteria
- Moving goalposts

### Using the ladder:

- **Hiring:** Consistent leveling of candidates
- **Performance reviews:** Clear evaluation criteria
- **Promotions:** Objective decision making
- **Development:** Roadmap for growth

**Remember:** Ladders are frameworks, not rigid rules. Adapt to your company culture and needs.""",
        "content_type": "markdown",
        "url": "https://www.progression.fyi/",
        "tags": ["management", "career-development", "engineering-ladder", "growth", "demo"],
        "created_at": datetime(2025, 2, 1, 10, 30, 0).isoformat(),
    },
]


def get_demo_resources() -> list[dict[str, Any]]:
    """Return a copy of demo resources for seeding the database.

    Returns:
        List of resource dictionaries with demo articles in markdown format.
    """
    return [resource.copy() for resource in DEMO_RESOURCES]
