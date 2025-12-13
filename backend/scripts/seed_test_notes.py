#!/usr/bin/env python3
"""
Seed Neo4j database with structured test notes for development.

Structure:
- 5 entry point notes (10-13 links each)
- 8 hub notes (5-11 links)
- 40 atomic notes (2-3 links each)
- 15 stub notes (TODOs)
- 10 question notes
- 10 orphan notes (0 links)
- 10 reference notes (quick references: frameworks, checklists, acronyms)

Total: ~320 bidirectional links, 3.5 avg links/note
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.neo4j import Neo4jAdapter
from wikilink_parser import WikilinkParser


def seed_notes() -> None:
    """Seed database with 87 structured test notes."""
    # Initialize Neo4j adapter and wikilink parser
    neo4j_adapter = Neo4jAdapter()
    wikilink_parser = WikilinkParser()

    if not neo4j_adapter.is_available():
        print("❌ Neo4j is not available. Please start Neo4j and try again.")
        sys.exit(1)

    print("🌱 Seeding test notes...")

    # Define all note IDs first for referencing

    # Create notes with content and links
    notes_created = 0

    # Entry points (10-13 links each)
    entry_point_notes = [
        {
            "id": "engineering-leadership",
            "title": "Engineering Leadership",
            "content": """Effective engineering leadership combines technical excellence with people management.

Key areas:
- [[team-dynamics]] and building high-performing teams
- [[career-ladders]] and growth paths
- [[feedback-culture]] and continuous improvement
- [[one-on-ones]] for individual development
- [[stakeholder-management]] and communication
- [[decision-records]] for architectural choices
- [[technical-debt]] management
- [[code-quality]] standards
- [[incident-management]] response
- [[observability]] practices
- [[deployment-strategies]] planning
- [[technical-interview-process]] design

Related: [[sre-practices]], [[software-architecture]]""",
        },
        {
            "id": "sre-practices",
            "title": "Site Reliability Engineering Practices",
            "content": """SRE focuses on reliability, scalability, and operational excellence.

Core practices:
- [[slo-definition]] and service level objectives
- [[error-budget]] management
- [[incident-management]] and response
- [[postmortem-template]] for learning
- [[on-call-rotation]] scheduling
- [[alert-fatigue]] prevention
- [[runbook-structure]] documentation
- [[observability]] infrastructure
- [[metrics-collection]] systems
- [[distributed-tracing]] implementation
- [[monitoring-tools]] evaluation

Related: [[engineering-leadership]], [[ai-ml-systems]]""",
        },
        {
            "id": "knowledge-management",
            "title": "Knowledge Management Systems",
            "content": """Effective knowledge management enables better decision-making and reduces information silos.

Key concepts:
- [[decision-records]] for transparency
- [[documentation-debt]] reduction
- [[technical-writing-stub]] practices
- [[runbook-structure]] for operations
- [[postmortem-template]] documentation
- [[code-review-process]] knowledge sharing
- [[feedback-culture]] continuous learning
- [[stakeholder-management]] communication
- [[async-communication]] patterns
- [[team-dynamics]] knowledge flow

Methods: Zettelkasten, PARA, PKM systems

Related: [[engineering-leadership]], [[software-architecture]]""",
        },
        {
            "id": "software-architecture",
            "title": "Software Architecture Patterns",
            "content": """Architecture decisions have long-term impact on system maintainability and scalability.

Key patterns:
- [[microservices]] design
- [[api-design]] principles
- [[event-sourcing]] and [[cqrs-pattern]]
- [[versioning-strategy]] for APIs
- [[backward-compatibility]] maintenance
- [[feature-flags]] for progressive rollout
- [[deployment-strategies]] planning
- [[scaling-patterns]] for growth
- [[technical-debt]] management
- [[refactoring-strategy]] approaches
- [[code-quality]] standards
- [[security-review]] processes

Related: [[ai-ml-systems]], [[sre-practices]]""",
        },
        {
            "id": "ai-ml-systems",
            "title": "AI/ML Systems Engineering",
            "content": """Building production ML systems requires both ML and engineering expertise.

Key components:
- [[model-serving]] infrastructure
- [[training-pipeline]] automation
- [[feature-store]] management
- [[data-pipelines]] architecture
- [[model-monitoring]] and observability
- [[ab-testing]] for model comparison
- [[model-versioning]] strategies
- [[hyperparameter-tuning]] systems
- [[etl-process]] for data preparation
- [[data-validation]] frameworks
- [[deployment-strategies]] for models

Related: [[software-architecture]], [[sre-practices]]""",
        },
    ]

    # Pass 1: Create all notes WITHOUT links
    all_notes = []

    # Tags for entry point notes
    entry_point_tags = {
        "engineering-leadership": ["leadership", "management"],
        "sre-practices": ["sre", "operations"],
        "knowledge-management": ["management", "productivity"],
        "software-architecture": ["architecture", "system-design"],
        "ai-ml-systems": ["ml", "ai", "system-design"],
    }

    for note_data in entry_point_notes:
        tags = entry_point_tags.get(note_data["id"], [])
        all_notes.append((note_data["id"], note_data["content"], note_data["title"]))
        neo4j_adapter.create_note(
            note_data["id"], note_data["content"], note_data["title"], tags=tags
        )
        notes_created += 1
    print(f"✅ Created {len(entry_point_notes)} entry point notes")

    # Hub notes (5-11 links each)
    hub_notes = [
        {
            "id": "incident-management",
            "title": "Incident Management Process",
            "content": """Structured incident response minimizes impact and enables learning.

Process:
- [[on-call-rotation]] for coverage
- [[alert-fatigue]] prevention
- [[runbook-structure]] for response
- [[postmortem-template]] for analysis
- [[observability]] for debugging
- [[slo-definition]] for impact assessment
- [[error-budget]] tracking

Related: [[sre-practices]], [[engineering-leadership]]""",
        },
        {
            "id": "observability",
            "title": "Observability Infrastructure",
            "content": """Observability enables understanding system behavior in production.

Three pillars:
- [[metrics-collection]] - quantitative data
- [[distributed-tracing]] - request flow
- [[log-aggregation]] - event logs

Applications:
- [[incident-management]] debugging
- [[performance-optimization]] analysis
- [[model-monitoring]] for ML systems
- [[alert-fatigue]] reduction
- [[slo-definition]] tracking

Related: [[sre-practices]]""",
        },
        {
            "id": "team-dynamics",
            "title": "Engineering Team Dynamics",
            "content": """Healthy team dynamics drive productivity and satisfaction.

Elements:
- [[one-on-ones]] for individual support
- [[feedback-culture]] for growth
- [[career-ladders]] for progression
- [[async-communication]] for remote work
- [[code-review-process]] collaboration
- [[decision-records]] transparency

Related: [[engineering-leadership]]""",
        },
        {
            "id": "code-quality",
            "title": "Code Quality Standards",
            "content": """Maintaining code quality reduces bugs and improves maintainability.

Practices:
- [[code-review-process]] for peer review
- [[testing-pyramid]] strategy
- [[ci-cd-pipeline]] automation
- [[refactoring-strategy]] continuous improvement
- [[technical-debt]] management
- [[documentation-debt]] reduction

Related: [[software-architecture]]""",
        },
        {
            "id": "deployment-strategies",
            "title": "Deployment Strategies",
            "content": """Safe deployment practices minimize risk and enable rapid iteration.

Strategies:
- [[blue-green-deploy]] for zero downtime
- [[canary-release]] for gradual rollout
- [[feature-flags]] for control
- [[ci-cd-pipeline]] automation
- [[model-serving]] for ML systems

Related: [[software-architecture]], [[ai-ml-systems]]""",
        },
        {
            "id": "data-pipelines",
            "title": "Data Pipeline Architecture",
            "content": """Reliable data pipelines are foundational for analytics and ML.

Components:
- [[etl-process]] for transformation
- [[data-validation]] for quality
- [[schema-evolution]] management
- [[training-pipeline]] for ML
- [[feature-store]] for ML features

Related: [[ai-ml-systems]]""",
        },
        {
            "id": "model-serving",
            "title": "ML Model Serving",
            "content": """Production model serving requires reliability and performance.

Key aspects:
- [[deployment-strategies]] for rollout
- [[model-monitoring]] for drift
- [[model-versioning]] for rollback
- [[ab-testing]] for comparison
- [[feature-store]] for features
- [[api-design]] for inference

Related: [[ai-ml-systems]]""",
        },
        {
            "id": "technical-debt",
            "title": "Technical Debt Management",
            "content": """Strategic technical debt management balances speed and quality.

Types:
- [[documentation-debt]] gaps
- [[refactoring-strategy]] needs
- [[dependency-updates]] lag
- Code quality issues
- [[scaling-patterns]] limitations

Management:
- [[decision-records]] for tradeoffs
- Regular cleanup sprints
- Quality gates in [[ci-cd-pipeline]]

Related: [[software-architecture]]""",
        },
    ]

    # Tags for hub notes
    hub_tags = {
        "incident-management": ["sre", "operations"],
        "observability": ["sre", "operations"],
        "team-dynamics": ["leadership", "management"],
        "code-quality": ["engineering", "best-practices"],
        "deployment-strategies": ["operations", "ci-cd"],
        "data-pipelines": ["ml", "data-engineering"],
        "model-serving": ["ml", "operations"],
        "technical-debt": ["technical-debt", "engineering"],
    }

    for note_data in hub_notes:
        tags = hub_tags.get(note_data["id"], [])
        all_notes.append((note_data["id"], note_data["content"], note_data["title"]))
        neo4j_adapter.create_note(
            note_data["id"], note_data["content"], note_data["title"], tags=tags
        )
        notes_created += 1
    print(f"✅ Created {len(hub_notes)} hub notes")

    # Atomic notes (2-3 links each)
    # (note_id, title, content, tags)
    atomic_note_data = [
        (
            "slo-definition",
            "Service Level Objectives",
            "SLOs define reliability targets. Work with [[error-budget]] and measured by [[metrics-collection]].",
            ["sre", "operations"],
        ),
        (
            "error-budget",
            "Error Budgets",
            "Error budgets balance reliability and velocity. Based on [[slo-definition]].",
            ["sre", "operations"],
        ),
        (
            "postmortem-template",
            "Postmortem Templates",
            "Blameless postmortems enable learning. Part of [[incident-management]].",
            ["sre", "operations"],
        ),
        (
            "on-call-rotation",
            "On-Call Rotation",
            "Fair on-call rotation prevents burnout. Part of [[incident-management]] with [[runbook-structure]].",
            ["sre", "operations"],
        ),
        (
            "alert-fatigue",
            "Alert Fatigue",
            "Too many alerts reduce effectiveness. Addressed through [[observability]] and better [[slo-definition]].",
            ["sre", "operations"],
        ),
        (
            "runbook-structure",
            "Runbook Structure",
            "Clear runbooks speed incident response. Used in [[incident-management]].",
            ["sre", "operations"],
        ),
        (
            "metrics-collection",
            "Metrics Collection",
            "Time-series metrics enable monitoring. Core to [[observability]].",
            ["sre", "operations"],
        ),
        (
            "distributed-tracing",
            "Distributed Tracing",
            "Traces show request flow across services. Part of [[observability]].",
            ["sre", "operations"],
        ),
        (
            "log-aggregation",
            "Log Aggregation",
            "Centralized logs aid debugging. Component of [[observability]].",
            ["sre", "operations"],
        ),
        (
            "one-on-ones",
            "One-on-One Meetings",
            "Regular 1:1s build trust and provide feedback. Key to [[team-dynamics]].",
            ["leadership", "one-on-ones"],
        ),
        (
            "feedback-culture",
            "Feedback Culture",
            "Regular feedback accelerates growth. Enables [[team-dynamics]].",
            ["leadership", "management"],
        ),
        (
            "career-ladders",
            "Career Ladders",
            "Clear progression paths retain talent. Part of [[team-dynamics]].",
            ["leadership", "management"],
        ),
        (
            "code-review-process",
            "Code Review Process",
            "Effective code reviews improve quality. Central to [[code-quality]] and [[team-dynamics]].",
            ["engineering", "best-practices"],
        ),
        (
            "testing-pyramid",
            "Testing Pyramid",
            "Balance unit, integration, and e2e tests. Foundation of [[code-quality]].",
            ["testing", "engineering"],
        ),
        (
            "ci-cd-pipeline",
            "CI/CD Pipeline",
            "Automated pipelines enable fast delivery. Supports [[code-quality]] and [[deployment-strategies]].",
            ["operations", "ci-cd"],
        ),
        (
            "feature-flags",
            "Feature Flags",
            "Feature flags decouple deploy from release. Key to [[deployment-strategies]].",
            ["operations", "experimentation"],
        ),
        (
            "blue-green-deploy",
            "Blue-Green Deployment",
            "Zero-downtime deployments using two environments. A [[deployment-strategies]] pattern.",
            ["operations", "system-design"],
        ),
        (
            "canary-release",
            "Canary Releases",
            "Gradual rollout to subset of users. A [[deployment-strategies]] approach with [[ab-testing]].",
            ["operations", "experimentation"],
        ),
        (
            "event-sourcing",
            "Event Sourcing",
            "Store state as sequence of events. An [[software-architecture]] pattern.",
            ["architecture", "system-design"],
        ),
        (
            "cqrs-pattern",
            "CQRS Pattern",
            "Separate read and write models. Often paired with [[event-sourcing]].",
            ["architecture", "system-design"],
        ),
        (
            "microservices",
            "Microservices Architecture",
            "Independently deployable services. A [[software-architecture]] pattern.",
            ["architecture", "system-design"],
        ),
        (
            "api-design",
            "API Design Principles",
            "Well-designed APIs are intuitive. Critical for [[software-architecture]] and [[model-serving]].",
            ["architecture", "system-design"],
        ),
        (
            "versioning-strategy",
            "API Versioning Strategy",
            "Version APIs to manage change. Enables [[backward-compatibility]].",
            ["architecture", "system-design"],
        ),
        (
            "backward-compatibility",
            "Backward Compatibility",
            "Maintain compatibility to avoid breaking clients. Part of [[versioning-strategy]].",
            ["architecture", "system-design"],
        ),
        (
            "etl-process",
            "ETL Process",
            "Extract, transform, load data. Foundation of [[data-pipelines]].",
            ["ml", "data-engineering"],
        ),
        (
            "data-validation",
            "Data Validation",
            "Validate data quality early. Critical for [[data-pipelines]].",
            ["ml", "data-engineering"],
        ),
        (
            "schema-evolution",
            "Schema Evolution",
            "Evolve data schemas safely. Important for [[data-pipelines]].",
            ["ml", "data-engineering"],
        ),
        (
            "model-monitoring",
            "ML Model Monitoring",
            "Monitor model performance in production. Essential for [[model-serving]] via [[observability]].",
            ["ml", "operations"],
        ),
        (
            "feature-store",
            "Feature Store",
            "Centralized feature management. Shared by [[data-pipelines]] and [[model-serving]].",
            ["ml", "data-engineering"],
        ),
        (
            "ab-testing",
            "A/B Testing",
            "Compare model or feature variants. Used in [[model-serving]] and [[canary-release]].",
            ["ml", "experimentation"],
        ),
        (
            "training-pipeline",
            "Training Pipeline",
            "Automated model training. Part of [[data-pipelines]].",
            ["ml", "data-engineering"],
        ),
        (
            "hyperparameter-tuning",
            "Hyperparameter Tuning",
            "Optimize model hyperparameters. Part of [[training-pipeline]].",
            ["ml", "experimentation"],
        ),
        (
            "model-versioning",
            "Model Versioning",
            "Version models for reproducibility. Essential for [[model-serving]].",
            ["ml", "operations"],
        ),
        (
            "refactoring-strategy",
            "Refactoring Strategy",
            "Incrementally improve code design. Addresses [[technical-debt]] while maintaining [[code-quality]].",
            ["engineering", "technical-debt"],
        ),
        (
            "documentation-debt",
            "Documentation Debt",
            "Missing or outdated docs. A form of [[technical-debt]].",
            ["technical-debt", "productivity"],
        ),
        (
            "dependency-updates",
            "Dependency Updates",
            "Keep dependencies current. Prevents [[technical-debt]] accumulation.",
            ["technical-debt", "operations"],
        ),
        (
            "security-review",
            "Security Review Process",
            "Regular security assessments. Part of [[code-quality]].",
            ["security", "engineering"],
        ),
        (
            "performance-optimization",
            "Performance Optimization",
            "Systematically improve performance. Uses [[observability]] data.",
            ["operations", "engineering"],
        ),
        (
            "scaling-patterns",
            "Scaling Patterns",
            "Patterns for horizontal and vertical scaling. Part of [[software-architecture]].",
            ["architecture", "system-design"],
        ),
        (
            "async-communication",
            "Asynchronous Communication",
            "Communication patterns for distributed teams. Enables [[team-dynamics]].",
            ["leadership", "productivity"],
        ),
        (
            "decision-records",
            "Architecture Decision Records",
            "Document significant decisions. Supports [[software-architecture]] and [[team-dynamics]].",
            ["architecture", "management"],
        ),
        (
            "stakeholder-management",
            "Stakeholder Management",
            "Manage expectations and communication. Critical for [[engineering-leadership]].",
            ["leadership", "management"],
        ),
    ]

    for note_id, title, content, tags in atomic_note_data:
        all_notes.append((note_id, content, title))
        neo4j_adapter.create_note(note_id, content, title, tags=tags)
        notes_created += 1
    print(f"✅ Created {len(atomic_note_data)} atomic notes")

    # Stub notes (minimal content with TODOs) - leave untagged intentionally
    stub_note_data: list[tuple[str, str, str, list[str]]] = [
        (
            "chaos-engineering-stub",
            "Chaos Engineering",
            "TODO: Add chaos engineering principles and practices.",
            [],
        ),
        (
            "service-mesh-stub",
            "Service Mesh",
            "TODO: Document service mesh patterns (Istio, Linkerd).",
            [],
        ),
        ("gitops-stub", "GitOps", "TODO: Explain GitOps deployment model.", []),
        (
            "platform-engineering-stub",
            "Platform Engineering",
            "TODO: Document internal developer platforms.",
            [],
        ),
        (
            "developer-experience-stub",
            "Developer Experience",
            "TODO: Catalog DX improvement strategies.",
            [],
        ),
        (
            "cost-optimization-stub",
            "Cloud Cost Optimization",
            "TODO: Add cost optimization techniques.",
            [],
        ),
        (
            "compliance-automation-stub",
            "Compliance Automation",
            "TODO: Document automated compliance checks.",
            [],
        ),
        (
            "disaster-recovery-stub",
            "Disaster Recovery",
            "TODO: Add DR planning and testing procedures.",
            [],
        ),
        (
            "capacity-planning-stub",
            "Capacity Planning",
            "TODO: Document capacity planning methodologies.",
            [],
        ),
        (
            "technical-writing-stub",
            "Technical Writing",
            "TODO: Add technical writing best practices.",
            [],
        ),
        ("api-gateway-stub", "API Gateway", "TODO: Document API gateway patterns.", []),
        ("rate-limiting-stub", "Rate Limiting", "TODO: Add rate limiting strategies.", []),
        (
            "authentication-patterns-stub",
            "Authentication Patterns",
            "TODO: Document auth patterns (OAuth, OIDC, etc).",
            [],
        ),
        (
            "authorization-models-stub",
            "Authorization Models",
            "TODO: Add authorization models (RBAC, ABAC).",
            [],
        ),
        (
            "data-retention-stub",
            "Data Retention Policies",
            "TODO: Document data retention strategies.",
            [],
        ),
    ]

    for note_id, title, content, tags in stub_note_data:
        all_notes.append((note_id, content, title))
        neo4j_adapter.create_note(note_id, content, title, tags=tags)
        notes_created += 1
    print(f"✅ Created {len(stub_note_data)} stub notes")

    # Question notes (exploring open topics)
    question_note_data = [
        (
            "how-to-measure-productivity",
            "How to Measure Developer Productivity?",
            "What metrics truly reflect productivity? Lines of code? PRs merged? Impact? Related to [[engineering-leadership]] and [[team-dynamics]].",
            ["leadership", "management"],
        ),
        (
            "when-to-split-microservices",
            "When Should We Split Microservices?",
            "How do we know when a service is too large? Related to [[microservices]] and [[software-architecture]].",
            ["architecture", "system-design"],
        ),
        (
            "best-monitoring-tools",
            "What Are the Best Monitoring Tools?",
            "Evaluating Prometheus, Datadog, New Relic, Grafana. Related to [[observability]] and [[metrics-collection]].",
            ["sre", "operations"],
        ),
        (
            "ml-model-accuracy-vs-latency",
            "How to Balance Model Accuracy vs Latency?",
            "Trade-offs between model complexity and serving speed. Related to [[model-serving]] and [[performance-optimization]].",
            ["ml", "operations"],
        ),
        (
            "database-sharding-strategy",
            "What's the Right Database Sharding Strategy?",
            "When and how to shard databases? Related to [[scaling-patterns]] and [[data-pipelines]].",
            ["architecture", "system-design"],
        ),
        (
            "team-size-optimization",
            "What's the Optimal Team Size?",
            "2-pizza rule vs larger teams. Related to [[engineering-leadership]] and [[team-dynamics]].",
            ["leadership", "management"],
        ),
        (
            "technical-interview-process",
            "How to Design Fair Technical Interviews?",
            "Balancing signal with candidate experience. Related to [[engineering-leadership]].",
            ["leadership", "interviewing"],
        ),
        (
            "remote-work-practices",
            "What Are Effective Remote Work Practices?",
            "Tools and culture for distributed teams. Related to [[team-dynamics]] and [[async-communication]].",
            ["leadership", "productivity"],
        ),
        (
            "open-source-contribution",
            "How to Contribute to Open Source?",
            "Getting started with OSS contributions. Related to [[code-quality]] and [[documentation-debt]].",
            ["engineering", "productivity"],
        ),
        (
            "learning-new-technologies",
            "How to Efficiently Learn New Technologies?",
            "Strategies for continuous learning. Related to [[feedback-culture]].",
            ["productivity", "learning"],
        ),
    ]

    for note_id, title, content, tags in question_note_data:
        all_notes.append((note_id, content, title))
        neo4j_adapter.create_note(note_id, content, title, tags=tags)
        notes_created += 1
    print(f"✅ Created {len(question_note_data)} question notes")

    # Reference notes (quick references: frameworks, checklists, acronyms)
    # These use is_reference=True to distinguish from Zettelkasten insights
    reference_note_data = [
        (
            "dora-metrics",
            "DORA Metrics",
            """The four key metrics from the DORA research program for measuring software delivery performance:

1. **Deployment Frequency** - How often code is deployed to production
2. **Lead Time for Changes** - Time from commit to production
3. **Mean Time to Recovery (MTTR)** - Time to restore service after incident
4. **Change Failure Rate** - Percentage of deployments causing failures

Related: [[sre-practices]], [[deployment-strategies]], [[ci-cd-pipeline]]""",
            ["sre", "metrics"],
        ),
        (
            "biceps-framework",
            "BICEPS Framework",
            """Core needs framework for understanding what people need at work:

- **B**elonging - Connection to a group
- **I**mprovement - Progress and growth
- **C**hoice - Autonomy and control
- **E**quality - Fair treatment
- **P**redictability - Certainty about the future
- **S**ignificance - Status and meaning

Related: [[team-dynamics]], [[one-on-ones]], [[feedback-culture]]""",
            ["leadership", "management"],
        ),
        (
            "eisenhower-matrix",
            "Eisenhower Matrix",
            """Prioritization framework based on urgency and importance:

|              | Urgent | Not Urgent |
|--------------|--------|------------|
| Important    | DO     | SCHEDULE   |
| Not Important| DELEGATE | DELETE   |

Related: [[stakeholder-management]], [[engineering-leadership]]""",
            ["productivity", "management"],
        ),
        (
            "testing-pyramid-ref",
            "Testing Pyramid Reference",
            """Standard testing distribution:

```
        /\\
       /E2E\\        (~10%)
      /------\\
     /Integration\\   (~20%)
    /--------------\\
   /    Unit Tests   \\ (~70%)
  /------------------\\
```

- **Unit**: Fast, isolated, many
- **Integration**: Medium speed, service boundaries
- **E2E**: Slow, full user flows, few

Related: [[testing-pyramid]], [[code-quality]]""",
            ["testing", "best-practices"],
        ),
        (
            "smart-goals",
            "SMART Goals Framework",
            """Goal-setting framework:

- **S**pecific - Clear and well-defined
- **M**easurable - Quantifiable progress
- **A**chievable - Realistic and attainable
- **R**elevant - Aligned with broader objectives
- **T**ime-bound - Has a deadline

Related: [[career-ladders]], [[one-on-ones]]""",
            ["management", "productivity"],
        ),
        (
            "http-status-codes",
            "HTTP Status Code Quick Reference",
            """Common HTTP status codes:

**2xx Success**
- 200 OK
- 201 Created
- 204 No Content

**4xx Client Errors**
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 429 Too Many Requests

**5xx Server Errors**
- 500 Internal Server Error
- 502 Bad Gateway
- 503 Service Unavailable

Related: [[api-design]]""",
            ["engineering", "api"],
        ),
        (
            "git-commands-ref",
            "Git Commands Quick Reference",
            """Essential git commands:

**Branching**
```bash
git checkout -b feature/name
git merge --no-ff feature/name
git rebase main
```

**Undoing**
```bash
git reset --soft HEAD~1  # undo commit, keep changes staged
git reset --hard HEAD~1  # undo commit, discard changes
git revert <commit>      # create new commit undoing changes
```

**Inspection**
```bash
git log --oneline --graph
git diff --stat
git blame <file>
```

Related: [[code-review-process]], [[ci-cd-pipeline]]""",
            ["engineering", "git"],
        ),
        (
            "incident-severity-levels",
            "Incident Severity Levels",
            """Standard incident classification:

| Level | Name | Description | Response |
|-------|------|-------------|----------|
| SEV1 | Critical | Full outage, data loss | All hands, 24/7 |
| SEV2 | Major | Partial outage, degraded | On-call + backup |
| SEV3 | Minor | Limited impact | On-call during hours |
| SEV4 | Low | Cosmetic, workaround exists | Normal priority |

Related: [[incident-management]], [[on-call-rotation]], [[slo-definition]]""",
            ["sre", "operations"],
        ),
        (
            "rest-api-conventions",
            "REST API Conventions",
            """Standard RESTful patterns:

**HTTP Methods**
- GET - Read (idempotent)
- POST - Create
- PUT - Update/Replace (idempotent)
- PATCH - Partial update
- DELETE - Remove (idempotent)

**URL Structure**
```
GET    /resources          # List
POST   /resources          # Create
GET    /resources/{id}     # Read
PUT    /resources/{id}     # Update
DELETE /resources/{id}     # Delete
```

**Response Codes**
- 200/201 for success
- 400 for client errors
- 500 for server errors

Related: [[api-design]], [[versioning-strategy]]""",
            ["engineering", "api"],
        ),
        (
            "twelve-factor-app",
            "12-Factor App Checklist",
            """The twelve factors for modern app development:

1. **Codebase** - One codebase, many deploys
2. **Dependencies** - Explicitly declare and isolate
3. **Config** - Store in environment
4. **Backing Services** - Treat as attached resources
5. **Build, Release, Run** - Strictly separate stages
6. **Processes** - Execute as stateless processes
7. **Port Binding** - Export services via port binding
8. **Concurrency** - Scale out via process model
9. **Disposability** - Fast startup, graceful shutdown
10. **Dev/Prod Parity** - Keep environments similar
11. **Logs** - Treat as event streams
12. **Admin Processes** - Run as one-off processes

Related: [[microservices]], [[deployment-strategies]], [[software-architecture]]""",
            ["architecture", "best-practices"],
        ),
    ]

    for note_id, title, content, tags in reference_note_data:
        all_notes.append((note_id, content, title))
        neo4j_adapter.create_note(note_id, content, title, tags=tags, is_reference=True)
        notes_created += 1
    print(f"✅ Created {len(reference_note_data)} reference notes")

    # Orphan notes (no links - for testing orphan detection) - leave untagged
    orphan_note_data: list[tuple[str, str, str, list[str]]] = [
        (
            "random-thought-1",
            "Random Thought 1",
            "This note has no links to other notes. Used for testing orphan detection.",
            [],
        ),
        ("random-thought-2", "Random Thought 2", "Another isolated note without connections.", []),
        ("random-thought-3", "Random Thought 3", "Testing orphan note functionality.", []),
        ("random-thought-4", "Random Thought 4", "Standalone note for graph testing.", []),
        ("random-thought-5", "Random Thought 5", "Unconnected note example.", []),
        ("random-thought-6", "Random Thought 6", "Isolated note for orphan detection.", []),
        ("random-thought-7", "Random Thought 7", "No wikilinks in this note.", []),
        ("random-thought-8", "Random Thought 8", "Another orphan note for testing.", []),
        ("random-thought-9", "Random Thought 9", "Disconnected from the main graph.", []),
        ("random-thought-10", "Random Thought 10", "Final orphan note for testing.", []),
    ]

    for note_id, title, content, tags in orphan_note_data:
        all_notes.append((note_id, content, title))
        neo4j_adapter.create_note(note_id, content, title, tags=tags)
        notes_created += 1
    print(f"✅ Created {len(orphan_note_data)} orphan notes")

    print(f"\n🎉 Successfully created {notes_created} notes!")

    # Pass 2: Create all links (now that all notes exist)
    print("\n📎 Creating links between notes...")
    links_created = 0
    if neo4j_adapter.driver:
        with neo4j_adapter.driver.session() as session:
            for note_id, content, _title in all_notes:
                links = wikilink_parser.extract_links(content)
                if links:
                    neo4j_adapter._create_links(session, note_id, links)
                    links_created += len(links)
    print(f"✅ Created {links_created} links")
    print("\nExpected structure:")
    print("  - 5 entry point notes (10-13 links each)")
    print("  - 8 hub notes (5-11 links)")
    print("  - 40 atomic notes (2-3 links each)")
    print("  - 15 stub notes (TODOs)")
    print("  - 10 question notes")
    print("  - 10 reference notes (is_reference=True)")
    print("  - 10 orphan notes (0 links)")
    print("  - Total: ~320 bidirectional links")

    # Verify by querying count
    if neo4j_adapter.driver:
        with neo4j_adapter.driver.session() as session:
            result = session.run("MATCH (n:Note) RETURN count(n) as count")
            record = result.single()
            count = record["count"] if record else 0
            print(f"\n✅ Verified: {count} notes in database")

            # Count links
            link_result = session.run("MATCH ()-[r:LINKS_TO]->() RETURN count(r) as count")
            link_record = link_result.single()
            link_count = link_record["count"] if link_record else 0
            print(f"✅ Verified: {link_count} links in database")


if __name__ == "__main__":
    seed_notes()
