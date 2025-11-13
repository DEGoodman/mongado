#!/usr/bin/env python3
"""
Seed Neo4j database with 87 structured test notes for development.

Structure:
- 5 entry point notes (10-13 links each)
- 8 hub notes (5-11 links)
- 40 atomic notes (2-3 links each)
- 15 stub notes (TODOs)
- 10 question notes
- 10 orphan notes (0 links)

Total: 308 bidirectional links, 3.5 avg links/note
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

Related: [[sre-practices]], [[software-architecture]]"""
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

Related: [[engineering-leadership]], [[ai-ml-systems]]"""
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

Related: [[engineering-leadership]], [[software-architecture]]"""
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

Related: [[ai-ml-systems]], [[sre-practices]]"""
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

Related: [[software-architecture]], [[sre-practices]]"""
        }
    ]

    # Pass 1: Create all notes WITHOUT links
    all_notes = []

    for note_data in entry_point_notes:
        all_notes.append((note_data["id"], note_data["content"], note_data["title"]))
        neo4j_adapter.create_note(
            note_data["id"],
            note_data["content"],
            note_data["title"]
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

Related: [[sre-practices]], [[engineering-leadership]]"""
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

Related: [[sre-practices]]"""
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

Related: [[engineering-leadership]]"""
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

Related: [[software-architecture]]"""
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

Related: [[software-architecture]], [[ai-ml-systems]]"""
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

Related: [[ai-ml-systems]]"""
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

Related: [[ai-ml-systems]]"""
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

Related: [[software-architecture]]"""
        }
    ]

    for note_data in hub_notes:
        all_notes.append((note_data["id"], note_data["content"], note_data["title"]))
        neo4j_adapter.create_note(
            note_data["id"],
            note_data["content"],
            note_data["title"]
        )
        notes_created += 1
    print(f"✅ Created {len(hub_notes)} hub notes")

    # Atomic notes (2-3 links each)
    atomic_note_data = [
        ("slo-definition", "Service Level Objectives", "SLOs define reliability targets. Work with [[error-budget]] and measured by [[metrics-collection]]."),
        ("error-budget", "Error Budgets", "Error budgets balance reliability and velocity. Based on [[slo-definition]]."),
        ("postmortem-template", "Postmortem Templates", "Blameless postmortems enable learning. Part of [[incident-management]]."),
        ("on-call-rotation", "On-Call Rotation", "Fair on-call rotation prevents burnout. Part of [[incident-management]] with [[runbook-structure]]."),
        ("alert-fatigue", "Alert Fatigue", "Too many alerts reduce effectiveness. Addressed through [[observability]] and better [[slo-definition]]."),
        ("runbook-structure", "Runbook Structure", "Clear runbooks speed incident response. Used in [[incident-management]]."),
        ("metrics-collection", "Metrics Collection", "Time-series metrics enable monitoring. Core to [[observability]]."),
        ("distributed-tracing", "Distributed Tracing", "Traces show request flow across services. Part of [[observability]]."),
        ("log-aggregation", "Log Aggregation", "Centralized logs aid debugging. Component of [[observability]]."),
        ("one-on-ones", "One-on-One Meetings", "Regular 1:1s build trust and provide feedback. Key to [[team-dynamics]]."),
        ("feedback-culture", "Feedback Culture", "Regular feedback accelerates growth. Enables [[team-dynamics]]."),
        ("career-ladders", "Career Ladders", "Clear progression paths retain talent. Part of [[team-dynamics]]."),
        ("code-review-process", "Code Review Process", "Effective code reviews improve quality. Central to [[code-quality]] and [[team-dynamics]]."),
        ("testing-pyramid", "Testing Pyramid", "Balance unit, integration, and e2e tests. Foundation of [[code-quality]]."),
        ("ci-cd-pipeline", "CI/CD Pipeline", "Automated pipelines enable fast delivery. Supports [[code-quality]] and [[deployment-strategies]]."),
        ("feature-flags", "Feature Flags", "Feature flags decouple deploy from release. Key to [[deployment-strategies]]."),
        ("blue-green-deploy", "Blue-Green Deployment", "Zero-downtime deployments using two environments. A [[deployment-strategies]] pattern."),
        ("canary-release", "Canary Releases", "Gradual rollout to subset of users. A [[deployment-strategies]] approach with [[ab-testing]]."),
        ("event-sourcing", "Event Sourcing", "Store state as sequence of events. An [[software-architecture]] pattern."),
        ("cqrs-pattern", "CQRS Pattern", "Separate read and write models. Often paired with [[event-sourcing]]."),
        ("microservices", "Microservices Architecture", "Independently deployable services. A [[software-architecture]] pattern."),
        ("api-design", "API Design Principles", "Well-designed APIs are intuitive. Critical for [[software-architecture]] and [[model-serving]]."),
        ("versioning-strategy", "API Versioning Strategy", "Version APIs to manage change. Enables [[backward-compatibility]]."),
        ("backward-compatibility", "Backward Compatibility", "Maintain compatibility to avoid breaking clients. Part of [[versioning-strategy]]."),
        ("etl-process", "ETL Process", "Extract, transform, load data. Foundation of [[data-pipelines]]."),
        ("data-validation", "Data Validation", "Validate data quality early. Critical for [[data-pipelines]]."),
        ("schema-evolution", "Schema Evolution", "Evolve data schemas safely. Important for [[data-pipelines]]."),
        ("model-monitoring", "ML Model Monitoring", "Monitor model performance in production. Essential for [[model-serving]] via [[observability]]."),
        ("feature-store", "Feature Store", "Centralized feature management. Shared by [[data-pipelines]] and [[model-serving]]."),
        ("ab-testing", "A/B Testing", "Compare model or feature variants. Used in [[model-serving]] and [[canary-release]]."),
        ("training-pipeline", "Training Pipeline", "Automated model training. Part of [[data-pipelines]]."),
        ("hyperparameter-tuning", "Hyperparameter Tuning", "Optimize model hyperparameters. Part of [[training-pipeline]]."),
        ("model-versioning", "Model Versioning", "Version models for reproducibility. Essential for [[model-serving]]."),
        ("refactoring-strategy", "Refactoring Strategy", "Incrementally improve code design. Addresses [[technical-debt]] while maintaining [[code-quality]]."),
        ("documentation-debt", "Documentation Debt", "Missing or outdated docs. A form of [[technical-debt]]."),
        ("dependency-updates", "Dependency Updates", "Keep dependencies current. Prevents [[technical-debt]] accumulation."),
        ("security-review", "Security Review Process", "Regular security assessments. Part of [[code-quality]]."),
        ("performance-optimization", "Performance Optimization", "Systematically improve performance. Uses [[observability]] data."),
        ("scaling-patterns", "Scaling Patterns", "Patterns for horizontal and vertical scaling. Part of [[software-architecture]]."),
        ("async-communication", "Asynchronous Communication", "Communication patterns for distributed teams. Enables [[team-dynamics]]."),
        ("decision-records", "Architecture Decision Records", "Document significant decisions. Supports [[software-architecture]] and [[team-dynamics]]."),
        ("stakeholder-management", "Stakeholder Management", "Manage expectations and communication. Critical for [[engineering-leadership]]."),
    ]

    for note_id, title, content in atomic_note_data:
        all_notes.append((note_id, content, title))
        neo4j_adapter.create_note(note_id, content, title)
        notes_created += 1
    print(f"✅ Created {len(atomic_note_data)} atomic notes")

    # Stub notes (minimal content with TODOs)
    stub_note_data = [
        ("chaos-engineering-stub", "Chaos Engineering", "TODO: Add chaos engineering principles and practices."),
        ("service-mesh-stub", "Service Mesh", "TODO: Document service mesh patterns (Istio, Linkerd)."),
        ("gitops-stub", "GitOps", "TODO: Explain GitOps deployment model."),
        ("platform-engineering-stub", "Platform Engineering", "TODO: Document internal developer platforms."),
        ("developer-experience-stub", "Developer Experience", "TODO: Catalog DX improvement strategies."),
        ("cost-optimization-stub", "Cloud Cost Optimization", "TODO: Add cost optimization techniques."),
        ("compliance-automation-stub", "Compliance Automation", "TODO: Document automated compliance checks."),
        ("disaster-recovery-stub", "Disaster Recovery", "TODO: Add DR planning and testing procedures."),
        ("capacity-planning-stub", "Capacity Planning", "TODO: Document capacity planning methodologies."),
        ("technical-writing-stub", "Technical Writing", "TODO: Add technical writing best practices."),
        ("api-gateway-stub", "API Gateway", "TODO: Document API gateway patterns."),
        ("rate-limiting-stub", "Rate Limiting", "TODO: Add rate limiting strategies."),
        ("authentication-patterns-stub", "Authentication Patterns", "TODO: Document auth patterns (OAuth, OIDC, etc)."),
        ("authorization-models-stub", "Authorization Models", "TODO: Add authorization models (RBAC, ABAC)."),
        ("data-retention-stub", "Data Retention Policies", "TODO: Document data retention strategies."),
    ]

    for note_id, title, content in stub_note_data:
        all_notes.append((note_id, content, title))
        neo4j_adapter.create_note(note_id, content, title)
        notes_created += 1
    print(f"✅ Created {len(stub_note_data)} stub notes")

    # Question notes (exploring open topics)
    question_note_data = [
        ("how-to-measure-productivity", "How to Measure Developer Productivity?", "What metrics truly reflect productivity? Lines of code? PRs merged? Impact? Related to [[engineering-leadership]] and [[team-dynamics]]."),
        ("when-to-split-microservices", "When Should We Split Microservices?", "How do we know when a service is too large? Related to [[microservices]] and [[software-architecture]]."),
        ("best-monitoring-tools", "What Are the Best Monitoring Tools?", "Evaluating Prometheus, Datadog, New Relic, Grafana. Related to [[observability]] and [[metrics-collection]]."),
        ("ml-model-accuracy-vs-latency", "How to Balance Model Accuracy vs Latency?", "Trade-offs between model complexity and serving speed. Related to [[model-serving]] and [[performance-optimization]]."),
        ("database-sharding-strategy", "What's the Right Database Sharding Strategy?", "When and how to shard databases? Related to [[scaling-patterns]] and [[data-pipelines]]."),
        ("team-size-optimization", "What's the Optimal Team Size?", "2-pizza rule vs larger teams. Related to [[engineering-leadership]] and [[team-dynamics]]."),
        ("technical-interview-process", "How to Design Fair Technical Interviews?", "Balancing signal with candidate experience. Related to [[engineering-leadership]]."),
        ("remote-work-practices", "What Are Effective Remote Work Practices?", "Tools and culture for distributed teams. Related to [[team-dynamics]] and [[async-communication]]."),
        ("open-source-contribution", "How to Contribute to Open Source?", "Getting started with OSS contributions. Related to [[code-quality]] and [[documentation-debt]]."),
        ("learning-new-technologies", "How to Efficiently Learn New Technologies?", "Strategies for continuous learning. Related to [[feedback-culture]]."),
    ]

    for note_id, title, content in question_note_data:
        all_notes.append((note_id, content, title))
        neo4j_adapter.create_note(note_id, content, title)
        notes_created += 1
    print(f"✅ Created {len(question_note_data)} question notes")

    # Orphan notes (no links - for testing orphan detection)
    orphan_note_data = [
        ("random-thought-1", "Random Thought 1", "This note has no links to other notes. Used for testing orphan detection."),
        ("random-thought-2", "Random Thought 2", "Another isolated note without connections."),
        ("random-thought-3", "Random Thought 3", "Testing orphan note functionality."),
        ("random-thought-4", "Random Thought 4", "Standalone note for graph testing."),
        ("random-thought-5", "Random Thought 5", "Unconnected note example."),
        ("random-thought-6", "Random Thought 6", "Isolated note for orphan detection."),
        ("random-thought-7", "Random Thought 7", "No wikilinks in this note."),
        ("random-thought-8", "Random Thought 8", "Another orphan note for testing."),
        ("random-thought-9", "Random Thought 9", "Disconnected from the main graph."),
        ("random-thought-10", "Random Thought 10", "Final orphan note for testing."),
    ]

    for note_id, title, content in orphan_note_data:
        all_notes.append((note_id, content, title))
        neo4j_adapter.create_note(note_id, content, title)
        notes_created += 1
    print(f"✅ Created {len(orphan_note_data)} orphan notes")

    print(f"\n🎉 Successfully created {notes_created} notes!")

    # Pass 2: Create all links (now that all notes exist)
    print("\n📎 Creating links between notes...")
    links_created = 0
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
    print("  - 10 orphan notes (0 links)")
    print("  - Total: ~308 bidirectional links")

    # Verify by querying count
    with neo4j_adapter.driver.session() as session:
        result = session.run("MATCH (n:Note) RETURN count(n) as count")
        count = result.single()["count"]
        print(f"\n✅ Verified: {count} notes in database")

        # Count links
        link_result = session.run("MATCH ()-[r:LINKS_TO]->() RETURN count(r) as count")
        link_count = link_result.single()["count"]
        print(f"✅ Verified: {link_count} links in database")


if __name__ == "__main__":
    seed_notes()
