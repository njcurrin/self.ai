---
created: "2026-04-11"
last_edited: "2026-04-12"
---

# Cavekit: Curator Pipeline Integration Testing

## Scope

End-to-end tests for `run_pipeline.py` and `stage_registry.py` with real NeMo Curator library code. Config serialization round-trip. Stage registry completeness. Streaming pipelines with small datasets. Deduplication workflows. IO format matrix. Error paths. All tests respect the 24 GB VRAM budget and use datasets under 1 MB.

These tests exercise the actual NeMo Curator pipeline machinery (readers, filters, modifiers, writers, dedup workflows) but use minimal data to keep execution fast and memory-safe.

## Requirements

### R1: Config Round-Trip

**Description:** A job config JSON file produced by the API contains every field from the original request, and `run_pipeline.py`'s `build_pipeline()` correctly consumes that config to produce the expected pipeline stages. No fields are silently dropped during serialization.

**Acceptance Criteria:**
- [ ] A config JSON file containing `name`, `input_path`, `output_path`, `text_field`, `stages`, and `output_format` is correctly parsed by `build_pipeline()`
- [ ] The `output_format` field in the config controls which writer stage is added (`JsonlWriter` for `"jsonl"`, `ParquetWriter` for `"parquet"`)
- [ ] If `output_format` is omitted or null in the config, `build_pipeline()` defaults to `"jsonl"` writer
- [ ] Stage params from the config JSON are passed to stage constructors with correct types (strings remain strings, ints remain ints, bools remain bools)
- [ ] A config with 3+ stages produces a pipeline with the correct number of processing stages (plus reader and writer)

**Dependencies:** cavekit-curator-test-infra R2 (fixture data, temp workspace), cavekit-curator-test-infra R3 (markers)
**Cross-reference:** cavekit-curator-api-contract R6 (output_format Config Persistence) validates the upstream producer of this config

### R2: Stage Registry Completeness

**Description:** The stage registry correctly discovers and catalogs all built-in NeMo Curator text stages. Every registered stage can be instantiated with default parameters.

**Acceptance Criteria:**
- [ ] `_load_text_stages()` executes without errors
- [ ] `get_text_stages_by_category()` returns a dict with at least the categories: `filters`, `modifiers`, `classifiers`
- [ ] The total number of stages across `_FILTER_CLASS_REGISTRY` (35), `_MODIFIER_CLASS_REGISTRY` (9), and `_CLASSIFIER_CLASS_REGISTRY` (8) matches the actual registry sizes
- [ ] Every class in `_FILTER_CLASS_REGISTRY` can be instantiated (some may require minimal valid params rather than bare defaults)
- [ ] Every class in `_MODIFIER_CLASS_REGISTRY` can be instantiated
- [ ] Every class in `_CLASSIFIER_CLASS_REGISTRY` can be instantiated (GPU classifiers may need to be instantiation-only, not execution)
- [ ] `FastTextQualityFilter` and `FastTextLangId` raise a clear error or skip gracefully when the required FastText model file is not present on disk
- [ ] `get_text_stage_detail()` returns a non-None result for every key in all three registries
- [ ] The fallback path in `build_pipeline()` (looking up `_STAGE_REGISTRY` when a type is not in the three class registries) is exercised and returns a valid stage instance

**Dependencies:** cavekit-curator-test-infra R3 (markers -- these are `fast` tests, no Ray needed for instantiation)

### R3: Streaming Pipeline

**Description:** A small dataset passes through a multi-stage streaming pipeline (reader, filter, modifier, writer) and produces correct output.

**Acceptance Criteria:**
- [ ] A JSONL input file with 10-50 records is processed through at least one filter stage and one modifier stage
- [ ] Output is written as valid JSONL with one JSON object per line
- [ ] Output records contain the expected `text` field
- [ ] Filter stages reduce record count (some records are removed based on filter criteria)
- [ ] Modifier stages transform text content (output text differs from input text for affected records)
- [ ] Multi-stage pipelines preserve record integrity: no records are duplicated, no fields are dropped
- [ ] The pipeline completes with exit code 0 when invoked via `run_pipeline.py`

**Dependencies:** cavekit-curator-test-infra R2 (fixture data, temp workspace), cavekit-curator-test-infra R3 (`integration` marker)

### R4: BUG -- text_field Propagation

**Description:** The `build_pipeline()` function in `run_pipeline.py` must not mutate the stage params dict. Currently, the modifier branch uses `stage_params.pop('text_field', 'text')` (line ~224), which removes `text_field` from the shared params dict. If the same params dict is reused or inspected later, the field is silently missing.

**Acceptance Criteria:**
- [ ] Calling `build_pipeline()` with a config containing multiple modifier stages does not raise a KeyError or produce incorrect behavior on the second modifier
- [ ] After `build_pipeline()` returns, the original config dict's stage params are unmodified (same keys and values as before the call)
- [ ] `text_field` is correctly passed to each modifier's `Modify(input_fields=...)` wrapper without being consumed from the params dict
- [ ] A pipeline with two modifiers that both specify `text_field: "content"` correctly applies both modifiers to the `"content"` field

**Dependencies:** cavekit-curator-test-infra R2 (fixture data, temp workspace), cavekit-curator-test-infra R3 (markers)

### R5: ExactDedup (DEFERRED — upstream workflow integration issue)

**Status:** DEFERRED. Tests are class-level `@pytest.mark.skip`-ed. NeMo
Curator's `TextDuplicatesRemovalWorkflow` phase-B fails with
"No match for FieldRef.Name(id)" against the phase-A output schema
even with `id_field=_curator_dedup_id` + `duplicate_id_field=id`
(the upstream defaults). The self.curator wrapper in
`api/run_pipeline.py:run_exact_dedup` is likely missing `input_fields`
or a similar param. This needs a dedicated NeMo Curator workflow debug
pass outside the contract-test scope.

**Description:** The exact deduplication workflow identifies and removes duplicate records from a small dataset.

**Acceptance Criteria:**
- [ ] A dataset with known exact-duplicate records (identical `text` values) is processed by `run_exact_dedup()`
- [ ] Output contains fewer records than input (duplicates removed)
- [ ] All unique records from the input are present in the output
- [ ] No records that were unique in the input are removed
- [ ] The two-phase workflow (ID identification, then removal) completes without error
- [ ] Output files are written to the specified output path

**Dependencies:** cavekit-curator-test-infra R2 (fixture data, temp workspace), cavekit-curator-test-infra R3 (`integration` marker), cavekit-curator-test-infra R4 (VRAM guard -- dedup may use GPU acceleration)

### R6: FuzzyDedup (DEFERRED — same upstream workflow issue as R5)

**Status:** DEFERRED. Shares the `TextDuplicatesRemovalWorkflow`
phase-B issue with R5. Also gated on `cudf` availability.

**Description:** The fuzzy deduplication workflow identifies and removes near-duplicate records using MinHash/LSH.

**Acceptance Criteria:**
- [ ] A dataset with known near-duplicate records (e.g., same text with minor word changes) is processed by `run_fuzzy_dedup()`
- [ ] Output contains fewer records than input (near-duplicates removed)
- [ ] Records that are clearly distinct (no similarity) are preserved in the output
- [ ] If `cudf` is unavailable or VRAM is insufficient, the test is skipped with a descriptive message (not a crash)
- [ ] The multi-phase workflow (minhash, LSH, connected components, removal) completes without error on the CPU path
- [ ] Output files are written to the specified output path

**Dependencies:** cavekit-curator-test-infra R2 (fixture data, temp workspace), cavekit-curator-test-infra R3 (`integration` or `gpu` marker as appropriate), cavekit-curator-test-infra R4 (VRAM guard)

### R7: Mixed Pipeline (DEFERRED — depends on R5/R6 dedup resolution)

**Status:** DEFERRED. Requires a working dedup stage; blocked on R5.

**Description:** A pipeline combining streaming stages (filters + modifiers) with a dedup stage processes data through the two-phase execution path: streaming stages write to an intermediate directory, then dedup runs on that intermediate output, and the final result is written to the requested output path.

**Acceptance Criteria:**
- [ ] A config with at least one filter, one modifier, and one ExactDedup stage is accepted by `run_pipeline.py`
- [ ] The intermediate directory (`{output_path}_pre_dedup`) is created during execution
- [ ] The final output directory contains the deduplicated, filtered, modified data
- [ ] The intermediate directory is cleaned up after successful completion
- [ ] Output record count is less than or equal to input count (filtering + dedup both reduce)

**Dependencies:** cavekit-curator-test-infra R2 (fixture data, temp workspace), cavekit-curator-test-infra R3 (`integration` marker)

### R8: IO Format Matrix

**Description:** The pipeline correctly reads and writes JSONL and Parquet formats, including cross-format conversion.

**Acceptance Criteria:**
- [ ] JSONL input with JSONL output (`output_format: "jsonl"`): output is valid JSONL
- [ ] Parquet input with Parquet output (`output_format: "parquet"`): output is valid Parquet readable by pandas/pyarrow
- [ ] JSONL input with Parquet output (`output_format: "parquet"`): output is valid Parquet with same record content
- [ ] Parquet input with JSONL output (`output_format: "jsonl"`): output is valid JSONL with same record content (explicitly add `test_parquet_to_jsonl`)
- [ ] In all cases, the `text` field content is preserved through the format conversion
- [ ] Record count is preserved in a pass-through pipeline (WordCountFilter with min_words=1, max_words=999999 or equivalent that accepts all): output record count equals input record count

**Dependencies:** cavekit-curator-test-infra R2 (JSONL and Parquet fixture data, temp workspace), cavekit-curator-test-infra R3 (`integration` marker)

### R9: Error Paths

**Description:** Pipeline execution produces clear, actionable error messages for invalid inputs and gracefully handles edge cases.

**Acceptance Criteria:**
- [ ] A config with an unknown `stage.type` (not in any registry) causes `build_pipeline()` to raise `ValueError` with a message containing the unknown type name
- [ ] A config with `input_path` pointing to a nonexistent file causes a clear, actionable error that mentions the path (not just a nonzero exit with generic traceback)
- [ ] A config with malformed JSONL input (at least one line that is invalid JSON) causes the pipeline to fail with a descriptive error, not an unhandled exception. Explicit test required.
- [ ] A config with an unsupported input file extension (e.g., `.csv`) causes `build_pipeline()` to raise `ValueError` mentioning "Unsupported input format". Explicit test required.
- [ ] A config with an unsupported `output_format` value (e.g., `"csv"`) causes `build_pipeline()` to raise `ValueError` mentioning "Unsupported output format"
- [ ] A filter stage that matches zero records produces an empty output file (zero records written, not a crash, not missing output). Explicit test required.
- [ ] `run_pipeline.py` exits with nonzero exit code on any pipeline error
- [ ] `_detect_filetype(path)` called with a nonexistent file path should not silently return "parquet" — either return a sentinel or raise FileNotFoundError (finding F-005)

**Dependencies:** cavekit-curator-test-infra R2 (fixture data, temp workspace), cavekit-curator-test-infra R3 (markers)

### R10: Resource Safety

**Description:** All pipeline integration tests respect resource constraints: small data, proper cleanup, no orphaned processes.

**Acceptance Criteria:**
- [ ] All fixture data files used by pipeline tests are under 1 MB each
- [ ] All tests that require GPU are marked with the `gpu` pytest marker
- [ ] All tests that require Ray are marked with the `integration` pytest marker
- [ ] Temp directories created during tests are cleaned up after each test (no accumulation across the test run)
- [ ] No orphan Ray worker processes remain after the test suite completes
- [ ] No orphan `run_pipeline.py` subprocesses remain after the test suite completes
- [ ] Tests that invoke `run_pipeline.py` as a subprocess set a timeout to prevent hanging indefinitely

**Dependencies:** cavekit-curator-test-infra R3 (markers), cavekit-curator-test-infra R4 (VRAM guard)

### R11: Dedup Cache Cleanup

**Description:** Dedup workflows produce a `{output_path}_dedup_cache`
directory alongside the `{output_path}_pre_dedup` intermediate. R7
covers cleanup of the `_pre_dedup` directory, but the `_dedup_cache`
directory (which holds MinHash/LSH caches and ID tables, and can be
substantial on large inputs) is never cleaned up. This is a disk leak
per dedup run.

**Acceptance Criteria:**
- [ ] After a successful dedup-containing pipeline run, the `{output_path}_dedup_cache` directory does not exist (cleaned up)
- [ ] On pipeline failure, cache cleanup is best-effort — not required, but must not crash the error path
- [ ] `run_pipeline.py` cleans both `{output_path}_pre_dedup` and `{output_path}_dedup_cache` symmetrically

**Dependencies:** R5 or R6 (must reach end-of-dedup to test cleanup)

### R12: _detect_filetype Regression Tests

**Description:** `_detect_filetype()` now handles both file paths and
directory paths. The file-path branch was the fix for a real bug
(`_detect_filetype` on a file returning "parquet" by fallback, which
broke dedup-on-file-path). The existing `TestDetectFiletype` tests
all pass directories — they do not exercise the file-path branch.

**Acceptance Criteria:**
- [ ] `_detect_filetype("/some/path/data.jsonl")` (file path, file may not exist) returns "jsonl"
- [ ] `_detect_filetype("/some/path/data.parquet")` returns "parquet"
- [ ] `_detect_filetype("/some/dir")` where dir contains *.jsonl returns "jsonl"
- [ ] `_detect_filetype("/some/dir")` where dir contains *.parquet returns "parquet"
- [ ] `_detect_filetype("/nonexistent/path")` behavior documented (current: returns "parquet"; see R9 AC8 for proposed error-raise)

**Dependencies:** cavekit-curator-test-infra R3 (markers)

## Out of Scope

- Testing the FastAPI HTTP layer (covered by cavekit-curator-api-contract)
- Testing individual stage behavior in isolation (covered by node tests in cavekit-curator-test-infra R5)
- Large-scale data processing or performance benchmarking
- GPU-specific classifiers that require downloaded model weights (e.g., FineWebEduClassifier with model files) -- instantiation is tested in R2, but execution with real models is not required
- Testing NeMo Curator internals (Ray scheduling, data partitioning internals)
- Testing deduplication accuracy thresholds beyond basic "duplicates removed" verification
- Custom stage pipeline execution (custom stages are tested via CRUD in API contract kit)

## Cross-References

- See also: `cavekit-curator-test-infra.md` -- provides fixture data (R2), markers (R3), VRAM guard (R4)
- See also: `cavekit-curator-api-contract.md` -- R6 (output_format bug) is the upstream producer; R1 here is the downstream consumer
- See also: `cavekit-curator-test-overview.md` -- master index

## Changes

- 2026-04-12: R5 (ExactDedup), R6 (FuzzyDedup), R7 (MixedPipeline) marked DEFERRED. Tests are class-level `@pytest.mark.skip`-ed — NeMo Curator's `TextDuplicatesRemovalWorkflow` phase-B fails with a field-mismatch error. Requires a dedicated workflow-debug pass outside contract-test scope. (Finding F-006.)
- 2026-04-12: R8 AC4 (Parquet→JSONL) made explicit. R8 AC6 record-count invariant tightened (must assert equality, not just presence). (Finding F-010.)
- 2026-04-12: R9 AC2/3/4/6 tightened — `malformed JSONL`, `unsupported input extension`, `zero-match filter empty output` explicitly require tests. Added AC8 to address `_detect_filetype` nonexistent-path silent fallthrough (finding F-005).
- 2026-04-12: Added R11 (dedup cache directory cleanup) — `{output_path}_dedup_cache` is never cleaned up; R7 only covers `_pre_dedup`. (Finding F-015.)
- 2026-04-12: Added R12 (`_detect_filetype` file-path regression tests) — existing `TestDetectFiletype` only exercises directory branch. (Finding F-004.)
