---
created: "2026-04-11"
last_edited: "2026-04-12"
---
# Implementation Tracking: Curator Test Suite

Build site: context/plans/build-site-curator-tests.md

## Status Summary

**Tier 0:** 4/4 complete
**Tier 1:** 4/4 complete
**Tier 2 (fast):** 21/28 tests complete (API contract + fast pipeline)
**Tier 2 (integration/gpu):** 0/10 — deferred (Ray-dependent)
**Tier 3:** 0/2

**Test results:** 218 passed, 1 skipped, 9 xfailed, 2 xpassed

## Task-by-task

| Task | Status | Notes |
|------|--------|-------|
| T-100 | DONE | tests/nodes/, tests/pipeline/ sub-packages with __init__.py |
| T-101 | DONE | selfai_conftest.py fixtures — TestClient, temp_workspace, job_factory. Patches both main.py and stage_registry.py paths. |
| T-102 | DONE | 30-record JSONL + Parquet fixtures. generate_fixtures.py for in-container generation. |
| T-103 | DONE | Verified upstream conftest.py shared_ray_cluster untouched |
| T-104 | DONE | pytest.ini with fast/integration/gpu markers. Marker filtering verified. |
| T-105 | DONE | VRAM guard auto-skips gpu tests below 4GB threshold (VRAM_THRESHOLD env var) |
| T-106 | DONE | 125 node tests migrated to tests/nodes/, all marked fast, 100% registry coverage |
| T-107 | DONE | run_tests.sh CI entrypoint. TEST_MARKERS env var. JUnit XML at tests/results/junit.xml |
| T-108 | DONE | Health endpoint (9 tests) |
| T-109 | DONE | Stage discovery counts (9 tests). NOTE: real API exposes 37 ProcessingStage classes across 7 categories, NOT run_pipeline wrapper registries. |
| T-110 | DONE | Stage detail schema + 404s (5 tests) |
| T-111 | DONE | Custom stage CRUD (7 tests, ALL xfail) — BUG: save_custom_stage() circular dependency |
| T-112 | DONE | Custom stage validation (7 tests, 1 xfail for duplicate_builtin) |
| T-113 | DONE | Job creation (8 tests) |
| T-114 | DONE | Job listing + get/404 (3 tests) |
| T-115 | DONE | Valid state transitions (7 tests) |
| T-116 | DONE | Invalid state transitions (6 tests) |
| T-117 | DONE | BUG: output_format config persistence (3 tests documenting current broken behavior) |
| T-118 | DONE | BUG: Approve failure state (4 tests) |
| T-119 | DONE | BEHAVIOR: Scheduled non-auto-start (2 tests) |
| T-120 | DONE | Job logs (6 tests, 1 skipped — stream test: TestClient limitation) |
| T-121 | DONE | Error response contract (5 tests) |
| T-122 | DONE | Concurrent state safety (3 tests, xfail) — BUG: _save_jobs() race condition |
| T-123 | DONE | Config round-trip (5 tests) |
| T-124 | DONE | Stage registry completeness (8 tests) |
| T-125 | DONE | Stage registry detail (2 tests; consolidated to API-exposed stages) |
| T-126 | PENDING | Streaming pipeline (integration — needs Ray) |
| T-127 | DONE | BUG: text_field propagation (2 tests; 1 xfail) |
| T-128 | PENDING | ExactDedup (integration) |
| T-129 | PENDING | FuzzyDedup (integration + gpu) |
| T-130 | PENDING | Mixed pipeline (integration) |
| T-131 | PENDING | IO format matrix (integration) |
| T-132 | DONE | Error paths (2 fast tests) |
| T-133 | PENDING | Error paths edge (integration) |
| T-134 | DONE | Resource safety static (1 test) |
| T-135 | PENDING | Resource safety processes (integration) |
| T-136 | PENDING | Cross-cutting validation |
| T-137 | PENDING | Full suite dry-run |

## Bugs Discovered by Tests

### Bug #1: save_custom_stage() circular dependency (NEW — tests surfaced)

**Location:** `api/stage_registry.py:321-355`
**Problem:** `save_custom_stage` calls `_load_custom_stage_class(stage_uuid)` BEFORE
adding the entry to the index. `_load_custom_stage_class` requires the uuid to
exist in the index (line 258-261: `if not entry: return None`). As a result,
every custom stage create fails with "Code must define exactly one concrete
ProcessingStage subclass".

**Impact:** Custom stages API is completely non-functional. UI can't create custom stages.

**Fix:** Either (a) pre-populate a placeholder index entry before validation, or
(b) rewrite `_load_custom_stage_class` to accept filepath directly for validation.

### Bug #2: _save_jobs() race condition (NEW — tests surfaced)

**Location:** `api/main.py:158-163`
**Problem:** `_save_jobs()` writes to a shared `.tmp` file
(`JOBS_STATE_FILE.with_suffix('.tmp')`) then calls `tmp.replace(STATE_FILE)`.
Two concurrent threads race: Thread A writes .tmp → Thread B writes .tmp →
Thread A renames .tmp to jobs.json → Thread B FileNotFoundError on rename.

**Impact:** Under concurrent job creation (e.g., via the GPU queue daemon
batching dispatches), jobs.json writes can fail intermittently, potentially
losing job state.

**Fix:** Use a per-call unique tmp filename (e.g., `f"{STATE_FILE}.{pid}.{threadid}.tmp"`)
or wrap `_save_jobs()` with a `threading.Lock`.

### Bug #3: output_format not persisted to config JSON (pre-existing, spec'd)

**Location:** `api/main.py:416-424`
**Problem:** The config dict written to disk in `create_job()` omits
`output_format`. `run_pipeline.py` reads the config and falls back to "jsonl"
when the key is missing.

**Impact:** Users requesting Parquet output get JSONL regardless.

**Fix:** Add `"output_format": req.output_format` to the config dict at main.py:422.

## UI-Side Flags (deferred)

- `validate-name` endpoint has no proxy route in self.UI
- GPU queue daemon assumes approve always succeeds
- `_finalize_curator_job()` has no retry on Knowledge creation failure

## Next Steps

1. Run integration/gpu tests (T-126, T-128, T-130, T-131, T-133, T-135) —
   requires Ray cluster, will take longer
2. T-136/T-137 — cross-cutting validation
3. Fix the 3 bugs discovered (can now be reproduced via tests)
