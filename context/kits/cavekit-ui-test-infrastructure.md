---
created: "2026-04-11"
last_edited: "2026-04-12"
---

# Cavekit: UI Test Infrastructure

## Scope

Test infrastructure setup for the self.UI backend (FastAPI) and frontend (SvelteKit 2). This kit covers pytest configuration, shared fixtures, model factories, external service mocking, frontend test tooling, CI pipeline integration, and startup task isolation. It is the structural enabler for all downstream test domains. No dependency on the security fix kits -- can be built in parallel.

Source analysis: `context/refs/research-brief-ui-test-suite.md` Sections 1, 3, 4, 5, 6.

## Requirements

### R1: Pytest Configuration

**Description:** The backend test runner must have explicit configuration defining test paths, custom markers, timeout defaults, and async backend settings. This replaces the current state where no `pytest.ini` or `[tool.pytest.ini_options]` exists.

**Acceptance Criteria:**
- [ ] pytest configuration exists (in `pyproject.toml` or equivalent) with `testpaths` pointing to the backend test directory
- [ ] Custom markers are registered: `tier0`, `tier1`, `tier2`, `security`, `slow`, `gpu`
- [ ] Strict marker mode is enabled (unregistered markers cause errors)
- [ ] Async test backend is configured for anyio (not pytest-asyncio)
- [ ] A default test timeout is set (between 30 and 120 seconds)
- [ ] Running `pytest --collect-only` from the backend directory discovers tests without warnings about unknown markers
- [ ] Running `pytest -m tier0` collects only tier0-marked tests
- [ ] Running `pytest -m security` collects only security-marked tests

**Dependencies:** None

### R2: Backend Test Fixtures (Truncation-Based)

**Description:** A conftest.py architecture providing shared fixtures for all backend tests. Uses `app.dependency_overrides` for dependency injection (not monkey-patching). Uses truncation-based teardown (DELETE FROM tables in dependency order) because the dual Peewee+SQLAlchemy session architecture makes transaction rollback unworkable.

**Acceptance Criteria:**
- [ ] A root-level conftest.py provides fixtures available to all backend test sub-packages
- [ ] A `test_app` fixture provides an HTTP test client connected to the FastAPI application without starting a real server
- [ ] Database dependencies are overridden via `app.dependency_overrides`, not by patching module-level imports
- [ ] Both Peewee and Alembic migrations run during test session setup, producing a complete schema
- [ ] After each test function, all user-created data is removed via truncation (DELETE) in foreign-key-safe order
- [ ] An `authenticated_user` fixture provides a test client pre-configured with a valid user-role session token
- [ ] An `authenticated_admin` fixture provides a test client pre-configured with a valid admin-role session token
- [ ] A `db_session` fixture provides direct database session access for tests that need to arrange data or assert DB state
- [ ] Two tests that write to the same table and run sequentially do not observe each other's data
- [ ] Fixtures do not rely on `metadata.create_all()` as the sole schema source (Peewee-only columns must be present)

**Dependencies:** None

### R3: Model Factories

**Description:** Reusable factory definitions for core data models, replacing hand-rolled `_make_*()` helpers. Each factory produces valid model instances with sensible defaults and supports trait-based customization.

**Acceptance Criteria:**
- [ ] Factories exist for: User, Auth, Chat, File, Knowledge, Tool, Function, TrainingJob, EvalJob, CuratorJob, JobWindow
- [ ] Each factory produces a valid, persistable instance when called with no arguments
- [ ] Factory-generated instances have unique identifiers (no collisions across multiple calls)
- [ ] Factories support overriding any field via keyword arguments
- [ ] Factories are importable from a single module (not scattered across test files)
- [ ] The existing `_make_*()` helper functions in current test files can be replaced by factory calls without changing test semantics

**Dependencies:** R2

### R4: External Service Mocking

**Description:** Fixtures for mocking outbound HTTP calls to external services at the transport level. Prevents tests from making real network requests and provides configurable response scenarios.

**Acceptance Criteria:**
- [ ] A mock fixture exists for each external service: Ollama, OpenAI, Llamolotl, Curator, eval harness
- [ ] Each mock intercepts outbound HTTP requests to the service's configured base URL
- [ ] Each mock supports configurable response scenarios: success, error (4xx/5xx), and timeout
- [ ] Mocks for streaming endpoints return well-formed streaming responses (SSE or chunked)
- [ ] Tests using these mocks make zero real network requests (verified by the mock asserting no unmatched requests leak through)
- [ ] Mocks are composable: a single test can activate mocks for multiple services simultaneously

**Dependencies:** R2

### R5: Frontend Test Configuration

**Description:** The frontend test runner must be configured with the correct environment, module aliases, and testing library dependencies. Currently vitest is installed but configured to pass with no tests and no testing libraries are present.

**Acceptance Criteria:**
- [ ] A vitest configuration file exists with the Svelte plugin and a DOM environment (jsdom or equivalent)
- [ ] Module aliases for `$app/*`, `$lib/*`, and other SvelteKit path aliases resolve correctly in tests
- [ ] A setup file provides DOM testing matchers (e.g., custom matchers for DOM assertions)
- [ ] `@testing-library/svelte` (v4+), `@testing-library/jest-dom`, and a network-level request mocking library are listed as dev dependencies
- [ ] Running the frontend test command discovers and runs test files under the `src/` directory
- [ ] A sample smoke test (e.g., rendering a simple component) passes, confirming the toolchain works end-to-end

**Dependencies:** None

### R6: CI Pipeline

**Description:** The existing commented-out pytest job in the integration test workflow must be activated and updated. A frontend test job must be added alongside it. Test failures must block the build.

**Acceptance Criteria:**
- [ ] The backend pytest job in the CI workflow is uncommented and functional
- [ ] The backend job runs `tier0` and `tier1` marked tests on every pull request
- [ ] A frontend test job exists in the CI workflow and runs vitest on every pull request
- [ ] Both jobs fail the overall CI check if any test fails
- [ ] The backend job produces test result output consumable by the CI platform (JUnit XML or equivalent)
- [ ] The frontend job produces test result output consumable by the CI platform
- [ ] Both jobs run in the existing CI environment without requiring additional infrastructure

**Dependencies:** R1, R5

### R7: Startup Task Isolation

**Description:** The application starts four fire-and-forget async tasks at startup (usage pool cleanup, crawl resume, GPU queue daemon, curator classifier health check). These tasks must be prevented from running during tests to avoid writing to the database after fixture teardown and interfering with test isolation.

**Acceptance Criteria:**
- [ ] A fixture or test configuration mechanism prevents all four startup tasks from executing during test runs
- [ ] The prevention mechanism does not require modifying production code paths (uses overrides, mocking, or lifespan control)
- [ ] Tests that specifically need to test a startup task's behavior can opt in to running that task in isolation
- [ ] No warnings or errors are logged about cancelled tasks during normal test execution
- [ ] Database state is not modified by background tasks after test teardown completes

**Dependencies:** R2

## Out of Scope

- Actual test case implementations (those belong in domain-specific test kits like `cavekit-ui-security-tests.md`)
- Frontend component test cases (infrastructure only, not the tests themselves)
- End-to-end browser tests (Cypress/Playwright configuration is a separate concern)
- Performance or load testing infrastructure
- Test coverage percentage targets or enforcement
- Docker image changes for the test environment
- Database choice for test execution (SQLite vs Postgres -- implementation decision)

## Cross-References

- See also: `cavekit-ui-security-tests.md` -- depends on R1 (markers), R2 (fixtures), R3 (factories), R4 (mocks), R7 (task isolation)
- See also: `cavekit-ui-security-quick-fixes.md` -- independent, can be built in parallel
- See also: `cavekit-ui-security-hardening.md` -- independent, can be built in parallel
- See also: `cavekit-ui-security-overview.md` -- master index
- Source: `context/refs/research-brief-ui-test-suite.md` -- Sections 1 (Current State), 3 (Architecture), 4 (Libraries), 5 (Best Practices), 6 (Pitfalls)

### R8: Pytest marker registration and strict warnings

**Description:** Every custom marker used by tests (tier0, tier1, tier2, slow, integration, etc.) must be registered in a pytest configuration file, and unknown-marker warnings must be promoted to errors. A typo in `@pytest.mark.<name>` currently produces a silent warning that the suite ignores — this defeats the tier system and allows dead decorators to accumulate.

**Acceptance Criteria:**
- [ ] A `pytest.ini`, `pyproject.toml [tool.pytest.ini_options]`, or equivalent lists every marker used in the suite with a one-line description
- [ ] `filterwarnings = error::pytest.PytestUnknownMarkWarning` (or equivalent) is set so unknown markers fail the run
- [ ] A typo in `@pytest.mark.tier0o` fails the suite rather than emitting a warning
- [ ] Running `pytest --markers` prints every marker the suite uses
- [ ] The existing 218+ `PytestUnknownMarkWarning` warnings per run are reduced to zero

**Dependencies:** None (infrastructure)
**Source:** Finding F-007 from `/ck:check` on 2026-04-12.

## Changelog
- 2026-04-12: Added R8 (Pytest marker registration and strict warnings) — discovered during `/ck:check`. The suite produces ~218 unknown-marker warnings per run because markers are used but never registered; a typo would be invisible.
