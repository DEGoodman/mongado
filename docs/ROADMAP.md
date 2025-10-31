# Mongado Development Priorities (October 2025)

> **Updated**: October 29, 2025  
> **Active Tracker**: [GitHub Issues](https://github.com/DEGoodman/mongado/issues)  
> **Project Board**: See [#82](https://github.com/DEGoodman/mongado/issues/82)

## 🎯 Current Focus

All active development is tracked via GitHub Issues with priority labels. This document provides a high-level view of our roadmap priorities.

---

## 🔥 High Priority (Do First)

**Foundational UX & Philosophy**

- **#78** - [Improve header and information architecture](https://github.com/DEGoodman/mongado/issues/78)
  - Articles vs Notes distinction unclear
  - Visual hierarchy issues
  - Well-defined spec with mockups
  - **Impact**: Every page view
  
- **#42** - [Review Zettelkasten state](https://github.com/DEGoodman/mongado/issues/42)
  - Align Notes with Zettelkasten philosophy
  - Review existing notes for clarity
  - Inform future UI/UX decisions
  - **Impact**: Core content strategy

**Why these first**: Define the core user experience and content philosophy. Everything else builds on this foundation.

---

## 📋 Medium Priority (Do Soon)

**Technical Foundation**

- **#14** - [Testing: Achieve 80%+ Backend Test Coverage](https://github.com/DEGoodman/mongado/issues/14)
  - Prevent regressions as codebase grows
  - Add incrementally as you work on features
  - **Approach**: Test as you go, not all at once

- **#77** - [Progressive/streaming display for AI suggestions](https://github.com/DEGoodman/mongado/issues/77)
  - Improve perceived performance
  - Frontend streaming implementation
  - **Benefit**: Better UX for slow AI operations

---

## 💡 Low Priority / Backlog

**AI Feature Polish**
- **#55** - AI Features Manual Testing Plan
- **#34** - Batch article concept extraction
- **#15** - AI: Auto-tagging and Concept Extraction (needs breakdown)

**Infrastructure**
- **#63** - Add resource usage monitoring endpoint
- **#82** - Create GitHub Project board

---

## 💭 Ideas (Not Yet Scoped)

Features to consider for future development:

- **#13** - Note Templates (Person, Book, Concept, Project)
- **#22** - Export notes as markdown files for version control
- **#35** - AI: Add graph analysis for clusters and orphans
- **#36** - UI: Add knowledge base health dashboard
- **#43** - Zen Mode for distraction-free writing
- **#58** - Search result snippeting with contextual highlighting

---

## 📚 Article Ideas (12 ideas)

All article ideas tracked with `kb` + `article-idea` labels. Filter: [article-idea issues](https://github.com/DEGoodman/mongado/issues?q=is%3Aissue+is%3Aopen+label%3Aarticle-idea)

Topics include: SaaS billing, engineering management, SRE practices, and technical frameworks.

---

## 🎬 Suggested Action Plan

### Phase 1: Clarity & Philosophy (1-2 weeks)
1. Start with **#42** (Review Zettelkasten) - Quick alignment check
2. Then tackle **#78** (Header/IA improvements) - Clear spec, high impact

### Phase 2: Stability (Ongoing)
3. **#14** (Testing) - Add incrementally as you work

### Phase 3: AI Polish (As needed)
4. **#77, #55, #34** - When AI usage increases

### Phase 4: Later
5. **#63, #15, #82** - When specific needs arise

---

## 📊 Labels & Filtering

**Priority Labels:**
- `priority: high` - Foundational work, do first
- `priority: medium` - Important but not urgent
- `priority: low` - Nice to have, backlog

**Status Labels:**
- `status: todo` - Ready to work on
- `status: in-progress` - Actively being worked on
- `status: done` - Completed
- `status: idea` - Not yet scoped

**Quick Filters:**
- [High priority todos](https://github.com/DEGoodman/mongado/issues?q=is%3Aissue+is%3Aopen+label%3A%22priority%3A+high%22)
- [All open features](https://github.com/DEGoodman/mongado/issues?q=is%3Aissue+is%3Aopen+label%3Afeature)
- [In progress work](https://github.com/DEGoodman/mongado/issues?q=is%3Aissue+is%3Aopen+label%3A%22status%3A+in-progress%22)


---

# Historical Roadmap (Reference Only)

> The content below is kept for historical reference. See above for current priorities.

This document tracks planned features, improvements, and technical debt for the Mongado project.

## Current Status

### ✅ Completed

- [x] Basic project structure (FastAPI + Next.js)
- [x] 1Password integration for secrets management
- [x] Docker development and production setup
- [x] Static article system with markdown + frontmatter
- [x] Image optimization workflow (WebP conversion)
- [x] Basic resource API (CRUD operations)
- [x] Zettelkasten notes system
  - [x] Adjective-noun IDs
  - [x] Wikilink syntax `[[note-id]]`
  - [x] Persistent notes (Neo4j database)
  - [x] Bidirectional backlinks
- [x] AI integration (Ollama)
  - [x] Semantic search
  - [x] Q&A with context
  - [x] AI-suggested links
  - [x] Auto-generated summaries
- [x] Graph visualization
  - [x] Force-directed layout
  - [x] Interactive navigation
  - [x] Local subgraphs
- [x] Frontend Knowledge Base UI
  - [x] Article browsing and display
  - [x] Note editor with wikilink autocomplete
  - [x] Graph view
  - [x] Backlinks panel

## High Priority

### ✅ Production Deployment (COMPLETED - Oct 2025)

**Status**: ✅ Live at https://mongado.com

**Completed**:
- ✅ Created DigitalOcean droplet (Premium AMD 2vCPU / 4GB RAM)
- ✅ Configured DNS records on Hover.com
  - ✅ A record for `@` (root domain)
  - ✅ A record for `www`
  - ✅ A record for `api`
  - ✅ Fastmail MX records preserved
- ✅ Set up GitHub Secrets in repository
- ✅ Configured Nginx reverse proxy
- ✅ Set up SSL certificates with Let's Encrypt
- ✅ GitHub Actions auto-deployment on push to `main`
- ✅ Fast article deployment workflow (~10s)
- ✅ Frontend accessible at https://mongado.com
- ✅ Backend API at https://api.mongado.com
- ✅ SSL certificates valid and auto-renewing
- ✅ Email still working via Fastmail

**Documentation**: See `docs/DEPLOYMENT.md` for complete deployment guide

### Authentication System (Q1 2025)

**Goal**: Implement proper admin authentication with dev and production keys.

**Tasks**:
- [ ] Set up dev passkey in 1Password (`mongado-dev-passkey`)
- [ ] Set up prod passkey in 1Password (`mongado-prod-passkey`)
- [ ] Create login page/modal at `/admin/login`
- [ ] Implement session management (JWT or session cookies)
- [ ] Add logout functionality
- [ ] Protect admin endpoints:
  - `POST /api/notes`
  - `PUT /api/notes/{id}`
  - `DELETE /api/notes/{id}`
  - `POST /api/resources` (if used for persistent content)
- [ ] Add admin indicator in UI (header/nav bar)
- [ ] Test auth flow in both dev and prod environments

**Technical Details**:
- Use simple passkey approach (Bearer token in Authorization header)
- Store passkey in localStorage after login
- Auto-refresh or prompt for re-auth on 401/403
- Different passkeys for dev vs prod (configured via environment)

**Reference**:
See `docs/knowledge-base/NOTES.md` for current auth implementation details.

### Database Migration (Q1-Q2 2025)

**Goal**: Move from in-memory storage to persistent database for all dynamic content.

**Current State**:
- Static articles: Filesystem (✅ complete)
- Persistent notes: Neo4j (✅ complete)
- User-created resources: In-memory (⚠️ needs migration)

**Tasks**:
- [ ] Evaluate database options:
  - [ ] Neo4j (current) - excellent for graph relationships
  - [ ] PostgreSQL - mature, well-understood, recursive CTEs for graphs
  - [ ] Hybrid: PostgreSQL + Neo4j (PostgreSQL for data, Neo4j for relationships)
- [ ] Design schema/model for all dynamic content
- [ ] Implement database connection and pooling
- [ ] Create migration scripts
- [ ] Add database health check endpoint
- [ ] Update Docker setup with database service
- [ ] Add database backup/restore documentation

**Decision Factors**:
- Graph size (expected number of notes and links)
- Query patterns (deep graph traversals vs simple lookups)
- Operational complexity
- Performance benchmarks

## Medium Priority

### Homepage Development (Q2 2025)

**Goal**: Build out the personal portfolio/professional presence homepage.

**Features**:
- [ ] Hero section with bio and photo
- [ ] Projects showcase
- [ ] Contact form
- [ ] Social media links
- [ ] Resume/CV download
- [ ] Navigation to Knowledge Base

**Design**:
- Clean, minimal aesthetic
- Mobile-responsive
- Fast loading (< 1s first contentful paint)
- Accessible (WCAG 2.1 AA)

### Knowledge Base Enhancements (Q2-Q3 2025)

**Notes System**:
- [ ] Note templates (Person, Book, Concept, Project)
- [ ] Version history and diffs
- [ ] Export to Obsidian/Roam format
- [ ] Import from Notion/Roam/Obsidian
- [ ] Note merge and split operations
- [ ] Bulk operations (tag all, delete selected)

**Search & Discovery**:
- [ ] Full-text search with Meilisearch or Elasticsearch
- [ ] Advanced filters (date range, author, tag combinations)
- [ ] Saved searches
- [ ] Search history
- [ ] Related articles/notes sidebar

**Graph Visualization**:
- [ ] Multiple layout algorithms (force, hierarchical, circular)
- [ ] Graph statistics (centrality, clusters)
- [ ] Time-based animation (show graph growth over time)
- [ ] Export graph as image (PNG, SVG)
- [ ] Shareable graph views (with filtering)

**Content**:
- [ ] Rich media support (embedded videos, audio)
- [ ] Mermaid.js diagram support in markdown
- [ ] Math equations (KaTeX or MathJax)
- [ ] Code syntax highlighting improvements
- [ ] Footnotes and citations

### AI Enhancements (Q3 2025)

**Goal**: Expand AI capabilities beyond search and suggestions.

**Features**:
- [ ] Auto-tagging based on content
- [ ] Cluster detection (find groups of related notes)
- [ ] Suggest note structure (outline generation)
- [ ] Question-answering over full knowledge graph
- [ ] Summarize multiple related notes
- [ ] Concept extraction and linking
- [ ] Writing assistance (expand on ideas, clarify language)

**Technical**:
- [ ] Evaluate local LLM alternatives (Mistral, Llama 3, etc.)
- [ ] Implement embedding caching for performance
- [ ] Add cost/usage monitoring
- [ ] Rate limiting for AI features

### Testing & Quality (Ongoing)

**Backend**:
- [ ] Achieve 80%+ test coverage
- [ ] Add integration tests for all API endpoints
- [ ] Performance tests (load testing with Locust)
- [ ] Security audits (OWASP top 10)

**Frontend**:
- [ ] Component test coverage > 70%
- [ ] E2E tests for critical paths
- [ ] Visual regression testing (Percy or Chromatic)
- [ ] Accessibility audits (axe-core, Lighthouse)

**Infrastructure**:
- [x] CI/CD pipeline (GitHub Actions)
- [x] Automated deployment to production
- [ ] Add staging environment
- [ ] Database backup automation
- [ ] Monitoring and alerting (Sentry, Datadog, or self-hosted)

## Low Priority / Future Ideas

### Collaborative Features (Q4 2025+)

- [ ] Public note sharing (opt-in, per-note)
- [ ] Comments on shared notes
- [ ] Suggestion mode (propose edits)
- [ ] Multi-user support (invite collaborators)

### Mobile App (2026+)

- [ ] React Native or Flutter app
- [ ] Quick note capture
- [ ] Offline mode with sync
- [ ] Push notifications
- [ ] Voice note transcription

### Content Organization (2026+)

- [ ] Collections (curated groups of notes/articles)
- [ ] Daily notes (journal-style entries)
- [ ] Kanban board view
- [ ] Timeline view (content by date)
- [ ] Mind map view

### Integrations (2026+)

- [ ] Browser extension (web clipper)
- [ ] API webhooks for automation
- [ ] Zapier/IFTTT integration
- [ ] RSS feed of published articles
- [ ] Newsletter/email digest

### Performance & Scale (As Needed)

- [ ] CDN integration (Cloudflare, Fastly)
- [ ] Image optimization service (imgix, Cloudinary)
- [ ] Database read replicas
- [ ] Caching layer (Redis)
- [ ] Search index optimization

## Technical Debt

### Code Quality

- [ ] Refactor large components (break down into smaller units)
- [ ] Standardize error handling patterns
- [ ] Improve type safety (eliminate `any` types in TypeScript)
- [ ] Document complex algorithms and business logic
- [ ] Add JSDoc/docstrings to all public functions

### Infrastructure

- [ ] Set up proper logging aggregation
- [ ] Implement structured logging (JSON format)
- [ ] Add request tracing (correlation IDs)
- [ ] Migrate from .env files to proper secrets management in production
- [ ] Set up automated backups for database

### Documentation

- [x] Split Knowledge Base docs from root documentation
- [x] Create ARTICLES.md and NOTES.md guides
- [ ] Add API documentation (OpenAPI/Swagger)
- [ ] Create video tutorials for common workflows
- [ ] Write contributor guide (if opening to contributions)
- [ ] Add troubleshooting runbook for common issues

## Completed Milestones

### Q4 2024
- ✅ Initial project setup
- ✅ Docker development environment
- ✅ 1Password integration
- ✅ Basic FastAPI backend
- ✅ Next.js frontend scaffold

### Q1-Q4 2025
- ✅ Knowledge Base architecture
- ✅ Static article system with markdown
- ✅ Image optimization pipeline
- ✅ Zettelkasten notes system
- ✅ Neo4j integration for persistent notes
- ✅ Wikilink parsing and bidirectional links
- ✅ Ollama AI integration
- ✅ Graph visualization (frontend)
- ✅ Documentation reorganization
- ✅ CI/CD pipeline with GitHub Actions
- ✅ Production deployment automation (DigitalOcean)
- ✅ DNS configuration guide (preserving Fastmail email)
- ✅ **Production deployment completed - Live at mongado.com**
- ✅ Fast article deployment workflow
- ✅ AI embedding cache for performance
- ✅ CodeMirror markdown editor (replaced TipTap)
- ✅ Article preview cards with detail view
- ✅ Basic admin authentication (Bearer token)

## Contribution Guidelines

This is currently a personal project, but if you're interested in contributing:

1. **Open an issue**: Discuss the feature/fix before starting work
2. **Follow conventions**: See CLAUDE.md for code patterns
3. **Write tests**: All new features need tests
4. **Update docs**: Keep documentation in sync with changes
5. **Small PRs**: Break large features into reviewable chunks

## Questions & Feedback

For questions or suggestions about the roadmap:
- Open an issue in the GitHub repo
- Contact via the website contact form (once live)
- Email: [your email here]

---

Last updated: 2025-10-14
