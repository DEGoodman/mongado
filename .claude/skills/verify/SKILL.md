---
name: verify
description: Runtime verification recipe for Mongado (Docker dev stack, Next.js frontend + FastAPI backend)
---

# Verifying changes in Mongado

Dev stack is always-on Docker Compose: `backend` (FastAPI, :8000, uvicorn auto-reload on file save), `frontend` (Next.js dev, :3000), `neo4j`, `ollama`. No build step needed for backend changes — saving a `.py` file restarts uvicorn.

## Handles

- **API**: `curl http://localhost:8000/api/...`. Admin-only endpoints (note create/update/delete): `TOKEN=$(grep "^ADMIN_TOKEN=" backend/.env | cut -d= -f2)` then `-H "Authorization: Bearer $TOKEN"`.
- **UI**: Chrome DevTools MCP against `http://localhost:3000`. First hit on a route compiles in Next dev — use `timeout: 45000`, the default 10s times out.
- **Dev Neo4j often has zero notes.** Create one via POST /api/notes (admin token) to exercise note pages; DELETE it after.

## Gotchas

- Article pages are ISR (`revalidate = 300`) server components: after a backend change that alters article HTML, the first page load serves the **stale** cached render and revalidates in background — reload once to see fresh output before concluding anything.
- Never `make build-frontend` while the dev server runs (prod build clobbers the dev `.next` volume).
- Note pages are client components (fetch on mount) — no ISR staleness there.
