# Research Findings Board: UI Test Suite

## Status: Wave 1 Complete, Wave 2 Dispatching

## Key Findings So Far

### Security (Critical)
- Default JWT secret `t0p-s3cr3t` not blocked if unchanged — JWT forgery
- `exec()` on user-supplied tool/function code — intentional RCE by design
- Arbitrary pip install from tool frontmatter — no validation
- `WEBUI_AUTH=False` creates hardcoded admin/admin
- No rate limiting anywhere (login, API keys, etc.)
- Wildcard CORS `*` default with credentials=true
- No CSRF protection, no security headers by default
- No server-side file size limit, no MIME allowlist
- `GET /memories/ef` unauthenticated debug endpoint exposing embedding function
- `GET /api/config` exposes Google Drive API key unauthenticated
- `GET /api/v1/retrieval/` leaks embedding config unauthenticated

### Frontend XSS
- `{@html token.text}` bypasses DOMPurify via iframe prefix check
- `{@html svg}` in SVGPanZoom unsanitized
- `console.log(sessionUser)` leaks JWT on every login
- localStorage.token with no expiry/refresh

### API Patterns
- Error shape `{"detail": "..."}` consistent but tasks.py returns 200 with error shape
- Three different pagination styles, no envelope
- Full table scans in training/eval list queries
- SSE proxy framing mismatch (evaluations dry-run path)
- Duplicate GET route for `/evaluations/feedbacks/all`
- Dead `commit_session_after_request` middleware (commits wrong session)
- Fire-and-forget startup tasks with no supervision

### Schema/Migration
- curator_job.dataset_name and created_knowledge_id only in Peewee migration, not Alembic — fresh deploy breaks

### Test Infrastructure
- 52 passing model unit tests (SQLite), not in CI
- 5 router integration test classes — BROKEN (missing selfai_ui.routers.webui module)
- 16 retrieval unit tests — likely passing, not in CI
- Cypress E2E: 4 files, only automated tests in CI
- Frontend unit tests: ZERO
- pytest job in CI is commented out

### Library Landscape
- Backend: pytest + httpx TestClient/AsyncClient + anyio + respx + factory_boy + schemathesis
- Frontend: vitest + @testing-library/svelte v4 + MSW v2 (or Playwright for E2E)
- DB: pytest-postgresql for real Postgres tier, transaction rollback pattern for speed
- Security: schemathesis (fuzz), bandit (SAST), pip-audit (CVE)

## Open Questions for Wave 2
- Best practices for testing inherited plugin/exec() architectures safely
- Pitfalls specific to testing FastAPI apps with dual session patterns
- How to structure test tiers for an app with 5 external service dependencies
- Security testing methodology for self-hosted apps with admin-as-root trust model
