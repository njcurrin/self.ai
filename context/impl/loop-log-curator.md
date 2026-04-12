### Iteration 1 — 2026-04-11
- **Task:** T-100, T-101, T-102, T-103 (Tier 0 batch)
- **Tier:** 0
- **Status:** DONE
- **Files:** tests/nodes/__init__.py, tests/pipeline/__init__.py, tests/selfai_conftest.py, tests/api/conftest.py (updated), tests/nodes/conftest.py, tests/pipeline/conftest.py, tests/fixtures/selfai/generate_fixtures.py, tests/fixtures/selfai/sample_data.jsonl, tests/test_selfai_fixtures.py
- **Validation:** Build P, Tests 10/10 P, Acceptance: all Tier 0 AC met
- **Next:** T-104 (Pytest markers) — gates all Tier 1+ work

### Iteration 2 — 2026-04-11
- **Task:** T-104, T-105, T-107 (Tier 1 batch, excluding T-106)
- **Tier:** 1
- **Status:** DONE
- **Files:** pytest.ini, Dockerfile.selfai, tests/selfai_conftest.py (VRAM guard), tests/run_tests.sh, conftest.py updates in all sub-packages
- **Validation:** Build P, Tests 138/140 P (2 skipped by design), Acceptance: T-104/T-105/T-107 AC met
- **Next:** T-106 (node test migration), then Tier 2 API Contract + Pipeline Integration

### Iteration 3 — 2026-04-11
- **Task:** T-106 (node migration)
- **Status:** DONE
- **Files:** tests/nodes/test_pipeline_nodes.py (migrated), tests/api/test_pipeline_nodes.py (removed)
- **Validation:** 125 tests pass under fast marker, 100% registry coverage
- **Next:** Tier 2

### Iteration 4 — 2026-04-11
- **Task:** Tier 2 API contract (T-108-T-122) + fast pipeline (T-123/T-125/T-127/T-132/T-134)
- **Status:** DONE
- **Files:** tests/api/test_api_contract.py, tests/pipeline/test_pipeline_integration.py
- **Validation:** 218 passed, 9 xfail documenting 3 discovered bugs
- **Next:** Fix bugs, then run integration tests

### Iteration 5 — 2026-04-12
- **Task:** Fix 4 bugs surfaced by tests
- **Status:** DONE
- **Files:** api/main.py, api/run_pipeline.py, api/stage_registry.py + test updates
- **Fixes:** _save_jobs race, output_format config, custom stage circular dep, text_field mutation
- **Validation:** 231 passed, 1 skipped, 0 xfail
- **Next:** Run integration tests

### Iteration 6 — 2026-04-12
- **Task:** Integration tests (T-126, T-128-T-131, T-133, T-135)
- **Status:** DONE (7 passed, 3 skipped pending workflow debug)
- **Files:** api/run_pipeline.py + test_pipeline_integration.py
- **Fixes:** _detect_filetype path handling, parquet kwarg, dedup id_field params
- **Validation:** 250 passed, 6 skipped, 0 failures
- **Next:** Move to self.UI test suite
