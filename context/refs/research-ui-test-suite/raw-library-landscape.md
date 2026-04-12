## Agent: library-landscape — Findings

**Note:** WebSearch blocked. Findings from FastAPI live docs fetch + training knowledge (Aug 2025).

### Q1: FastAPI Testing Stack (2024-2026)

**Layer 1 — Sync integration tests (default):**
- `fastapi.testclient.TestClient` (backed by httpx)
- Plain `def test_*` — no async needed

**Layer 2 — Async tests:**
- `httpx.AsyncClient` with `transport=ASGITransport(app=app)`
- `@pytest.mark.anyio` (FastAPI now recommends anyio over pytest-asyncio)
- `asgi-lifespan` needed if app uses startup/shutdown events

**Key 2024-2025 changes:**
- `httpx.ASGITransport` required (old `AsyncClient(app=app)` deprecated in httpx 0.23+)
- `pytest-asyncio >= 0.21` requires explicit `asyncio_mode` config

**Existing codebase gap:** `requirements.txt` has pytest but NO httpx, pytest-asyncio, or anyio. Existing conftest uses SQLite patching only — HTTP layer entirely untested.

**Confidence: High** (confirmed from live FastAPI docs)

### Q2: API Security Testing Tools

**Schemathesis (~3.33):** OpenAPI-driven fuzz testing. Zero test-writing for baseline coverage. `schemathesis run http://localhost:8000/openapi.json --checks all`. Can use TestClient transport.

**Bandit (~1.7):** Python SAST. Hardcoded secrets, SQL injection via string formatting, eval(), insecure subprocess.

**pip-audit (~2.7):** Dependency CVE scanning. Will flag `python-jose==3.3.0` for key confusion CVEs.

**Confidence: High**

### Q3: SvelteKit 2 / Svelte 4 Testing Stack

Project already has: `vitest ^1.6.0`, `cypress ^13.15.0`

**Canonical 2024-2025 stack:**
- Vitest + `@testing-library/svelte` v4 (for Svelte 4) + jsdom/happy-dom
- Playwright 1.44+ preferred over Cypress (SvelteKit scaffold switched in 2024)

**Missing from project:** `@testing-library/svelte`, `@testing-library/jest-dom`. Vitest present but unused (passWithNoTests).

**Confidence: High**

### Q4: Testing Stores and API Client Modules

**Svelte stores:** Plain JS, testable without DOM. `get(myStore)` from svelte/store.

**API client modules:** Pure TypeScript + fetch. Options:
- `vi.stubGlobal('fetch', ...)` 
- **MSW v2** (Mock Service Worker) — intercepts at network level, works with SvelteKit fetch
- `@mswjs/data` for factory-style in-memory DB for handlers

**SSE/streaming in API tests:** ReadableStream + TransformStream in MSW handlers

**Confidence: High**

### Q5: WebSocket and SSE Testing

**Backend WebSocket:** `TestClient.websocket_connect("/ws")` — synchronous, standard
**Backend SSE:** `client.stream("GET", "/events")` + `iter_lines()`
**Frontend WebSocket:** `mock-socket` or `@socket.io/mock-socket` for Socket.IO
**Frontend SSE:** MSW v2 supports streaming, or mock EventSource
**E2E:** Playwright has `page.on('websocket', ...)` and `route.fulfill()` for SSE

**Confidence: Medium-High**

### Q6: Database Testing — SQLAlchemy + PostgreSQL

**Current project:** SQLite in-memory + monkey-patching get_db. Misses Postgres-specific semantics.

**Three tiers:**
1. SQLite in-memory (fast, zero infra) — good for model logic, bad for jsonb/array/CTEs
2. `pytest-postgresql` (~6.x) — real Postgres process, zero Docker
3. Transaction rollback per test — `begin_nested()` savepoint, fastest real-Postgres isolation

**Alembic integration:** Run `alembic upgrade head` once at session start, avoid metadata.create_all drift.

**Confidence: High**

### Q7: Mocking and Fixture Libraries

| Library | Purpose | Version | Priority |
|---|---|---|---|
| pytest | Runner | ~8.3 (existing) | existing |
| httpx | TestClient + AsyncClient | ~0.27 | **add** |
| anyio[pytest] | Async test marks | ~4.x | **add** |
| pytest-mock | mocker fixture | ~3.14 | **add** |
| factory_boy | Model factories | ~3.3 | **add** |
| Faker | Fake data | ~26 | **add** |
| respx | Mock httpx outbound | ~0.21 | **add** |
| schemathesis | OpenAPI fuzz | ~3.33 | **add** |
| bandit | SAST | ~1.7 | CI |
| pip-audit | CVE scanning | ~2.7 | CI |
| pytest-postgresql | Real Postgres | ~6.x | integration tier |

### Cross-Cutting Observations

1. **HTTP layer entirely untested** — highest-leverage gap. No TestClient tests for any of 30+ routers.
2. **Dependency injection not used for test isolation** — monkey-patching is fragile. Should use `app.dependency_overrides`.
3. **Cypress installed but Playwright is 2024+ SvelteKit default** — better SSE/WebSocket inspection.
4. **`@testing-library/svelte` missing** — Vitest present but no component testing library.
5. **`python-jose==3.3.0` CVE risk** — pip-audit will flag for key confusion vulnerabilities. Consider `joserfc`.
