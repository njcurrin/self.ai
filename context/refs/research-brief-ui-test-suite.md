---
Generated: 2026-04-11
Topic: ui-test-suite
Agents: 8 (4 codebase, 4 web/synthesis)
---

## Research Brief: UI Test Suite

### Summary

self.UI is a SvelteKit 2 + FastAPI application forked from Open-WebUI with extensive custom additions (curator, training, evaluations, job scheduling). The codebase has near-zero effective test coverage: 52 passing model-level unit tests exist but are not wired into CI, 5 router integration test classes are broken due to a stale import, zero frontend unit tests exist, and the only automated CI tests are 4 Cypress E2E files and a migration smoke test. Security analysis reveals multiple critical findings inherited from the Open-WebUI fork -- a well-known default JWT secret, exec()-based plugin RCE by design, and no rate limiting -- alongside medium-severity XSS vectors in Svelte `{@html}` usage and comprehensive input validation gaps on 19+ endpoints that accept raw `dict` instead of Pydantic models. The hybrid Peewee+Alembic migration system and dual-session database architecture create non-obvious testing pitfalls that must be designed around from the start.

### Key Findings

#### 1. Current State Assessment

**What exists (backend):**
- 52 passing model unit tests across 4 files in `backend/tests/`: benchmark_config (9), curator_jobs (15), gpu_queue (14), job_windows (14). All use SQLite in-memory with manual `get_db` monkey-patching in `conftest.py`. Not in CI.
- 5 router integration test classes in `backend/selfai_ui/test/apps/webui/routers/` (auths: 9, chats: 14, models: 1, prompts: 1, users: 1). All BROKEN -- `mock_user.py:8` imports `from selfai_ui.routers.webui import app` which was refactored into `main.py`.
- 16 retrieval unit tests across 2 files (firecrawl 403 handling, crawl options). Likely passing but not in CI.
- No `pytest.ini` or `[tool.pytest.ini_options]` configuration, no markers, no testpaths defined.

**What exists (frontend):**
- vitest ^1.6.0 installed; `"test:frontend": "vitest --passWithNoTests"` -- zero test files.
- `@testing-library/svelte` NOT installed.
- Cypress ^13.15.0 with 4 E2E files (registration, chat, documents, settings) -- the only tests running in CI.

**What's in CI:**
- `integration-test.yml`: Cypress E2E + migration smoke only.
- Pytest job block (lines 81-101) is fully commented out.
- `format-backend.yaml`: black formatting check only.
- `format-build-frontend.yaml`: build check only.

**Coverage by the numbers:**
- 32 router files, 0 with working HTTP-layer tests (0%).
- 21 model files, 4 with tests (19%).
- ~30 frontend API client modules, 0 with tests (0%).
- Frontend components: 0 tests.

#### 2. Security Findings (Prioritized)

**CRITICAL:**

1. **Default JWT secret `"t0p-s3cr3t"`** -- `env.py:361`. Well-known (public in Open-WebUI GitHub). Any deployment not overriding `WEBUI_JWT_SECRET_KEY` allows forged admin JWTs. The code only blocks empty string, not the default value.

2. **`exec()` on user-supplied code** -- `plugin.py:101,145`. By-design RCE for tool/function creators. Any user with workspace tool permission executes arbitrary Python on the server. No sandboxing.

3. **Arbitrary pip install from tool frontmatter** -- `plugin.py:173`. Tool code can declare pip dependencies that install without validation.

4. **`WEBUI_AUTH=False` creates hardcoded admin** -- `auths.py:330-335`. Creates `admin@localhost` / `admin` silently. Critical if instance is network-accessible.

**HIGH:**

5. **No rate limiting** -- Zero brute-force protection on login, API key creation, or any endpoint.

6. **Wildcard CORS with credentials** -- `main.py:909-913`. `CORS_ALLOW_ORIGIN` defaults to `"*"` with `allow_credentials=True`.

7. **`BYPASS_MODEL_ACCESS_CONTROL` env flag** -- Silently disables all model-level ACL when set.

8. **`GET /api/v1/memories/ef`** -- `memories.py:18-20`. Unauthenticated endpoint that invokes the embedding function. Debug endpoint left in production.

**MEDIUM:**

9. **`{@html token.text}` DOMPurify bypass** -- `MarkdownTokens.svelte:208`, `MarkdownInlineTokens.svelte:30`. Iframe prefix check falls through to raw `{@html}`.

10. **`{@html svg}` unsanitized** -- `SVGPanZoom.svelte:42`. DOMPurify imported but not applied.

11. **`console.log(sessionUser)` leaks JWT** -- `auth/+page.svelte:33`. Logs full session object including token on every login.

12. **No server-side file size enforcement** -- `FILE_MAX_SIZE` is config state read by frontend only.

13. **No CSRF protection** -- No tokens or middleware. `getFileContentById` uses cookie-only auth.

14. **19+ endpoints accept raw `dict`** -- No Pydantic validation on chat completions, tasks, tool execution, etc.

15. **JIT eval tokens have no TTL** -- Valid until explicit revocation.

16. **Google Drive API key leaked unauthenticated** -- Returned in `/api/config` response.

#### 3. Architecture & Patterns

**Backend:**
- **Dual session architecture**: `SessionLocal()` (non-scoped) used by all models vs `scoped_session` (`Session`) referenced by dead `commit_session_after_request` middleware.
- **Hybrid migrations**: Peewee (`internal/migrations/`) runs first, then Alembic (`migrations/versions/`). curator_job columns exist only in Peewee migration 019.
- **Auth via DI**: Consistent `Depends(get_verified_user/get_admin_user)` across 32 routers (363 occurrences). No global auth middleware.
- **Background tasks**: Four fire-and-forget `asyncio.create_task()` at startup. No supervision.
- **URL namespace split**: Custom service routers at root (`/curator`, `/llamolotl`) vs core API at `/api/v1/`.

**Frontend:**
- ~30 API modules with raw `fetch()`, inline auth headers, no shared interceptor.
- JWT in `localStorage.token`, no expiry monitoring, no refresh.
- Error pattern `error = err.detail` silently swallows undefined errors → null returns.
- No 401/403 handling. Mid-session expiry → broken UI, no re-auth.
- DOMPurify on most `{@html}` but bypass paths exist.

**Testing challenges specific to this codebase:**
- Dual sessions → transaction-rollback isolation doesn't work
- Peewee autocommit → can't roll back Peewee-managed table writes
- Import-time side effects fire during pytest collection
- `metadata.create_all()` misses Peewee-only columns
- `app` singleton global state bleeds between tests
- Frontend tab indentation → Edit tool can't match, requires Python-based edits

#### 4. Library Landscape

**Backend:**

| Tool | Purpose | Tier |
|------|---------|------|
| pytest ~8.3 (existing) | Runner | All |
| httpx ~0.27 + ASGITransport | TestClient | T0+ |
| anyio[pytest] ~4.x | Async test marks | T0+ |
| respx ~0.21 | Mock outbound HTTP | T0 |
| factory_boy ~3.3 | Model factories | T0+ |
| pytest-mock ~3.14 | Mocker fixture | T0+ |
| pytest-postgresql ~6.x | Real Postgres | T1+ |
| schemathesis ~3.33 | OpenAPI fuzz | T2 |
| bandit ~1.7 | SAST | CI |
| pip-audit ~2.7 | CVE scanning | CI |

**Frontend:**

| Tool | Purpose |
|------|---------|
| vitest ^1.6.0 (existing) | Runner |
| @testing-library/svelte v4 | Component testing |
| @testing-library/jest-dom | DOM assertions |
| MSW v2 | Network-level fetch mock |
| jsdom or happy-dom | DOM environment |

#### 5. Best Practices for This Codebase

1. **Use truncation-based teardown, not transaction rollback.** Dual sessions + Peewee autocommit make nested-transaction isolation unworkable.
2. **Override dependencies via `app.dependency_overrides`, not monkey-patching.** The existing conftest patches `get_db` in 5 modules individually — fragile.
3. **Run both Peewee AND Alembic migrations in test setup.** `metadata.create_all()` misses Peewee-only columns.
4. **Build an authorization matrix test.** Parametrized (role, endpoint, expected_status) covering all 32+ routers.
5. **Test exec() enforcement boundaries, not internals.** Fixture plugins that attempt escapes; assert the block.
6. **Mock all LLM backends at HTTP level with respx.** Test SSE structure, not token content.
7. **Explicitly set anyio backend in conftest.** Avoid event loop policy mismatch.
8. **Mock `$app/*` at vitest.config.ts level.** Global aliases, not per-test mocks.

#### 6. Pitfalls to Avoid

1. **Import-time side effects during collection** — triggers engine creation, DB connections. Override lifespan before first app import.
2. **Fire-and-forget tasks outliving tests** — four startup tasks write to DB after fixture teardown. Mock or cancel explicitly.
3. **Fixture scope mismatch** — session-scoped DB + function-scoped tests = data leaks. Most common "passes alone, fails in CI."
4. **Schemathesis blind on `dict` endpoints** — 19+ endpoints produce `{}` in OpenAPI. No security fuzz coverage. Supplement with explicit tests.
5. **SQLite vs Postgres semantic gaps** — current tests miss jsonb, arrays, CTEs. False greens likely.
6. **pytest-xdist with SQLite** — parallel workers share in-memory DB → deadlock. Each needs own temp path.
7. **Frontend jsdom limitations** — no matchMedia, IntersectionObserver. Must `await tick()` for reactive assertions. Default env is `node` not `jsdom`.

### Contradictions & Open Questions

1. **Transaction rollback vs truncation** — Settled: truncation is the only viable approach for this codebase.
2. **pytest-asyncio vs anyio** — Settled: use anyio exclusively (FastAPI recommendation).
3. **Cypress vs Playwright** — Open: existing Cypress works, Playwright is modern default. Not blocking for this session.
4. **CORS wildcard exploitability** — Open: browsers ignore credentials with literal `*`, but need to verify CORSMiddleware behavior.
5. **FILE_MAX_SIZE enforcement** — Open: needs runtime code path verification.
6. **Schemathesis + exec() paths** — Open: should schemathesis be explicitly blocked from routes reaching exec()?

### Implications for Design

**Natural domain decomposition:**

1. **Test Infrastructure & CI** — pytest config, markers, tier system, fixture architecture (truncation teardown, DI overrides, migration setup), CI pipeline. Cross-cutting enabler — must be done first.
2. **API Auth & Security** — JWT validation, role-based access matrix, rate limiting signals, CORS, CSRF, default-secret detection. Highest-priority domain.
3. **API Correctness (Router Tests)** — Endpoint contracts, error shapes, pagination, status codes for all 32 routers. Depends on infrastructure + auth fixtures.
4. **Model Layer** — CRUD operations, business logic, query correctness for 21 models. Partially independent.
5. **Frontend API Client** — ~30 fetch modules: error handling, auth headers, streaming. Pure TypeScript, independent of backend.
6. **Frontend XSS & Sanitization** — `{@html}` audit, DOMPurify bypass paths, SVG sanitization. Component-level.
7. **Migration Integrity** — Peewee+Alembic schema consistency, fresh deploy correctness. Standalone.

**Dependencies:**
- Infrastructure (1) unblocks all others
- Auth & Security (2) and Model Layer (4) share DB fixtures
- Router Tests (3) depends on Auth (2) + Model (4) for fixtures
- Frontend domains (5, 6) are independent of backend — can proceed in parallel
- Migration Integrity (7) is standalone

### Sources

Key references:
- FastAPI Testing: https://fastapi.tiangolo.com/tutorial/testing/
- FastAPI Async Tests: https://fastapi.tiangolo.com/advanced/async-tests/
- OWASP ASVS 4.0.3: https://owasp.org/www-project-application-security-verification-standard/
- OWASP File Upload Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
- OWASP JWT Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
- schemathesis: https://schemathesis.readthedocs.io/en/stable/
- respx: https://lundberg.github.io/respx/
- testcontainers-python: https://testcontainers-python.readthedocs.io/en/latest/
- pytest-postgresql: https://pytest-postgresql.readthedocs.io/
- factory_boy: https://factoryboy.readthedocs.io/en/stable/orms.html
- RestrictedPython: https://restrictedpython.readthedocs.io/en/latest/
- time-machine: https://github.com/adamchainz/time-machine
- MSW v2: https://mswjs.io/docs/
- @testing-library/svelte: https://testing-library.com/docs/svelte-testing-library/intro/
- anyio testing: https://anyio.readthedocs.io/en/stable/testing.html
