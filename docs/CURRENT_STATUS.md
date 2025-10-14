# Mongado - Current Status (October 2025)

**Last Updated:** 2025-10-14

## 🎉 What's Working Today

### ✅ Production Deployment
- **Live at:** https://mongado.com
- **API:** https://api.mongado.com
- **Server:** DigitalOcean Premium AMD 2vCPU / 4GB RAM
- **Auto-deployment:** GitHub Actions on push to main
- **Fast article deployment:** Separate workflow for static content (~10s vs 5-10min)
- **SSL/HTTPS:** Configured with Let's Encrypt
- **Monitoring:** Basic health checks in deployment workflow

### ✅ Knowledge Base - Articles
- **Storage:** Static markdown files with YAML frontmatter
- **Features:**
  - List view with preview cards (title, date, tags, 200-char preview)
  - Detail view with full markdown rendering
  - Client-side search (filters by title, content, tags)
  - Wikilinks support: `[[note-id]]` syntax
  - Image optimization (WebP conversion)
- **Content authoring:** Write markdown files, push to `backend/static/articles/`
- **Fast deployment:** Changes deploy in ~10 seconds via `deploy-articles.yml`

### ✅ Knowledge Base - Notes (Zettelkasten)
- **Persistent notes:** Neo4j graph database (admin only)
- **Ephemeral notes:** In-memory storage (session-based for visitors)
- **Features:**
  - Adjective-noun IDs (e.g., `wise-mountain`, `curious-elephant`)
  - Wikilinks: `[[note-id]]` syntax with autocomplete
  - Bidirectional backlinks
  - Graph visualization (force-directed layout)
  - Local subgraphs (view connections around a note)
  - CodeMirror markdown editor (replaced TipTap for simpler UX)
- **API endpoints:**
  - Full CRUD operations
  - Backlinks and outbound links
  - Graph data endpoints

### ✅ AI Integration (Ollama)
- **Model:** llama3.2:1b (optimized for 4GB RAM server)
- **Features:**
  - Unified "Ask" mode (hybrid KB + general knowledge)
  - Semantic search with embeddings
  - Embedding cache (SHA256-based, major performance win)
  - 90-second timeout for slower server responses
- **Performance:** 30-60 seconds per query on 2vCPU server
- **Smart hybrid prompting:** Tries KB first, falls back to general knowledge

### ✅ Authentication
- **Admin auth:** Bearer token (ADMIN_TOKEN) for persistent notes
- **Session-based:** X-Session-ID header for ephemeral notes
- **UI indicator:** Shows "Admin: Erik" when authenticated
- **Login page:** `/login` with passkey stored in localStorage

### ✅ Development Environment
- **Docker Compose:** Full stack with hot-reloading
- **Services:** Backend, Frontend, Neo4j, Ollama
- **1Password integration:** Secrets management via service account token
- **CI/CD:** Pre-push hooks for linting, type checking, formatting
- **Testing:** Unit tests for backend, component tests for frontend

## 📊 Architecture Overview

```
Frontend (Next.js 15)
├── Articles (static markdown)
├── Notes (Zettelkasten)
├── Graph visualization (D3.js force-directed)
└── AI Panel (Ollama integration)

Backend (FastAPI + Python 3.13)
├── Article loader (filesystem)
├── Notes service (Neo4j + SQLite fallback)
├── Ephemeral store (in-memory)
├── Ollama client (embeddings + chat)
└── ID generator (adjective-noun)

Data Storage
├── Static articles: backend/static/articles/*.md
├── Static assets: backend/static/assets/
├── Persistent notes: Neo4j graph database
├── Ephemeral notes: In-memory (session-scoped)
└── Note metadata: SQLite (fallback when Neo4j unavailable)

AI/ML
├── Ollama (local LLM)
├── Model: llama3.2:1b
├── Embedding cache (content hash-based)
└── Semantic search + Q&A
```

## 🎯 Key Decisions Made

### 1. Editor Simplification (Oct 14, 2025)
**Decision:** Replaced TipTap with CodeMirror
**Rationale:**
- TipTap was complex and caused markdown rendering issues
- CodeMirror is simpler, lighter, more markdown-native
- Better for AI assistant (pure markdown vs HTML conversion)
- Removed 71 packages, added 26 packages
- User prefers simplest approach

### 2. AI Performance Optimization (Oct 14, 2025)
**Decision:** Merged Search/Q&A into unified Ask mode with embedding cache
**Rationale:**
- Q&A was 2x slower than Search (did search + generation)
- Users confused about difference between modes
- Embedding cache prevents regenerating for same content
- Hybrid mode: KB first, general knowledge fallback

### 3. Ollama Model Selection (Oct 14, 2025)
**Decision:** Use llama3.2:1b instead of 3B
**Rationale:**
- 3B model needs 2.9GB, only 2.3GB available after OS
- 1B model needs ~1.3GB, fits comfortably in 4GB server
- Acceptable quality for knowledge base use case
- Can upgrade to 3B if server upgraded to 8GB

### 4. Article Preview Cards (Oct 14, 2025)
**Decision:** List view shows previews, detail view shows full content
**Rationale:**
- Full content in list made page overwhelming
- Search was working but hard to see value
- Standard REST pattern (list = preview, detail = full)
- Better UX for scanning/browsing

### 5. Fast Article Deployment (Oct 14, 2025)
**Decision:** Separate GitHub Action for static content
**Rationale:**
- Articles written separately, deployed frequently
- Full rebuild takes 5-10 minutes, uses server resources
- Article-only deploy takes ~10 seconds (git pull + backend restart)
- Enables rapid content iteration

## 🚧 Known Issues & Limitations

### Current Limitations
1. **AI response time:** 30-60 seconds on 2vCPU server (acceptable for now)
2. **No staging environment:** All changes go directly to production
3. **Basic auth:** Simple passkey, no session expiry or refresh
4. **No backups:** Neo4j data not automatically backed up
5. **No monitoring:** No alerts for errors or downtime

### Technical Debt
1. **Test coverage:** Backend ~50%, Frontend ~30%
2. **No E2E tests:** Only unit/component tests
3. **Type errors:** Mypy shows warnings (not blocking)
4. **Large components:** Some React components could be split
5. **Logging:** No centralized log aggregation

## 🎯 Immediate Next Steps

### High Priority (Next 2 Weeks)
1. **Homepage development:** Build out portfolio/professional presence
   - Hero section with bio
   - Projects showcase
   - Link to Knowledge Base
   - Contact information

2. **Neo4j backup automation:**
   - Daily backup script
   - Upload to DigitalOcean Spaces
   - Restore procedure documented

3. **Basic monitoring:**
   - Uptime check (UptimeRobot or similar)
   - Error tracking (Sentry free tier)
   - Disk space alerts

### Medium Priority (Next Month)
1. **Testing improvements:**
   - Increase backend test coverage to 70%+
   - Add E2E tests for critical paths (create note, view graph)
   - Add visual regression tests

2. **Auth improvements:**
   - Session expiry (7 days)
   - Refresh token mechanism
   - Better logout flow

3. **Content organization:**
   - Note templates (Person, Book, Project)
   - Bulk operations (tag multiple notes)
   - Export notes to Obsidian format

### Low Priority (Future)
1. **Database evaluation:** PostgreSQL vs continued Neo4j
2. **Advanced search:** Full-text search with Meilisearch
3. **Graph enhancements:** Multiple layouts, time animation
4. **Mobile optimization:** PWA or React Native app

## 📝 Documentation Status

### ✅ Up to Date
- `CLAUDE.md` - Project guidance for AI assistance
- `README.md` - Quick start guide
- `docs/DEPLOYMENT.md` - Production deployment
- `docs/knowledge-base/ARTICLES.md` - Content authoring
- `docs/knowledge-base/NOTES.md` - Zettelkasten guide
- `docs/TESTING.md` - Testing strategy
- `docs/PROFILING.md` - Performance profiling

### ⚠️ Needs Update
- `docs/PROJECT_STATUS.md` - Outdated (Oct 2024) → Use this document instead
- `docs/ROADMAP.md` - Many items completed, needs refresh
- `docs/PRODUCTION.md` - Merge with DEPLOYMENT.md (duplicate info)
- `docs/PRODUCTION_ENV.md` - Merge with DEPLOYMENT.md

### 🗑️ Can Archive
- `docs/DEVELOPMENT_SETUP.md` - Content moved to README.md
- `docs/DNS_SETUP.md` - DNS already configured, move to archive/
- `docs/DISASTER_RECOVERY.md` - Empty, remove or complete

## 🔮 Vision & Direction

### What Mongado Is
- **Personal knowledge management system** with Zettelkasten principles
- **Static article platform** for long-form writing
- **Professional portfolio** showcasing projects and expertise
- **AI-enhanced** search and discovery

### What Mongado Is Not
- Not a social network or collaborative platform (at least not yet)
- Not a general-purpose CMS
- Not trying to replace Notion/Obsidian (but can complement them)
- Not focused on mobile-first (desktop-first, mobile-responsive)

### Success Criteria
1. **Personal use:** Erik actively uses it for note-taking and writing
2. **Content growth:** Consistent addition of articles and notes
3. **Performance:** Fast enough for daily use (current: acceptable)
4. **Reliability:** >99% uptime, no data loss
5. **Maintainability:** Easy to update, debug, extend

## 📞 Questions for Erik

1. **Homepage priority:** How important is building out the homepage vs continuing KB features?
2. **AI performance:** Is 30-60s per query acceptable, or should we prioritize optimization?
3. **Backup frequency:** Daily backups sufficient, or need more frequent?
4. **Monitoring:** What matters most? Uptime? Errors? Performance?
5. **Next features:** Templates? Export? Advanced search? Something else?

---

**Next Review:** 2025-11-14 (1 month)
