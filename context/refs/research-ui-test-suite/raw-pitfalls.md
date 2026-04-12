## Agent: pitfalls — Findings

### Q1: Adding Tests to Large Untested FastAPI Codebase

- **Import-time side effects** — engine creation, DB connections, signal handlers fire during pytest collection. Override lifespan or `app.dependency_overrides` before first app import.
- **`app` singleton global state** — multiple test files mutating `dependency_overrides` bleed into each other. Always use fixture with try/finally teardown.
- **Router import chains** — broken import anywhere in dependency graph surfaces as misleading collection error. Wave 1 confirms this exact pattern (missing selfai_ui.routers.webui).
- **Fixture scope mismatch** — session-scoped DB + function-scoped test = data leaks. Most common "pass alone, fail in CI" cause.
- **pytest-xdist with SQLite** — parallel workers share same in-memory DB path = deadlock/corruption. Each worker needs own temp path.
- **Confidence: High**

### Q2: Dual Session Pattern (scoped_session + sessionmaker) Pitfalls

- **"Wrong session sees the data"** — test inserts via SessionLocal, endpoint uses ScopedSession (different object). In async tests, insert may be invisible to endpoint.
- **scoped_session registry never reset** — without `Session.remove()` in teardown, next test gets same session with dirty/pending state.
- **Nested transaction trick breaks** — with two sessions both calling commit(), inner commit can't be rolled back. Dual-session = nested-transaction isolation DOESN'T WORK.
- **Dead `commit_session_after_request` middleware** — confuses debugging of data persistence issues.
- **SQLite in-memory + two connections** — each gets its own DB. Use `sqlite:///file::memory:?uri=true&cache=shared` or temp file.
- **Confidence: High**

**HIGH PRIORITY FLAG:** Standard transaction-rollback test isolation will NOT work with this codebase's dual sessions + Peewee autocommit. Must use explicit truncation-based teardown (DELETE FROM each table in dependency order). Design this into fixtures from the start.

### Q3: Asyncio Background Tasks in FastAPI Tests

- **Fire-and-forget tasks outlive tests** — loop closed while tasks pending → `Task was destroyed but it is pending!`. Task may write to DB after fixture teardown.
- **pytest-asyncio 0.21+ scope change** — default loop scope changed, session-scoped async fixtures run on different loop than test. App state (queues, locks) becomes invalid.
- **BackgroundTasks vs create_task** — TestClient runs BackgroundTasks synchronously; AsyncClient runs them async (may not complete before assertion). Mock the dispatcher instead.
- **lifespan + TestClient context manager** — cancellation of tasks holding DB connections → `InterfaceError: connection already closed`.
- **Event loop policy mismatch** — uvloop in prod vs asyncio in tests = behavior differences. Set policy explicitly in conftest.
- **Confidence: High**

### Q4: Hybrid Migration Systems (Peewee + Alembic)

- **Two sources of truth, no single "current" schema** — Alembic upgrade head misses Peewee-only columns. Peewee create_tables misses Alembic-managed tables.
- **create_all() bypasses migration hooks** — data migrations, defaults, column additions not applied. Causes alembic check drift.
- **Peewee + SQLAlchemy locking conflicts on SQLite** — both use own connection pools, simultaneous write lock → `database is locked`.
- **Schema drift is silent** — no Peewee equivalent of `alembic check`. Drift detected only at runtime query failure.
- **Transaction semantics differ** — Peewee autocommit vs SQLAlchemy explicit. Rolling back Peewee autocommitted writes impossible. Nested-transaction rollback completely unworkable for Peewee tables.
- **Confidence: High**

### Q5: SvelteKit/Svelte 4 First-Time Test Setup Gotchas

- **jsdom/happy-dom ≠ browser** — no matchMedia, IntersectionObserver, ResizeObserver. Store subscriptions to window events silently don't fire.
- **Missing vite-plugin-svelte in vitest config** — `.svelte` imports fail with `SyntaxError: Unexpected token '<'`. Most common first-time failure.
- **`$app/*` virtual modules fail without mocks** — `$app/navigation`, `$app/stores`, `$app/environment` throw at test time. Solve at vitest.config.ts level (aliases), not per-test.
- **Reactive `$:` statements async** — must `await tick()` before asserting DOM state after prop/store changes.
- **Component teardown leaks** — event listeners from onMount not properly cleaned if unmount() skips onDestroy.
- **Default vitest environment is `node`, not `jsdom`** — any component test fails with `document is not defined` without explicit config.
- **Confidence: High**

### Q6: Schemathesis/Fuzzing with Raw `dict` Parameters

- **No cases generated for untyped endpoints** — `body: dict` appears as `{}` in OpenAPI. Schemathesis generates empty or random objects, never exercises real field names.
- **422 treated as pass** — endpoint rejecting all fuzz input = "passing" all tests while logic is untested.
- **Security fuzzing is blind** — XSS/SQLi payloads only injected into declared fields. No fields = no security tests.
- **Stateful fuzzing breaks** — inconsistent response envelopes + no `links` objects = no lifecycle testing.
- **exec() reachable via fuzz** — Schemathesis payloads could reach exec() paths. Fuzzing must be blocked at routing layer before exec.
- **Background task pile-up** — rapid fuzz requests spawn hundreds of fire-and-forget tasks → memory pressure → timeout errors misread as app failures.
- **Confidence: High**
