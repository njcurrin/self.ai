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

### Iteration 7 — 2026-04-12
- **Task:** Tier 4 revisions (T-138–T-150) from /ck:check
- **Status:** DONE (13/14; T-151 L-sized dedup debug deferred)
- **Files:** api/main.py, api/run_pipeline.py, api/stage_registry.py, tests/run_tests.sh, 3x sub-package conftests, test_api_contract.py, test_pipeline_integration.py, test_pipeline_nodes.py
- **Fixes:**
  - P1: shell quoting in run_tests.sh; _poll_jobs_once helper + 4 real R13 tests
  - P2: orphan .tmp cleanup, custom stage class-name check, _dedup_cache cleanup, unsupported input extension, malformed JSONL, zero-match filter, portable conftests
  - P3: Parquet→JSONL IO case, record-count invariant, 400/422 detail-key expansion, concurrent companion test
- **Validation:** Full suite 265 passed / 6 skipped / 0 failures (was 250). Fast 242 / 1 skipped.
- **Next:** T-151 (dedup workflow debug) in a dedicated session, or move to self.UI

### Iteration 8 — 2026-04-12
- **Task:** T-151 dedup workflow debug
- **Status:** DONE — ExactDedup + MixedPipeline un-skipped and passing
- **Root cause:**
  1. `duplicate_id_field` was hardcoded to "id" in the removal workflow
     call. When assign_id=True, identification writes parquets with
     column `_curator_dedup_id` (not "id"). Upstream tests hand-crafted
     the ids files with an "id" column, which is why the default works
     for them but not for us.
  2. ids_to_remove_path was pointing at the dir containing both
     parquets AND the exact_id_generator.json. pandas.read_parquet
     scans every file and chokes on the JSON. Must point at
     {output_path}/ExactDuplicateIds/ subdir.
- **Files:** api/run_pipeline.py (run_exact_dedup + run_fuzzy_dedup), tests/pipeline/test_pipeline_integration.py
- **Validation:** 267 passed, 4 skipped, 0 failures. ExactDedup + MixedPipeline green. FuzzyDedup auto-skips on single-GPU hosts (NCCL requires multi-GPU).
- **Next:** Curator test suite complete. Move to self.UI (handled separately).
