---
created: "2026-04-11"
last_edited: "2026-04-12"
---

# Cavekit: Curator Test Infrastructure

## Scope

Test suite layout, shared fixtures, pytest configuration, migration of existing 125 node tests, and VRAM safety guards for the self.curator service. This kit covers the structural foundation that the API Contract and Pipeline Integration test kits depend on. All tests run inside the curator Docker container (CUDA 12.8.1, Ubuntu 24.04, Python 3.12, Ray, NeMo Curator).

## Requirements

### R1: Unified Test Layout

**Description:** The test suite uses a single `tests/` directory with clearly separated sub-packages. A single `pytest` invocation from the container working directory discovers and runs all tests.

**Acceptance Criteria:**
- [ ] `tests/nodes/` sub-package exists and contains node instantiation/behavior tests
- [ ] `tests/api/` sub-package exists and contains API contract tests (HTTP-level)
- [ ] `tests/pipeline/` sub-package exists and contains pipeline integration tests
- [ ] Each sub-package has an `__init__.py` file
- [ ] Running `pytest tests/` from the container root discovers tests in all three sub-packages
- [ ] Test files outside the three sub-packages are allowed ONLY if they validate the test-infra fixtures themselves (e.g., `tests/test_selfai_fixtures.py`). Conftest files and fixture validation are exempt.

**Dependencies:** None

### R2: Shared Fixtures

**Description:** A conftest hierarchy provides reusable fixtures across all test sub-packages: a FastAPI TestClient for HTTP tests, auto-cleaned temp workspace directories, a mock job state factory for lifecycle tests, and small fixture data files.

**Acceptance Criteria:**
- [ ] A root-level `tests/conftest.py` provides fixtures available to all sub-packages
- [ ] A `TestClient` fixture wraps the FastAPI `app` from `api/main.py` without starting a real server
- [ ] A temp workspace fixture creates an isolated directory tree matching the production layout (`configs/`, `data/`, `logs/`, `jobs/`, `custom_stages/`) and removes it after each test
- [ ] A job state factory fixture creates `CurationJob` instances with configurable status, timestamps, and paths, pre-populated in the app's `_jobs` dict
- [ ] JSONL fixture data file is checked in under `tests/fixtures/selfai/sample_data.jsonl` with fewer than 50 records and total size under 1 MB
- [ ] Parquet fixture data is generated on-demand by `tests/fixtures/selfai/generate_fixtures.py` (pyarrow is container-only, not available on host). The `run_tests.sh` CI entrypoint ensures regeneration before the suite runs. Total size under 1 MB.
- [ ] Fixture data files contain a `text` field with realistic multi-word string content (not empty strings or single characters)
- [ ] Sub-package conftest files use a PORTABLE import path for the `api/` directory — `Path(__file__).resolve().parents[2] / "api"` — NOT a hardcoded `/app/api`. Matches the portable pattern already in `selfai_conftest.py`. (Finding F-014.)
- [ ] The existing `shared_ray_cluster` session fixture from the upstream NeMo Curator conftest is preserved and available to integration tests

**Dependencies:** None

### R3: Pytest Markers

**Description:** Custom pytest markers allow selective test execution by resource requirement: fast tests (no Ray, no GPU), integration tests (needs Ray), and GPU tests (needs CUDA device).

**Acceptance Criteria:**
- [ ] Marker `fast` is registered in pytest config and applies to tests that need no Ray cluster and no GPU
- [ ] Marker `integration` is registered in pytest config and applies to tests that require a running Ray cluster
- [ ] Marker `gpu` is registered in pytest config and applies to tests that require a CUDA-capable GPU
- [ ] `pytest -m fast` runs only fast-marked tests, zero integration or gpu tests collected
- [ ] `pytest -m integration` runs only integration-marked tests
- [ ] `pytest -m gpu` runs only gpu-marked tests
- [ ] `pytest -m "not gpu"` excludes all gpu-marked tests
- [ ] All existing node tests from the migrated file are marked `fast`

**Dependencies:** R1

### R4: VRAM Guard

**Description:** A fixture or utility that checks available GPU memory before gpu-marked tests execute, auto-skipping if free VRAM is below a configurable threshold. Prevents OOM crashes on the 24 GB system when other processes consume GPU memory.

**Acceptance Criteria:**
- [ ] A mechanism exists that queries current free GPU memory before each `gpu`-marked test
- [ ] If free VRAM is below a configurable threshold (default: 4 GB), the test is skipped with a descriptive message stating required vs. available VRAM
- [ ] The threshold is overridable via environment variable or pytest option
- [ ] The VRAM check itself does not fail or raise if no GPU is present (it returns 0 available)
- [ ] Tests marked only with `fast` or `integration` (no `gpu` marker) are never subject to VRAM checks

**Dependencies:** R3

### R5: Node Test Migration

**Description:** The existing 125 tests from `tests/api/test_pipeline_nodes.py` are audited for correctness and migrated to the `tests/nodes/` sub-package. Working tests are preserved as-is. Tests that contain bugs (e.g., incorrect assertions, missing edge cases) are fixed. The original file at `tests/api/test_pipeline_nodes.py` is removed after migration.

**Acceptance Criteria:**
- [ ] All 125 existing test cases are present in `tests/nodes/` (same test names, same assertions unless a fix was needed)
- [ ] The original `tests/api/test_pipeline_nodes.py` no longer exists
- [ ] Any test that was modified has a code comment explaining what was fixed and why
- [ ] All migrated tests pass when run with `pytest tests/nodes/ -m fast`
- [ ] Registry coverage is verified: every key in `_FILTER_CLASS_REGISTRY`, `_MODIFIER_CLASS_REGISTRY`, and `_CLASSIFIER_CLASS_REGISTRY` has at least one test in `tests/nodes/`
- [ ] If any registry key lacks test coverage, a new test is added that at minimum instantiates the stage with default parameters

**Dependencies:** R1, R3

### R6: CI Entrypoint

**Description:** A shell script or Makefile target that runs the full test suite inside the curator container. The marker selection is configurable via environment variable so CI pipelines can run subsets.

**Acceptance Criteria:**
- [ ] An entrypoint script exists at a documented path within the self.curator repo
- [ ] Running the script with no arguments executes `pytest tests/` (all tests)
- [ ] Setting `TEST_MARKERS` environment variable (e.g., `TEST_MARKERS=fast`) passes the value as `-m` to pytest
- [ ] The script exits with a nonzero code if any test fails
- [ ] The script produces JUnit XML output to a predictable path for CI consumption
- [ ] The script can be invoked from a `docker compose exec` or `docker exec` command from the host

**Dependencies:** R1, R3

## Out of Scope

- Writing test implementations (this kit specifies structure and acceptance criteria only)
- NeMo Curator's own upstream test suite (`tests/stages/`, `tests/core/`, etc.) -- those are NVIDIA's responsibility
- Performance benchmarking or load testing
- Test coverage percentage targets beyond the explicit registry coverage in R5
- Docker image build configuration (assumes the existing curator container)
- IDE or editor integration for test running

## Cross-References

- See also: `cavekit-curator-api-contract.md` -- depends on TestClient and job state factory fixtures from R2
- See also: `cavekit-curator-pipeline-integration.md` -- depends on fixture data, markers, and VRAM guard from R2/R3/R4
- See also: `cavekit-curator-test-overview.md` -- master index

## Changes

- 2026-04-12: R1 AC6 relaxed — `tests/test_selfai_fixtures.py` (fixture validation) allowed at root, not a violation (finding: stray test file).
- 2026-04-12: R2 AC6/7 updated — Parquet fixture is lazily generated (pyarrow container-only); CI script regenerates before runs. Added AC8 requiring portable sys.path setup in sub-package conftests (finding F-014).
