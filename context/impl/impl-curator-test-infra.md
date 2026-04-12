---
created: "2026-04-11"
last_edited: "2026-04-12"
---
# Implementation Tracking: Curator Test Suite

Build site: context/plans/build-site-curator-tests.md

## Status Summary

**Tier 0:** 4/4 complete
**Tier 1:** 4/4 complete
**Tier 2:** 25/28 tasks effectively complete; 3 dedup classes (T-128/T-129/T-130) BLOCKED pending NeMo Curator workflow debug
**Tier 3:** effective coverage via run_tests.sh dry-run
**Tier 4:** 14/14 complete (T-138–T-151). T-151 surfaced two additional real bugs in the dedup workflow wrapper.

**Test results:** 267 passed, 4 skipped, 0 xfail, 0 failures (was 250 pre-revision → 265 after T-138–T-150 → 267 after T-151)
**Fast subset:** 242 passed, 1 skipped

**Bugs fixed:** 9 total discovered-and-fixed by this test suite.
- Bug #1–#4 (original loop): save_jobs race, output_format drop, custom stage cycle, params mutation
- Bug #5–#7 (first integration run): _detect_filetype file-path, parquet kwarg, dedup id_field (partial)
- Bug #8 (T-151): duplicate_id_field in removal workflow should match identification's id_field (was "id", must be "_curator_dedup_id" when assign_id=True)
- Bug #9 (T-151): ids_to_remove_path was pointing at the directory containing both parquets AND exact_id_generator.json; must point at the parquet-only subdirectory ({output_path}/ExactDuplicateIds/)

All /ck:check P1 findings closed. P2/P3 findings closed except F-008 (TestClient thread-safety — low priority, deferred), F-011 (shallow dict copy — latent, acceptable for current stages), F-012 (empty stages list — spec gap, deferred).

**Skip inventory:** 4 legitimate skips:
- Stream log test (TestClient can't terminate infinite loop; route verified via OpenAPI)
- FuzzyDedup (NCCL multi-GPU required; 24GB single-GPU host can't run it)
- 2 integration fixtures marked gpu, auto-skipped by VRAM guard

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
| T-126 | DONE | Streaming pipeline — JSONL through filter + modifier + writer |
| T-127 | DONE | BUG: text_field propagation FIXED — build_pipeline now copies params dict |
| T-128 | DONE | ExactDedup — un-skipped and passing end-to-end (T-151 fixed two workflow wrapper bugs) |
| T-129 | DONE (env-gated) | FuzzyDedup — workflow wrapper verified same code path as ExactDedup; end-to-end test skipped pending multi-GPU host (NCCL required) |
| T-130 | DONE | Mixed pipeline — un-skipped and passing end-to-end |
| T-131 | DONE | IO format matrix — 4x format combos + text_field preserved |
| T-132 | DONE | Error paths (2 fast tests) |
| T-133 | DONE | Error paths edge — nonzero exit on invalid input |
| T-134 | DONE | Resource safety static — fixtures under 1MB |
| T-135 | DONE | Resource safety processes — subprocess timeout |
| T-136 | DONE | Cross-cutting validation — full suite run via run_tests.sh |
| T-137 | DONE | Full suite dry-run — 250 passed, 6 skipped |

## Bugs Discovered and Fixed by Tests

Seven bugs total — all discovered by the test suite, all fixed. Summary:

| # | Component | Status |
|---|-----------|--------|
| 1 | `_save_jobs()` race condition | FIXED |
| 2 | `output_format` dropped in config JSON | FIXED |
| 3 | `save_custom_stage()` circular dependency | FIXED |
| 4 | `build_pipeline()` mutates caller's config | FIXED |
| 5 | `_detect_filetype()` only checked directories | FIXED |
| 6 | Parquet reader wrong FilePartitioningStage kwarg | FIXED |
| 7 | Dedup missing id_field / duplicate_id_field params | PARTIALLY FIXED (deeper workflow issue remains) |

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

1. **Dedup workflow debug** — ExactDedup/FuzzyDedup/MixedPipeline tests are
   skipped pending investigation of TextDuplicatesRemovalWorkflow phase-B
   field-mismatch error ("No match for FieldRef.Name(id)"). This is likely
   a deeper issue in how self.curator wraps the NeMo Curator dedup
   workflows — needs a dedicated debug pass comparing upstream test
   patterns with our invocation.
2. **Move to self.UI** — curator test suite is now solid enough to support
   confident curator refactors. Testing focus shifts to self.UI.
