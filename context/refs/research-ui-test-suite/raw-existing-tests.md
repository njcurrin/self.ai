## Agent: codebase-existing-tests — Findings

### Test File Inventory

**backend/tests/ (custom self.AI model/utility tests):**
- `conftest.py` — SQLite in-memory `db_session` fixture, patches `get_db` in 5 modules
- `test_benchmark_config.py` — 9 tests, BenchmarkConfigs model CRUD
- `test_curator_jobs.py` — 15 tests, CuratorJobs model, priority, status, ordering
- `test_gpu_queue.py` — 14 tests, dispatch logic, priority ordering, window fitting
- `test_job_windows.py` — 14 tests, JobWindows CRUD, status logic, slots

**selfai_ui/test/ (legacy integration tests from fork):**
- `apps/webui/routers/test_auths.py` — 9 tests, auth endpoints
- `apps/webui/routers/test_chats.py` — 14 tests, chat CRUD
- `apps/webui/routers/test_models.py` — 1 combined workflow test
- `apps/webui/routers/test_prompts.py` — 1 combined workflow test
- `apps/webui/routers/test_users.py` — 1 combined workflow test
- `retrieval/test_firecrawl_403.py` — 7 tests, SafeFirecrawlLoader 403 cancellation
- `retrieval/test_firecrawl_crawl_options.py` — 9 tests, crawl option handling

### Critical Issues

1. **Router integration tests are BROKEN**: `mock_user.py:8` imports `from selfai_ui.routers.webui import app` — this module doesn't exist. Was refactored into `main.py`.
2. **Missing `__init__.py`** in `test/apps/`, `test/apps/webui/`, `test/apps/webui/routers/`
3. **Pytest job in CI is commented out** — no backend tests run in CI at all
4. **No pytest configuration** — no `[tool.pytest.ini_options]`, no markers, no testpaths

### Coverage Summary

**Tested models:** benchmark_config, curator_jobs, job_windows, eval_jobs (indirect), training (indirect)
**Tested utilities:** gpu_queue dispatch logic, SafeFirecrawlLoader
**Completely untested routers (28):** audio, benchmarks, bigcode_eval, channels, configs, curator, evaluations, files, folders, functions, groups, images, knowledge, llamolotl, lm_eval, memories, ollama, openai, pipelines, queue, retrieval, system, tasks, tools, training, windows, utils
**Completely untested models (11):** channels, feedbacks, files, folders, functions, groups, knowledge, memories, messages, tags, tools

### Frontend Testing

- `vitest ^1.6.0` installed, script uses `--passWithNoTests` — zero test files exist
- `cypress ^13.15.0` with 4 E2E files: registration, chat, documents, settings
- **No component tests, no store tests, no API client tests**
- `@testing-library/svelte` not installed

### CI Status

- `integration-test.yml`: Cypress E2E + migration smoke test only
- **pytest job block is commented out**
- `format-backend.yaml`: black check only
- `format-build-frontend.yaml`: build check only
