"""Generate a realistic Zettelkasten test corpus for local development.

Creates ~75-80 notes with proper atomic structure and interconnections:
- Entry point notes (broad concepts)
- Hub notes (well-connected)
- Regular notes (2-3 links)
- Orphans (for testing)
- Mix of fully developed, stubs, questions, and definitions

Usage:
    docker compose exec backend python scripts/generate_zettelkasten_corpus.py
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.neo4j import get_neo4j_adapter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Adjective-noun pairs for note IDs (pre-generated for consistency)
NOTE_IDS = [
    "curious-mountain", "brave-river", "silent-forest", "quick-thunder",
    "gentle-breeze", "wise-ocean", "bold-sunrise", "calm-meadow",
    "bright-star", "deep-valley", "swift-wind", "ancient-tree",
    "golden-sunset", "quiet-lake", "strong-eagle", "peaceful-garden",
    "wild-storm", "clear-spring", "noble-phoenix", "steady-rock",
    "pure-crystal", "warm-fire", "cool-shadow", "vast-horizon",
    "sharp-blade", "soft-cloud", "dark-void", "light-beam",
    "fierce-lion", "graceful-swan", "mighty-oak", "tender-rose",
    "rapid-stream", "still-pond", "high-peak", "low-tide",
    "fresh-dawn", "old-wisdom", "new-insight", "long-journey",
    "short-burst", "wide-plain", "narrow-path", "deep-thought",
    "shallow-pool", "rough-terrain", "smooth-flow", "hard-lesson",
    "soft-touch", "loud-echo", "quiet-whisper", "true-north",
    "false-start", "real-impact", "ideal-state", "actual-result",
    "future-vision", "past-experience", "present-moment", "constant-change",
    "rare-gem", "common-pattern", "unique-approach", "standard-practice",
    "complex-system", "simple-rule", "clear-signal", "mixed-message",
    "strong-signal", "weak-link", "firm-foundation", "shaky-ground",
    "solid-base", "fluid-motion", "fixed-point", "moving-target",
    "stable-core", "volatile-edge", "certain-fact", "uncertain-future"
]


# Note content templates organized by category
NOTES = {
    # ENTRY POINTS (5 notes) - Broad concepts, 8-12 links each
    "entry_points": [
        {
            "id": "curious-mountain",
            "title": "Engineering Management - Core Responsibilities",
            "content": """Engineering management spans multiple disciplines requiring both technical depth and leadership breadth.

**Core Areas:**
- [[brave-river]] People Management - hiring, growth, retention
- [[silent-forest]] Technical Strategy - architecture, technical debt, platform evolution
- [[quick-thunder]] Delivery - sprint planning, velocity, release management
- [[gentle-breeze]] Communication - stakeholder management, transparency
- [[wise-ocean]] Culture - psychological safety, feedback loops

**Key Practices:**
- [[golden-sunset]] Regular 1-on-1s with direct reports
- [[clear-spring]] Skip-level meetings to surface hidden issues
- [[steady-rock]] Incident management and postmortems
- [[vast-horizon]] Career development and growth planning

**Common Pitfalls:**
- Becoming a bottleneck instead of multiplier
- Losing touch with technical reality
- Over-optimizing for short-term metrics

The best engineering managers balance [[swift-wind]] tactical execution with [[ancient-tree]] strategic thinking.""",
            "tags": ["engineering-management", "leadership", "meta"],
            "links": ["brave-river", "silent-forest", "quick-thunder", "gentle-breeze",
                     "wise-ocean", "golden-sunset", "clear-spring", "steady-rock",
                     "vast-horizon", "swift-wind", "ancient-tree"]
        },
        {
            "id": "brave-river",
            "title": "Site Reliability Engineering - Principles",
            "content": """SRE bridges software engineering and operations through engineering discipline applied to infrastructure and operations problems.

**Core Principles:**
- [[calm-meadow]] Service Level Objectives (SLOs) define acceptable service levels
- [[bright-star]] Error Budgets allow calculated risk-taking
- [[deep-valley]] Toil Reduction through automation
- [[noble-phoenix]] Incident Response with blameless postmortems
- [[warm-fire]] Capacity Planning for sustainable growth

**Golden Signals** ([[cool-shadow]]):
- Latency, Traffic, Errors, Saturation

**Key Practices:**
- [[sharp-blade]] On-call rotations with clear escalation
- [[vast-horizon]] Runbooks for common incidents
- [[steady-rock]] Chaos engineering to validate resilience
- [[pure-crystal]] Observability: metrics, logs, traces

SRE is about [[real-impact]] sustainable operations, not heroics.""",
            "tags": ["sre", "operations", "meta"],
            "links": ["calm-meadow", "bright-star", "deep-valley", "noble-phoenix",
                     "warm-fire", "cool-shadow", "sharp-blade", "vast-horizon",
                     "steady-rock", "pure-crystal", "real-impact"]
        },
        {
            "id": "silent-forest",
            "title": "Knowledge Management - Building a Second Brain",
            "content": """Effective knowledge management transforms information consumption into knowledge creation.

**Core Methods:**
- [[ancient-tree]] Zettelkasten: atomic notes with bidirectional links
- [[quiet-lake]] Progressive Summarization: layer information by importance
- [[peaceful-garden]] PARA: Projects, Areas, Resources, Archives
- [[wild-storm]] Evergreen Notes: permanent, concept-oriented

**Key Principles:**
- [[new-insight]] Atomic notes capture single ideas
- [[deep-thought]] Links create emergence through connections
- [[true-north]] Personal voice over copying
- [[long-journey]] Regular review and refinement

**Common Mistakes:**
- Collecting without connecting ([[false-start]])
- Over-organizing prematurely
- Copying instead of synthesizing

The goal is [[future-vision]] compound knowledge growth, not information hoarding.""",
            "tags": ["knowledge-management", "pkm", "meta"],
            "links": ["ancient-tree", "quiet-lake", "peaceful-garden", "wild-storm",
                     "new-insight", "deep-thought", "true-north", "long-journey",
                     "false-start", "future-vision"]
        },
        {
            "id": "quick-thunder",
            "title": "Software Development - Core Practices",
            "content": """Modern software development requires balancing speed with sustainability.

**Development Practices:**
- [[smooth-flow]] Continuous Integration/Deployment
- [[hard-lesson]] Test-Driven Development (TDD)
- [[common-pattern]] Code Review for knowledge sharing
- [[simple-rule]] Refactoring to manage complexity
- [[clear-signal]] Pair Programming for knowledge transfer

**Architecture Patterns:**
- [[complex-system]] Microservices vs monoliths
- [[firm-foundation]] Event-driven architecture
- [[solid-base]] API-first design
- [[stable-core]] Database per service

**Quality Gates:**
- [[strong-signal]] Automated testing (unit, integration, e2e)
- [[rare-gem]] Static analysis and linting
- [[certain-fact]] Security scanning

The best teams treat [[standard-practice]] technical excellence as enabler of [[moving-target]] business agility.""",
            "tags": ["software-development", "engineering", "meta"],
            "links": ["smooth-flow", "hard-lesson", "common-pattern", "simple-rule",
                     "clear-signal", "complex-system", "firm-foundation", "solid-base",
                     "stable-core", "strong-signal", "rare-gem", "certain-fact",
                     "standard-practice", "moving-target"]
        },
        {
            "id": "gentle-breeze",
            "title": "AI & Machine Learning - Applied Patterns",
            "content": """AI/ML in production requires engineering discipline beyond model training.

**Architecture Patterns:**
- [[light-beam]] Model serving: batch vs real-time
- [[dark-void]] Feature stores for consistency
- [[mighty-oak]] MLOps: deployment, monitoring, retraining
- [[tender-rose]] A/B testing for model validation

**Common Challenges:**
- [[rough-terrain]] Training-serving skew
- [[shallow-pool]] Concept drift over time
- [[mixed-message]] Data quality issues
- [[weak-link]] Model explainability

**Best Practices:**
- [[fluid-motion]] Gradual rollouts with monitoring
- [[fixed-point]] Versioning for reproducibility
- [[volatile-edge]] Continuous monitoring of model performance
- [[uncertain-future]] Fallback strategies for model failures

Success requires treating models as [[constant-change]] living systems, not static artifacts.""",
            "tags": ["ai", "ml", "engineering", "meta"],
            "links": ["light-beam", "dark-void", "mighty-oak", "tender-rose",
                     "rough-terrain", "shallow-pool", "mixed-message", "weak-link",
                     "fluid-motion", "fixed-point", "volatile-edge", "uncertain-future",
                     "constant-change"]
        }
    ],

    # HUB NOTES (8 notes) - Well-connected concepts, 5-8 links each
    "hubs": [
        {
            "id": "wise-ocean",
            "title": "Psychological Safety in Engineering Teams",
            "content": """Psychological safety is the foundation for high-performing teams.

**Definition:**
A shared belief that the team is safe for interpersonal risk-taking. Team members feel comfortable being vulnerable with each other.

**Why It Matters:**
- Enables [[golden-sunset]] candid 1-on-1 discussions
- Drives [[steady-rock]] effective incident response
- Supports [[hard-lesson]] productive code reviews
- Facilitates [[clear-signal]] honest feedback

**Building Safety:**
1. [[gentle-breeze]] Lead with vulnerability yourself
2. [[true-north]] Respond positively to bad news
3. [[peaceful-garden]] Create space for dissent
4. [[noble-phoenix]] Conduct blameless postmortems

**Measurement:**
Ask: "If you make a mistake, is it held against you?"

See [[curious-mountain]] for broader management context.""",
            "tags": ["management", "culture", "teamwork"],
            "links": ["curious-mountain", "golden-sunset", "steady-rock", "hard-lesson",
                     "clear-signal", "gentle-breeze", "true-north", "peaceful-garden",
                     "noble-phoenix"]
        },
        {
            "id": "ancient-tree",
            "title": "Technical Debt - When to Pay It Down",
            "content": """Technical debt isn't inherently bad - it's a tool for managing trade-offs.

**Types of Debt:**
- Deliberate: conscious decisions to move fast
- Accidental: lack of knowledge or experience
- [[rough-terrain]] Environmental: external changes invalidate decisions

**When to Address:**
- [[deep-valley]] Velocity declining >20% over 3 months
- [[weak-link]] Incidents traced to debt >3x in 6 months
- [[shallow-pool]] New features blocked by architecture

**Strategies:**
- [[swift-wind]] Boy Scout Rule: leave code better
- [[smooth-flow]] Dedicate 20% time to refactoring
- [[real-impact]] Link cleanup to business value

**Measurement:**
Track [[strong-signal]] deployment frequency and [[certain-fact]] lead time as proxies for debt impact.

Part of [[curious-mountain]] engineering management.""",
            "tags": ["technical-debt", "engineering", "management"],
            "links": ["curious-mountain", "rough-terrain", "deep-valley", "weak-link",
                     "shallow-pool", "swift-wind", "smooth-flow", "real-impact",
                     "strong-signal", "certain-fact"]
        },
        {
            "id": "golden-sunset",
            "title": "Effective 1-on-1s - Structure and Purpose",
            "content": """1-on-1s are your most valuable management tool when done well.

**Structure:**
- [[long-journey]] Career growth and aspirations (monthly)
- [[new-insight]] Current project feedback (weekly)
- [[deep-thought]] Team dynamics and concerns (as needed)
- Personal connection (always)

**Anti-Patterns:**
- Using as status updates (waste of time)
- Manager talking >50% (should be 20-30%)
- Skipping regularly (destroys trust)

**Key Questions:**
- "What's going well that we should do more of?"
- "What's frustrating you?"
- "What would you like to learn?"
- "How can I help?"

Builds [[wise-ocean]] psychological safety. Part of [[curious-mountain]] management practice.""",
            "tags": ["one-on-ones", "management", "leadership"],
            "links": ["curious-mountain", "wise-ocean", "long-journey", "new-insight",
                     "deep-thought"]
        },
        {
            "id": "calm-meadow",
            "title": "Service Level Objectives (SLOs)",
            "content": """SLOs quantify reliability targets, enabling data-driven decisions about risk.

**Components:**
- SLI (Indicator): measurement (e.g., request latency)
- SLO (Objective): target (e.g., 99.9% of requests <100ms)
- SLA (Agreement): business consequences if missed

**Setting SLOs:**
1. Start with [[real-impact]] user-visible metrics
2. [[certain-fact]] Measure current performance
3. Set targets just below current (leave headroom)
4. [[bright-star]] Calculate error budget

**Using Error Budgets:**
- Budget remaining → [[smooth-flow]] take risks, move fast
- Budget exhausted → [[firm-foundation]] focus on reliability

**Common Mistakes:**
- Setting SLOs too aggressive (no room for change)
- [[false-start]] Measuring what's easy vs meaningful
- Not using error budgets to make decisions

Core of [[brave-river]] SRE practice.""",
            "tags": ["sre", "operations", "reliability"],
            "links": ["brave-river", "real-impact", "certain-fact", "bright-star",
                     "smooth-flow", "firm-foundation", "false-start"]
        },
        {
            "id": "peaceful-garden",
            "title": "PARA Method - Organizing Digital Information",
            "content": """PARA organizes information by actionability, not topic.

**Structure:**
1. **Projects**: Active work with deadline
   - Sprint work, launches, initiatives
   - Archive when complete

2. **Areas**: Ongoing responsibilities
   - [[curious-mountain]] Team management
   - [[brave-river]] Production operations
   - Personal development

3. **Resources**: Topics of interest
   - [[silent-forest]] Knowledge management techniques
   - [[quick-thunder]] Software patterns
   - Industry research

4. **Archives**: Completed projects

**Benefits:**
- [[swift-wind]] Reduces decision fatigue
- [[clear-signal]] Clear action hierarchy
- [[simple-rule]] Easy maintenance

Complements [[ancient-tree]] Zettelkasten for [[new-insight]] knowledge building.""",
            "tags": ["knowledge-management", "pkm", "productivity"],
            "links": ["silent-forest", "curious-mountain", "brave-river", "quick-thunder",
                     "ancient-tree", "swift-wind", "clear-signal", "simple-rule", "new-insight"]
        },
        {
            "id": "steady-rock",
            "title": "Incident Management - Process and Practice",
            "content": """Effective incident response minimizes impact and maximizes learning.

**Roles:**
- Incident Commander: coordinates response
- Communications: updates stakeholders
- Subject Matter Experts: investigate and fix

**Process:**
1. [[clear-signal]] Detect and declare
2. [[swift-wind]] Assess severity and impact
3. [[smooth-flow]] Mitigate (not fix)
4. [[real-impact]] Resolve root cause
5. [[noble-phoenix]] Postmortem and improve

**Blameless Postmortems:**
- Focus on [[complex-system]] systems, not individuals
- [[new-insight]] Document what we learned
- [[hard-lesson]] Define action items with owners
- [[wise-ocean]] Build psychological safety

**Anti-Patterns:**
- Hero culture (unsustainable)
- Blaming individuals (destroys trust)
- Skipping postmortems (miss learning)

Part of [[brave-river]] SRE practice and [[curious-mountain]] leadership.""",
            "tags": ["sre", "operations", "incident-management"],
            "links": ["brave-river", "curious-mountain", "clear-signal", "swift-wind",
                     "smooth-flow", "real-impact", "noble-phoenix", "complex-system",
                     "new-insight", "hard-lesson", "wise-ocean"]
        },
        {
            "id": "hard-lesson",
            "title": "Code Review - Knowledge Transfer Tool",
            "content": """Code review is primarily about knowledge sharing, secondarily about quality.

**Goals:**
1. [[new-insight]] Spread knowledge across team
2. [[common-pattern]] Establish conventions
3. Catch bugs (least important!)

**Best Practices:**
- [[swift-wind]] Review within 24 hours
- [[simple-rule]] Keep PRs small (<400 lines)
- [[clear-signal]] Explain "why", not just "what"
- Ask questions, don't command

**What to Review:**
- [[certain-fact]] Tests cover edge cases
- [[firm-foundation]] Architecture patterns consistent
- [[smooth-flow]] Code is readable

**Building Safety:**
- [[wise-ocean]] Praise good solutions publicly
- [[true-north]] Nitpicks marked as optional
- Focus on learning, not gatekeeping

Part of [[quick-thunder]] development practices.""",
            "tags": ["software-development", "code-review", "teamwork"],
            "links": ["quick-thunder", "new-insight", "common-pattern", "swift-wind",
                     "simple-rule", "clear-signal", "certain-fact", "firm-foundation",
                     "smooth-flow", "wise-ocean", "true-north"]
        },
        {
            "id": "smooth-flow",
            "title": "Continuous Deployment - Shipping Small Changes Frequently",
            "content": """Continuous deployment reduces risk by shipping small, reversible changes.

**Benefits:**
- [[swift-wind]] Faster feedback on changes
- [[real-impact]] Smaller blast radius for failures
- [[firm-foundation]] Forces investment in automation
- [[certain-fact]] Reduces fear of deploying

**Requirements:**
- [[strong-signal]] Comprehensive automated testing
- [[clear-signal]] Feature flags for gradual rollouts
- [[calm-meadow]] Good observability and alerting
- [[steady-rock]] Incident response process

**Cultural Shift:**
- From "deploy is scary" to [[moving-target]] "deploy is routine"
- From manual gates to [[standard-practice]] automated checks
- [[simple-rule]] Trunk-based development over long branches

**Measurement:**
Deploy [[certain-fact]] frequency and [[real-impact]] lead time show team health.

Core of [[quick-thunder]] modern software development.""",
            "tags": ["software-development", "ci-cd", "devops"],
            "links": ["quick-thunder", "swift-wind", "real-impact", "firm-foundation",
                     "certain-fact", "strong-signal", "clear-signal", "calm-meadow",
                     "steady-rock", "moving-target", "standard-practice", "simple-rule"]
        }
    ],

    # REGULAR NOTES (40 notes) - Atomic concepts, 2-3 links each
    "regular": [
        {
            "id": "bright-star",
            "title": "Error Budgets - Risk Management Tool",
            "content": """Error budget = (1 - SLO) × time period

Example: 99.9% SLO = 0.1% error budget = 43 minutes/month

**Usage:**
- Budget available → [[smooth-flow]] ship features, take risks
- Budget consumed → [[firm-foundation]] freeze, focus on reliability

Makes [[calm-meadow]] SLO targets actionable for teams.""",
            "tags": ["sre", "operations"],
            "links": ["calm-meadow", "smooth-flow", "firm-foundation"]
        },
        {
            "id": "deep-valley",
            "title": "Toil - Work to Eliminate",
            "content": """Toil is manual, repetitive, automatable work without enduring value.

**Characteristics:**
- Manual: requires human action
- Repetitive: done over and over
- Automatable: could be scripted
- No enduring value: doesn't improve system

**Goal:** <50% of SRE time on toil.

**Strategy:** [[swift-wind]] Automate most common tasks first.

Part of [[brave-river]] SRE principles.""",
            "tags": ["sre", "operations", "automation"],
            "links": ["brave-river", "swift-wind"]
        },
        {
            "id": "noble-phoenix",
            "title": "Blameless Postmortems",
            "content": """Postmortems should focus on systems and processes, not individuals.

**Key Questions:**
- What happened?
- Why did it happen?
- How do we prevent recurrence?

**Action Items:**
Must have owners and deadlines. Track completion.

**Culture:**
Builds [[wise-ocean]] psychological safety. Incidents are [[new-insight]] learning opportunities.

See [[steady-rock]] for full incident process.""",
            "tags": ["sre", "incident-management", "culture"],
            "links": ["steady-rock", "wise-ocean", "new-insight"]
        },
        {
            "id": "warm-fire",
            "title": "Capacity Planning - Staying Ahead of Growth",
            "content": """Capacity planning prevents outages from resource exhaustion.

**Approach:**
1. [[certain-fact]] Measure current usage and growth rate
2. Project when resources hit 80% (danger zone)
3. Order capacity 3-6 months ahead

**Common Mistakes:**
- Planning based on averages (miss spikes)
- [[false-start]] Waiting until 90% utilized

Part of [[brave-river]] SRE practice.""",
            "tags": ["sre", "operations", "capacity-planning"],
            "links": ["brave-river", "certain-fact", "false-start"]
        },
        {
            "id": "cool-shadow",
            "title": "Four Golden Signals - SRE Monitoring",
            "content": """Monitor these four metrics to understand system health:

1. **Latency**: Response time
2. **Traffic**: Request volume
3. **Errors**: Failed request rate
4. **Saturation**: Resource utilization

If you can only monitor 4 things, monitor these.

Foundation of [[brave-river]] SRE observability.""",
            "tags": ["sre", "monitoring", "observability"],
            "links": ["brave-river"]
        },
        {
            "id": "sharp-blade",
            "title": "On-Call Rotation - Sustainable Practice",
            "content": """On-call should be sustainable, not heroic.

**Best Practices:**
- Rotate responsibility (avoid burnout)
- [[steady-rock]] Clear escalation paths
- Compensate appropriately
- [[calm-meadow]] Alert on SLO violations, not everything

**Signs of Dysfunction:**
- Pager fatigue (too many alerts)
- Hero culture
- No [[deep-valley]] toil reduction effort

Part of [[brave-river]] SRE.""",
            "tags": ["sre", "operations", "on-call"],
            "links": ["brave-river", "steady-rock", "calm-meadow", "deep-valley"]
        },
        {
            "id": "vast-horizon",
            "title": "Career Development - Manager's Role",
            "content": """Managers should actively guide career growth.

**Regular Activities:**
- [[golden-sunset]] Discuss career goals in 1-on-1s
- Create stretch opportunities
- Provide candid feedback
- Connect to sponsors/mentors

**Growth Areas:**
- Technical depth
- Scope/impact
- [[wise-ocean]] Leadership skills

Part of [[curious-mountain]] engineering management.""",
            "tags": ["management", "career-development", "leadership"],
            "links": ["curious-mountain", "golden-sunset", "wise-ocean"]
        },
        {
            "id": "swift-wind",
            "title": "Boy Scout Rule - Leave Code Better",
            "content": """Always leave code a little better than you found it.

**Application:**
- Fix small issues as you see them
- Don't need permission for tiny improvements
- Reduces [[ancient-tree]] technical debt gradually

Part of [[quick-thunder]] development culture.""",
            "tags": ["software-development", "best-practices"],
            "links": ["quick-thunder", "ancient-tree"]
        },
        {
            "id": "pure-crystal",
            "title": "Observability - Metrics, Logs, Traces",
            "content": """Observability is the ability to understand system state from external outputs.

**Three Pillars:**
1. **Metrics**: Aggregated numbers ([[cool-shadow]] Golden Signals)
2. **Logs**: Event records
3. **Traces**: Request paths through system

**Goal:** Debug unknown-unknowns, not just known failures.

Core of [[brave-river]] SRE.""",
            "tags": ["sre", "observability", "monitoring"],
            "links": ["brave-river", "cool-shadow"]
        },
        {
            "id": "real-impact",
            "title": "User Impact - The North Star Metric",
            "content": """Always tie technical work to user impact.

**Questions:**
- How many users affected?
- How severe is degradation?
- What's the business cost?

**Application:**
- [[calm-meadow]] SLOs based on user experience
- [[steady-rock]] Incident severity by user impact
- [[ancient-tree]] Prioritize debt that hurts users

Keeps engineering [[true-north]] user-focused.""",
            "tags": ["product", "metrics", "user-experience"],
            "links": ["calm-meadow", "steady-rock", "ancient-tree", "true-north"]
        },
        {
            "id": "new-insight",
            "title": "Zettelkasten - Atomic Notes",
            "content": """Each note should capture ONE idea in your own words.

**Why Atomic:**
- Easier to link precisely
- Reusable in multiple contexts
- Forces clear thinking

**Anti-Pattern:**
Copying text without synthesis ([[false-start]]).

**Links Create Value:**
Individual notes have [[deep-thought]] minimal value. Connections create [[future-vision]] emergence.

Core of [[silent-forest]] knowledge management.""",
            "tags": ["zettelkasten", "pkm", "note-taking"],
            "links": ["silent-forest", "false-start", "deep-thought", "future-vision"]
        },
        {
            "id": "deep-thought",
            "title": "Links in Zettelkasten - Creating Emergence",
            "content": """The value of a Zettelkasten emerges from connections, not individual notes.

**Types of Links:**
- Sequence: This builds on that
- Contrast: This opposes that
- Example: This illustrates that

**Best Practice:**
Add [[new-insight]] context when linking - WHY are these connected?

Part of [[silent-forest]] knowledge management.""",
            "tags": ["zettelkasten", "pkm", "connections"],
            "links": ["silent-forest", "new-insight"]
        },
        {
            "id": "true-north",
            "title": "Write in Your Own Voice",
            "content": """Zettelkasten should be your thinking, not copied content.

**Why:**
- Forces understanding
- Creates [[new-insight]] unique connections
- More memorable

**How:**
1. Read source
2. Close it
3. Write what you understood

Avoids [[false-start]] collecting without processing.

Part of [[silent-forest]] knowledge management.""",
            "tags": ["zettelkasten", "pkm", "writing"],
            "links": ["silent-forest", "new-insight", "false-start"]
        },
        {
            "id": "long-journey",
            "title": "Progressive Summarization - Layered Highlighting",
            "content": """Progressively bold and highlight the most important points over multiple passes.

**Layers:**
1. Original text
2. Bold the important parts
3. Highlight the key sentences
4. Write a summary at top

**Benefit:**
Future you quickly finds [[new-insight]] key ideas without re-reading everything.

Complements [[silent-forest]] note-taking.""",
            "tags": ["pkm", "productivity", "reading"],
            "links": ["silent-forest", "new-insight"]
        },
        {
            "id": "false-start",
            "title": "Collector's Fallacy",
            "content": """Collecting information ≠ learning.

**The Trap:**
Saving articles, bookmarking, highlighting - feels productive but isn't.

**The Fix:**
[[true-north]] Process into your own words. Create [[new-insight]] connections.

Part of [[silent-forest]] knowledge management pitfalls.""",
            "tags": ["pkm", "productivity", "anti-pattern"],
            "links": ["silent-forest", "true-north", "new-insight"]
        },
        {
            "id": "future-vision",
            "title": "Compound Knowledge Growth",
            "content": """Well-maintained Zettelkasten creates compound returns on learning.

**Mechanism:**
- Each [[new-insight]] new note connects to existing notes
- Connections reveal [[deep-thought]] patterns
- Patterns generate insights

**Timeline:**
Value appears after ~100-200 notes, 6+ months.

Goal of [[silent-forest]] knowledge management.""",
            "tags": ["zettelkasten", "pkm", "learning"],
            "links": ["silent-forest", "new-insight", "deep-thought"]
        },
        {
            "id": "common-pattern",
            "title": "Design Patterns - Shared Vocabulary",
            "content": """Design patterns provide shared language for discussing solutions.

**Benefits:**
- [[clear-signal]] Communicate intent quickly
- [[hard-lesson]] Codify best practices
- Avoid reinventing wheels

**Caution:**
Don't force patterns. [[simple-rule]] Solve the problem first.

Part of [[quick-thunder]] software development.""",
            "tags": ["software-development", "design-patterns"],
            "links": ["quick-thunder", "clear-signal", "hard-lesson", "simple-rule"]
        },
        {
            "id": "simple-rule",
            "title": "YAGNI - You Aren't Gonna Need It",
            "content": """Don't add functionality until you need it.

**Why:**
- [[ancient-tree]] Creates debt for unused features
- Increases complexity
- Takes time from real needs

**Application:**
Build for [[present-moment]] today's requirements, not [[uncertain-future]] imagined future.

Part of [[quick-thunder]] development principles.""",
            "tags": ["software-development", "best-practices"],
            "links": ["quick-thunder", "ancient-tree", "present-moment", "uncertain-future"]
        },
        {
            "id": "clear-signal",
            "title": "Naming - Most Important Design Decision",
            "content": """Good names make code self-documenting.

**Principles:**
- Reveal intent
- Avoid misleading
- Be consistent with [[common-pattern]] domain language

**Cost:**
Rename aggressively. Bad names compound [[ancient-tree]] technical debt.

Part of [[quick-thunder]] code quality.""",
            "tags": ["software-development", "code-quality"],
            "links": ["quick-thunder", "common-pattern", "ancient-tree"]
        },
        {
            "id": "complex-system",
            "title": "Microservices vs Monolith - Trade-offs",
            "content": """Neither architecture is inherently better - each has trade-offs.

**Monolith Benefits:**
- [[simple-rule]] Simpler to develop and deploy
- Easier to maintain consistency
- Lower operational overhead

**Microservices Benefits:**
- Independent scaling and deployment
- [[firm-foundation]] Technology flexibility per service
- Team autonomy

**Rule:** Start with monolith, split only when [[real-impact]] pain justifies complexity.

Part of [[quick-thunder]] architecture decisions.""",
            "tags": ["software-development", "architecture", "microservices"],
            "links": ["quick-thunder", "simple-rule", "firm-foundation", "real-impact"]
        },
        {
            "id": "firm-foundation",
            "title": "API Design - Contract-First",
            "content": """Design APIs before implementation.

**Benefits:**
- [[clear-signal]] Clear interface contracts
- Enables parallel development
- Forces thinking about [[real-impact]] user needs

**Best Practices:**
- Use OpenAPI/Swagger specs
- Version from day one
- [[common-pattern]] Follow REST or GraphQL conventions

Part of [[quick-thunder]] software development.""",
            "tags": ["software-development", "api-design"],
            "links": ["quick-thunder", "clear-signal", "real-impact", "common-pattern"]
        },
        {
            "id": "solid-base",
            "title": "Database Per Service - Microservices Pattern",
            "content": """Each microservice should own its database.

**Rationale:**
- Service autonomy
- [[firm-foundation]] Independent scaling
- Schema evolution without coordination

**Challenges:**
- Cross-service queries harder
- Data consistency across services
- [[complex-system]] Increased operational complexity

Part of [[quick-thunder]] microservices architecture.""",
            "tags": ["software-development", "microservices", "database"],
            "links": ["quick-thunder", "firm-foundation", "complex-system"]
        },
        {
            "id": "stable-core",
            "title": "Event-Driven Architecture - Loose Coupling",
            "content": """Services communicate via events, not direct calls.

**Benefits:**
- [[firm-foundation]] Loose coupling between services
- Natural audit log
- Easy to add consumers

**Trade-offs:**
- [[complex-system]] Harder to debug flows
- Eventual consistency

Part of [[quick-thunder]] architecture patterns.""",
            "tags": ["software-development", "architecture", "events"],
            "links": ["quick-thunder", "firm-foundation", "complex-system"]
        },
        {
            "id": "strong-signal",
            "title": "Test Pyramid - Balance Test Types",
            "content": """Balance fast unit tests with fewer slow integration tests.

**Ratio:**
- 70% unit tests
- 20% integration tests
- 10% e2e tests

**Rationale:**
Unit tests are [[swift-wind]] fast, reliable. E2e tests are [[deep-valley]] slow, flaky.

Enables [[smooth-flow]] continuous deployment.

Part of [[quick-thunder]] testing strategy.""",
            "tags": ["software-development", "testing", "quality"],
            "links": ["quick-thunder", "swift-wind", "deep-valley", "smooth-flow"]
        },
        {
            "id": "rare-gem",
            "title": "Static Analysis - Catch Issues Early",
            "content": """Automated tools catch bugs before code review.

**Tools:**
- Linters (style)
- Type checkers
- Security scanners

**Benefit:**
[[hard-lesson]] Reviews focus on design, not syntax.

Part of [[quick-thunder]] development workflow.""",
            "tags": ["software-development", "tools", "quality"],
            "links": ["quick-thunder", "hard-lesson"]
        },
        {
            "id": "certain-fact",
            "title": "DORA Metrics - Measuring DevOps Performance",
            "content": """Four key metrics predict software delivery performance:

1. **Deployment Frequency**: How often you ship
2. **Lead Time**: Commit to production time
3. **Change Failure Rate**: % deployments causing incidents
4. **Time to Restore**: Incident recovery time

Elite teams: Deploy multiple times/day, <1 hour lead time.

Validates [[smooth-flow]] continuous deployment practices.""",
            "tags": ["metrics", "devops", "performance"],
            "links": ["smooth-flow"]
        },
        {
            "id": "standard-practice",
            "title": "Trunk-Based Development",
            "content": """All developers commit to main/trunk daily.

**Requires:**
- [[strong-signal]] Comprehensive automated tests
- [[clear-signal]] Feature flags for incomplete work

**Benefits:**
- [[smooth-flow]] Faster integration
- Reduces merge conflicts
- [[swift-wind]] Accelerates feedback

Part of [[quick-thunder]] development workflow.""",
            "tags": ["software-development", "git", "workflow"],
            "links": ["quick-thunder", "strong-signal", "clear-signal", "smooth-flow", "swift-wind"]
        },
        {
            "id": "moving-target",
            "title": "Feature Flags - Decouple Deploy from Release",
            "content": """Deploy code disabled, enable via config.

**Use Cases:**
- [[smooth-flow]] Gradual rollouts (1% → 10% → 100%)
- A/B testing
- Kill switches for bad features

**Requires:**
- Feature flag management system
- [[certain-fact]] Metrics to validate rollout

Enables [[smooth-flow]] continuous deployment.

Part of [[quick-thunder]] deployment strategy.""",
            "tags": ["software-development", "deployment", "feature-flags"],
            "links": ["quick-thunder", "smooth-flow", "certain-fact"]
        },
        {
            "id": "light-beam",
            "title": "Model Serving - Batch vs Real-Time",
            "content": """ML models can be served in two modes:

**Batch:**
- Pre-compute predictions
- Store in database
- Serve lookups

**Real-Time:**
- Compute on request
- Lower latency possible with [[firm-foundation]] careful optimization

**Trade-off:**
Batch simpler, real-time more flexible.

Part of [[gentle-breeze]] ML engineering.""",
            "tags": ["ml", "architecture", "inference"],
            "links": ["gentle-breeze", "firm-foundation"]
        },
        {
            "id": "dark-void",
            "title": "Feature Stores - Consistent ML Features",
            "content": """Centralized store for ML features ensures training-serving consistency.

**Problem Solved:**
Training uses one code, serving uses different code → [[rough-terrain]] training-serving skew.

**Solution:**
Single feature computation logic used both places.

Part of [[gentle-breeze]] ML architecture.""",
            "tags": ["ml", "mlops", "features"],
            "links": ["gentle-breeze", "rough-terrain"]
        },
        {
            "id": "mighty-oak",
            "title": "MLOps - Model Lifecycle Management",
            "content": """Models require [[constant-change]] continuous operations like services.

**Lifecycle:**
1. Training → 2. Validation → 3. Deployment → 4. [[volatile-edge]] Monitoring → 5. Retraining

**Key Practices:**
- [[fixed-point]] Version everything (code, data, models)
- [[fluid-motion]] Gradual rollouts
- [[certain-fact]] Monitor performance metrics

Part of [[gentle-breeze]] ML engineering.""",
            "tags": ["ml", "mlops", "operations"],
            "links": ["gentle-breeze", "constant-change", "volatile-edge", "fixed-point",
                     "fluid-motion", "certain-fact"]
        },
        {
            "id": "tender-rose",
            "title": "A/B Testing for ML Models",
            "content": """Compare model versions with controlled experiments.

**Setup:**
- Route 50% traffic to model A, 50% to model B
- [[certain-fact]] Measure business metrics (not just accuracy)
- Statistical significance before declaring winner

**Common Mistake:**
Optimizing for [[mixed-message]] proxy metrics that don't reflect [[real-impact]] user value.

Part of [[gentle-breeze]] model validation.""",
            "tags": ["ml", "experimentation", "testing"],
            "links": ["gentle-breeze", "certain-fact", "mixed-message", "real-impact"]
        },
        {
            "id": "rough-terrain",
            "title": "Training-Serving Skew - ML Bug Source",
            "content": """Features computed differently in training vs serving causes silent failures.

**Example:**
Training uses SQL, serving uses Python → different results.

**Prevention:**
[[dark-void]] Feature stores ensure single computation logic.

Critical issue in [[gentle-breeze]] ML systems.""",
            "tags": ["ml", "mlops", "debugging"],
            "links": ["gentle-breeze", "dark-void"]
        },
        {
            "id": "shallow-pool",
            "title": "Concept Drift - Models Decay Over Time",
            "content": """World changes → model predictions become stale.

**Example:**
COVID changed shopping patterns → pre-COVID recommendation model performs poorly.

**Detection:**
[[volatile-edge]] Monitor model performance over time.

**Solution:**
[[mighty-oak]] Retrain periodically or on-demand.

Part of [[gentle-breeze]] ML operations.""",
            "tags": ["ml", "mlops", "monitoring"],
            "links": ["gentle-breeze", "volatile-edge", "mighty-oak"]
        },
        {
            "id": "mixed-message",
            "title": "Data Quality Issues in ML",
            "content": """Poor data quality silently degrades ML models.

**Common Issues:**
- Missing values
- Outliers
- [[rough-terrain]] Feature computation bugs

**Prevention:**
- Data validation pipelines
- [[certain-fact]] Monitor feature distributions

Critical for [[gentle-breeze]] ML reliability.""",
            "tags": ["ml", "data-quality", "operations"],
            "links": ["gentle-breeze", "rough-terrain", "certain-fact"]
        },
        {
            "id": "weak-link",
            "title": "Model Explainability - Building Trust",
            "content": """Understanding WHY models make predictions builds trust.

**Techniques:**
- Feature importance
- SHAP values
- Example-based explanations

**Trade-off:**
Complex models ([[light-beam]] neural nets) harder to explain than [[simple-rule]] decision trees.

Important for [[gentle-breeze]] ML adoption.""",
            "tags": ["ml", "explainability", "trust"],
            "links": ["gentle-breeze", "light-beam", "simple-rule"]
        },
        {
            "id": "fluid-motion",
            "title": "Gradual ML Model Rollouts",
            "content": """Roll out new models incrementally to limit blast radius.

**Process:**
1% → 10% → 50% → 100%, [[certain-fact]] monitoring at each step.

**Fallback:**
[[uncertain-future]] Automatic rollback on metric degradation.

Enables [[smooth-flow]] safe deployment.

Part of [[mighty-oak]] MLOps practice.""",
            "tags": ["ml", "deployment", "risk-management"],
            "links": ["mighty-oak", "certain-fact", "uncertain-future", "smooth-flow"]
        },
        {
            "id": "fixed-point",
            "title": "ML Model Versioning",
            "content": """Version models, code, data, and hyperparameters together.

**Why:**
Reproducibility. Must be able to recreate exact model.

**Tools:**
MLflow, W&B, DVC

Part of [[mighty-oak]] MLOps infrastructure.""",
            "tags": ["ml", "mlops", "versioning"],
            "links": ["mighty-oak"]
        },
        {
            "id": "volatile-edge",
            "title": "Model Performance Monitoring",
            "content": """Monitor models in production for [[shallow-pool]] degradation.

**Metrics:**
- Prediction distribution (drift?)
- Business metrics ([[real-impact]] conversions, revenue)
- [[certain-fact]] Latency and errors

**Alert:**
Automatic retraining when performance drops.

Part of [[mighty-oak]] MLOps.""",
            "tags": ["ml", "monitoring", "operations"],
            "links": ["mighty-oak", "shallow-pool", "real-impact", "certain-fact"]
        }
    ],

    # STUB NOTES (15 notes) - Placeholders with TODOs, 1-2 links each
    "stubs": [
        {
            "id": "quiet-lake",
            "title": "Progressive Summarization - Reading Workflow",
            "content": """[TODO: Expand on the 4-layer highlighting system]

Related to [[long-journey]] and [[silent-forest]] knowledge management.

Tiago Forte's method for [[new-insight]] processing reading material.""",
            "tags": ["pkm", "reading", "stub"],
            "links": ["silent-forest", "long-journey", "new-insight"]
        },
        {
            "id": "wild-storm",
            "title": "Evergreen Notes - Permanent Knowledge",
            "content": """[TODO: Define evergreen notes vs fleeting notes]

**Characteristics:**
- Concept-oriented, not source-oriented
- [[new-insight]] Densely linked
- Written in own words

Part of [[silent-forest]] note-taking philosophy.""",
            "tags": ["zettelkasten", "pkm", "stub"],
            "links": ["silent-forest", "new-insight"]
        },
        {
            "id": "present-moment",
            "title": "Build for Today's Requirements",
            "content": """[TODO: Expand on balancing current needs vs future flexibility]

Related to [[simple-rule]] YAGNI principle.

Avoid [[uncertain-future]] over-engineering for imagined future.""",
            "tags": ["software-development", "architecture", "stub"],
            "links": ["simple-rule", "uncertain-future"]
        },
        {
            "id": "uncertain-future",
            "title": "Over-Engineering - Premature Optimization",
            "content": """[TODO: Examples of over-engineering and its costs]

Opposite of [[present-moment]] building for today.

Creates [[ancient-tree]] unnecessary technical debt.""",
            "tags": ["software-development", "anti-pattern", "stub"],
            "links": ["present-moment", "ancient-tree"]
        },
        {
            "id": "constant-change",
            "title": "ML Models as Living Systems",
            "content": """[TODO: Expand on continuous model lifecycle]

Models require [[volatile-edge]] ongoing monitoring and [[mighty-oak]] retraining.

Never "done" like traditional software.

Part of [[gentle-breeze]] ML engineering mindset.""",
            "tags": ["ml", "mlops", "stub"],
            "links": ["gentle-breeze", "volatile-edge", "mighty-oak"]
        },
        {
            "id": "shaky-ground",
            "title": "Technical Debt - Interest Compounds",
            "content": """[TODO: Expand on how debt compounds]

Related to [[ancient-tree]] technical debt management.

Small [[swift-wind]] improvements prevent compounding.""",
            "tags": ["technical-debt", "management", "stub"],
            "links": ["ancient-tree", "swift-wind"]
        },
        {
            "id": "loud-echo",
            "title": "Alert Fatigue - Too Many Alarms",
            "content": """[TODO: Expand on alert fatigue causes and solutions]

Related to [[sharp-blade]] on-call practices.

Should alert on [[calm-meadow]] SLO violations, not everything.""",
            "tags": ["sre", "operations", "stub"],
            "links": ["sharp-blade", "calm-meadow"]
        },
        {
            "id": "quiet-whisper",
            "title": "Feedback Loops - Faster is Better",
            "content": """[TODO: Expand on feedback loop importance]

Related to [[smooth-flow]] continuous deployment.

[[certain-fact]] DORA metrics measure feedback speed.""",
            "tags": ["devops", "metrics", "stub"],
            "links": ["smooth-flow", "certain-fact"]
        },
        {
            "id": "ideal-state",
            "title": "Zero-Bug Policy",
            "content": """[TODO: Expand on zero-bug approaches]

Related to [[hard-lesson]] code review and [[strong-signal]] testing.

Controversial practice in [[quick-thunder]] development.""",
            "tags": ["software-development", "quality", "stub"],
            "links": ["quick-thunder", "hard-lesson", "strong-signal"]
        },
        {
            "id": "actual-result",
            "title": "Metrics Gaming - Goodhart's Law",
            "content": """[TODO: Expand on metric gaming]

"When a measure becomes a target, it ceases to be a good measure."

Relevant to [[certain-fact]] DORA metrics and [[calm-meadow]] SLOs.""",
            "tags": ["metrics", "management", "stub"],
            "links": ["certain-fact", "calm-meadow"]
        },
        {
            "id": "past-experience",
            "title": "Postmortem Database - Learning from History",
            "content": """[TODO: Expand on maintaining incident history]

Related to [[noble-phoenix]] blameless postmortems.

Part of [[steady-rock]] incident management.""",
            "tags": ["sre", "incident-management", "stub"],
            "links": ["noble-phoenix", "steady-rock"]
        },
        {
            "id": "unique-approach",
            "title": "Innovation vs Convention",
            "content": """[TODO: Expand on when to innovate vs follow convention]

Related to [[common-pattern]] design patterns.

Balance [[rare-gem]] innovation with [[standard-practice]] conventions.""",
            "tags": ["software-development", "culture", "stub"],
            "links": ["common-pattern", "rare-gem", "standard-practice"]
        },
        {
            "id": "high-peak",
            "title": "10x Engineers - Myth or Reality?",
            "content": """[TODO: Expand on productivity variance]

Related to [[vast-horizon]] career development.

[[wise-ocean]] Environment and team dynamics matter more than individual skill.""",
            "tags": ["engineering", "career", "stub"],
            "links": ["vast-horizon", "wise-ocean"]
        },
        {
            "id": "low-tide",
            "title": "Technical Writing - Documentation as Code",
            "content": """[TODO: Expand on docs-as-code practices]

Related to [[firm-foundation]] API design.

Part of [[quick-thunder]] development workflow.""",
            "tags": ["documentation", "software-development", "stub"],
            "links": ["firm-foundation", "quick-thunder"]
        },
        {
            "id": "fresh-dawn",
            "title": "Onboarding New Engineers",
            "content": """[TODO: Expand on onboarding best practices]

Related to [[vast-horizon]] career development and [[wise-ocean]] team culture.

First [[golden-sunset]] 1-on-1s are critical.""",
            "tags": ["onboarding", "management", "stub"],
            "links": ["vast-horizon", "wise-ocean", "golden-sunset"]
        }
    ],

    # QUESTION NOTES (10 notes) - Exploring ideas, 1-2 links each
    "questions": [
        {
            "id": "old-wisdom",
            "title": "When Does Technical Debt Become Worth Paying?",
            "content": """**Question:** At what threshold should we stop feature work to address [[ancient-tree]] technical debt?

**Signals to watch:**
- [[certain-fact]] Deploy frequency dropping >20%
- Velocity declining >30% over 2 quarters
- [[weak-link]] Incident rate increasing

**Open question:** Is there a universal threshold, or is it context-dependent?

Need to track [[real-impact]] impact on user experience, not just developer happiness.""",
            "tags": ["technical-debt", "management", "question"],
            "links": ["ancient-tree", "certain-fact", "weak-link", "real-impact"]
        },
        {
            "id": "rapid-stream",
            "title": "Should Every Team Have an SRE Embed?",
            "content": """**Question:** Is embedded SRE model better than centralized SRE team?

**Embedded Pros:**
- Closer to dev team
- Faster response

**Centralized Pros:**
- Deeper [[brave-river]] SRE expertise
- Better [[sharp-blade]] on-call rotation

**Hypothesis:** Depends on team size and maturity.""",
            "tags": ["sre", "organization", "question"],
            "links": ["brave-river", "sharp-blade"]
        },
        {
            "id": "still-pond",
            "title": "Is Zero-Downtime Deployment Worth the Complexity?",
            "content": """**Question:** When is [[smooth-flow]] zero-downtime deployment overhead justified?

**Trade-off:**
More complex deployment vs [[real-impact]] no user impact

**Variables:**
- User base size
- SLO requirements
- Deployment frequency

Most startups over-invest in this early.""",
            "tags": ["deployment", "operations", "question"],
            "links": ["smooth-flow", "real-impact"]
        },
        {
            "id": "narrow-path",
            "title": "Should Managers Code?",
            "content": """**Question:** Should engineering managers maintain technical skills through coding?

**Arguments For:**
- Maintain credibility
- Better technical decisions

**Arguments Against:**
- Takes time from [[curious-mountain]] management work
- Blocks team ownership

**Nuance:** Depends on org size and manager level.""",
            "tags": ["management", "leadership", "question"],
            "links": ["curious-mountain"]
        },
        {
            "id": "wide-plain",
            "title": "How Much Monitoring is Too Much?",
            "content": """**Question:** When does monitoring become [[loud-echo]] noise instead of [[clear-signal]] signal?

**Hypothesis:**
Start with [[cool-shadow]] four golden signals. Add only when debugging reveals gaps.

**Risk:**
Over-monitoring creates [[sharp-blade]] alert fatigue.""",
            "tags": ["monitoring", "sre", "question"],
            "links": ["cool-shadow", "loud-echo", "clear-signal", "sharp-blade"]
        },
        {
            "id": "short-burst",
            "title": "Pair Programming - Worth the Cost?",
            "content": """**Question:** Is pair programming 2x the cost for <2x the benefit?

**Benefits:**
- [[hard-lesson]] Knowledge sharing
- Fewer bugs
- [[wise-ocean]] Builds team cohesion

**Costs:**
- Literally 2 engineers on one task
- Scheduling overhead

**Hypothesis:** Best for complex problems and onboarding, not routine work.""",
            "tags": ["software-development", "practices", "question"],
            "links": ["hard-lesson", "wise-ocean"]
        },
        {
            "id": "rough-edge",
            "title": "When to Split a Monolith?",
            "content": """**Question:** At what point does [[complex-system]] microservices complexity become worth it?

**Signals:**
- Team >15 engineers
- Deploy conflicts
- Different scaling needs

**Caution:**
[[simple-rule]] Don't split prematurely. Distributed systems are hard.""",
            "tags": ["architecture", "microservices", "question"],
            "links": ["complex-system", "simple-rule"]
        },
        {
            "id": "soft-landing",
            "title": "How Much Test Coverage is Enough?",
            "content": """**Question:** Is 80% coverage sufficient, or should we aim for 100%?

**Diminishing Returns:**
Last 20% often costs 80% of effort.

**Better Metric:**
[[strong-signal]] Critical paths must have tests. Coverage % less important.

Related to [[smooth-flow]] deployment confidence.""",
            "tags": ["testing", "quality", "question"],
            "links": ["strong-signal", "smooth-flow"]
        },
        {
            "id": "hard-truth",
            "title": "Should We Automate This Manual Task?",
            "content": """**Question:** When is automation worth the upfront cost?

**Rule of Thumb:**
If done >3x/week and takes >30 min, automate.

**Caution:**
[[deep-valley]] Toil reduction has value beyond time savings - reduces errors, enables scaling.

Part of [[brave-river]] SRE philosophy.""",
            "tags": ["automation", "sre", "question"],
            "links": ["deep-valley", "brave-river"]
        },
        {
            "id": "gentle-touch",
            "title": "How Often Should We Refactor?",
            "content": """**Question:** Continuous [[swift-wind]] refactoring or dedicated sprints?

**Continuous Pros:**
- [[ancient-tree]] Debt doesn't compound
- Momentum maintained

**Dedicated Pros:**
- Focused effort
- Easier to track

**Hypothesis:** Mix both - continuous small improvements + quarterly focused efforts.""",
            "tags": ["refactoring", "technical-debt", "question"],
            "links": ["swift-wind", "ancient-tree"]
        }
    ],

    # ORPHAN NOTES (10 notes) - No links, for testing orphan detection
    "orphans": [
        {
            "id": "lost-traveler",
            "title": "Conway's Law",
            "content": """Organizations design systems that mirror their communication structure.

**Implication:**
If you want microservices, organize teams around services.""",
            "tags": ["architecture", "organization"],
            "links": []
        },
        {
            "id": "forgotten-path",
            "title": "Hyrum's Law",
            "content": """With sufficient number of users, every observable behavior becomes depended upon.

**Implication:**
You can't change anything without breaking someone's workflow.""",
            "tags": ["api-design", "compatibility"],
            "links": []
        },
        {
            "id": "silent-echo",
            "title": "Brooks's Law",
            "content": """Adding people to a late project makes it later.

**Reason:**
Ramp-up time + communication overhead.""",
            "tags": ["project-management", "scaling"],
            "links": []
        },
        {
            "id": "empty-room",
            "title": "Peter Principle",
            "content": """People rise to their level of incompetence.

**In Tech:**
Great engineer becomes mediocre manager.""",
            "tags": ["management", "career"],
            "links": []
        },
        {
            "id": "blank-canvas",
            "title": "Parkinson's Law",
            "content": """Work expands to fill the time available.

**Application:**
Set tight deadlines to prevent scope creep.""",
            "tags": ["productivity", "time-management"],
            "links": []
        },
        {
            "id": "cold-stone",
            "title": "Hofstadter's Law",
            "content": """It always takes longer than you expect, even when you account for Hofstadter's Law.

**Lesson:**
Estimates are always optimistic. Plan accordingly.""",
            "tags": ["estimation", "project-management"],
            "links": []
        },
        {
            "id": "distant-star",
            "title": "The Two Pizza Rule",
            "content": """Teams should be small enough to feed with two pizzas (~6-8 people).

**Rationale:**
Communication overhead grows O(n²) with team size.""",
            "tags": ["team-size", "organization"],
            "links": []
        },
        {
            "id": "lone-wolf",
            "title": "Rubber Duck Debugging",
            "content": """Explain code to inanimate object to find bugs.

**Why it Works:**
Articulating problem reveals assumptions.""",
            "tags": ["debugging", "techniques"],
            "links": []
        },
        {
            "id": "isolated-peak",
            "title": "The Bike Shed Effect",
            "content": """People spend time on trivial decisions they understand, ignoring complex important ones.

**Example:**
Arguing about variable names instead of architecture.""",
            "tags": ["decision-making", "meetings"],
            "links": []
        },
        {
            "id": "abandoned-road",
            "title": "Not Invented Here Syndrome",
            "content": """Rejecting external solutions because they weren't built internally.

**Cost:**
Wasted effort rebuilding existing solutions.""",
            "tags": ["culture", "anti-pattern"],
            "links": []
        }
    ]
}


def generate_corpus() -> None:
    """Generate the full Zettelkasten corpus."""
    logger.info("=== Generating Zettelkasten Test Corpus ===\n")

    # Get Neo4j adapter
    neo4j = get_neo4j_adapter()

    if not neo4j.is_available():
        logger.error("❌ Neo4j is not available")
        sys.exit(1)

    # Clear existing notes
    logger.info("Clearing existing notes...")
    with neo4j.driver.session(database=neo4j.database) as session:
        session.run("MATCH (n:Note) DETACH DELETE n")
    logger.info("✓ Database cleared\n")

    # Create notes in order (entry points first for proper linking)
    categories = ["entry_points", "hubs", "regular", "stubs", "questions", "orphans"]
    total_created = 0

    for category in categories:
        logger.info(f"Creating {category.replace('_', ' ')} notes...")
        notes = NOTES[category]

        for note in notes:
            try:
                neo4j.create_note(
                    note_id=note["id"],
                    title=note["title"],
                    content=note["content"],
                    author="Erik",
                    tags=note["tags"],
                    links=note.get("links", []),
                )
                total_created += 1
                logger.info(f"  ✓ {note['id']}: {note['title']}")
            except Exception as e:
                logger.error(f"  ✗ Failed to create {note['id']}: {e}")

        logger.info(f"  Created {len(notes)} {category.replace('_', ' ')} notes\n")

    logger.info(f"{'='*60}")
    logger.info(f"✅ Generated {total_created} notes")
    logger.info(f"{'='*60}\n")

    # Show statistics
    with neo4j.driver.session(database=neo4j.database) as session:
        # Count by category
        result = session.run("""
            MATCH (n:Note)
            RETURN
                count(n) as total,
                count(CASE WHEN size([(n)-[:LINKS_TO]->() | 1]) = 0 AND NOT exists((()-[:LINKS_TO]->(n))) THEN 1 END) as orphans,
                count(CASE WHEN size([(n)-[:LINKS_TO]->() | 1]) = 0 AND exists((()-[:LINKS_TO]->(n))) THEN 1 END) as dead_ends,
                count(CASE WHEN size([(n)-[:LINKS_TO]->() | 1]) >= 5 THEN 1 END) as hubs,
                avg(size([(n)-[:LINKS_TO]->() | 1])) as avg_links
        """)
        stats = result.single()

        logger.info("Graph Statistics:")
        logger.info(f"  Total notes: {stats['total']}")
        logger.info(f"  Orphans (no links): {stats['orphans']}")
        logger.info(f"  Dead ends (no outbound links): {stats['dead_ends']}")
        logger.info(f"  Hub notes (5+ links): {stats['hubs']}")
        logger.info(f"  Average links per note: {stats['avg_links']:.1f}")


if __name__ == "__main__":
    generate_corpus()
