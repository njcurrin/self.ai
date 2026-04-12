---
created: "2026-04-11"
last_edited: "2026-04-12"
---

# Cavekit: Curator API Contract Testing

## Scope

TestClient-based tests for all 19 HTTP endpoints in `api/main.py`. Full request/response schema validation. Known bugs specified as explicit failing-then-fixed test cases. Job state lifecycle transitions. SSE log streaming. Concurrent state safety. All tests in this kit are `fast`-marked (no Ray, no GPU, no subprocess).

Endpoint inventory (19 total):
- `GET /health`
- `GET /api/text`
- `GET /api/text/{category}/stages`
- `GET /api/text/{category}/stages/{stage_id}`
- `POST /api/text/custom/stages` (create)
- `GET /api/text/custom/stages` (list)
- `GET /api/text/custom/stages/{stage_uuid}` (detail)
- `DELETE /api/text/custom/stages/{stage_uuid}`
- `POST /api/text/custom/stages/validate-name`
- `POST /api/jobs`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/logs`
- `DELETE /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/cancel`
- `POST /api/jobs/{job_id}/schedule`
- `POST /api/jobs/{job_id}/unschedule`
- `POST /api/jobs/{job_id}/approve`
- `GET /api/data`

## Requirements

### R1: Health Endpoint

**Description:** The health endpoint returns a well-formed status response reflecting current job state.

**Acceptance Criteria:**
- [ ] `GET /health` returns HTTP 200
- [ ] Response body contains keys: `status`, `running_jobs`, `jobs_total`, `api_version`
- [ ] `status` is the string `"ok"`
- [ ] `running_jobs` is an integer >= 0
- [ ] `jobs_total` is an integer >= 0
- [ ] `api_version` is a non-empty string matching semver pattern (e.g., `"1.0.0"`)
- [ ] With no jobs created, `running_jobs` is 0 and `jobs_total` is 0
- [ ] After creating N jobs, `jobs_total` equals N
- [ ] `running_jobs` reflects only jobs whose status is `"running"`, not pending/scheduled/completed

**Dependencies:** cavekit-curator-test-infra R2 (TestClient fixture)

### R2: Stage Discovery

**Description:** The stage discovery endpoints return complete, correctly structured catalogs of all built-in processing stages.

**Note on registries:** The `/api/text` endpoint is backed by
`stage_registry.py`, which exposes NeMo Curator's `_STAGE_REGISTRY`
(ProcessingStage subclasses: `Filter`, `ScoreFilter`, `Modify`, etc.)
across 7 auto-detected categories: `filters`, `modifiers`, `classifiers`,
`document_ops`, `io`, `deduplication`, `other`. The run_pipeline.py
wrapper registries (`_FILTER_CLASS_REGISTRY` with 35 filter functions,
`_MODIFIER_CLASS_REGISTRY` with 9, `_CLASSIFIER_CLASS_REGISTRY` with 8)
are an internal job-dispatch layer NOT exposed through this endpoint.
Acceptance criteria below target the actually-exposed stage catalog.

**Acceptance Criteria:**
- [ ] `GET /api/text` returns HTTP 200 with a JSON object whose keys are category names
- [ ] Response includes at least the categories: `filters`, `modifiers`, `classifiers`
- [ ] Each category value is a list of objects with keys `id`, `name`, `source`
- [ ] Total stage count across all categories is at least 30 (the NeMo Curator catalog varies by version)
- [ ] Classifiers category has at least 8 entries
- [ ] `GET /api/text/filters/stages` returns only filter-category stages (HTTP 200)
- [ ] `GET /api/text/modifiers/stages` returns only modifier-category stages (HTTP 200)
- [ ] `GET /api/text/classifiers/stages` returns only classifier-category stages (HTTP 200)
- [ ] `GET /api/text/document_ops/stages` returns document_ops stages (HTTP 200)
- [ ] `GET /api/text/nonexistent/stages` returns HTTP 404
- [ ] `GET /api/text/document_ops/stages/AddId` (or any known builtin stage) returns an object with keys: `id`, `name`, `category`, `description`, `module`, `parameters`, `resources`
- [ ] `parameters` is a list of objects each containing `name`, `type`, `required`
- [ ] `GET /api/text/{category}/stages/NonexistentStage` returns HTTP 404
- [ ] Requesting a known stage under the wrong category returns HTTP 404 (e.g., `/api/text/modifiers/stages/AddId` when `AddId` is in `document_ops`)

**Dependencies:** cavekit-curator-test-infra R2 (TestClient fixture)

### R3: Custom Stage CRUD

**Description:** Full create, list, get, delete lifecycle for user-defined custom stages, including validation and error handling.

**Acceptance Criteria:**
- [ ] `POST /api/text/custom/stages` with valid name, category, and ProcessingStage code returns HTTP 201
- [ ] Response contains `id` (UUID string), `name`, `source` (`"custom"`), `category`
- [ ] `GET /api/text/custom/stages` lists the created stage with matching `id` and `name`
- [ ] `GET /api/text/custom/stages/{uuid}` returns full detail including `code` field containing the original source
- [ ] `DELETE /api/text/custom/stages/{uuid}` returns HTTP 200 with `status: "deleted"`
- [ ] After deletion, `GET /api/text/custom/stages/{uuid}` returns HTTP 404
- [ ] After deletion, `GET /api/text/custom/stages` no longer includes the deleted stage
- [ ] `POST /api/text/custom/stages` with invalid Python code (syntax error) returns HTTP 400
- [ ] `POST /api/text/custom/stages` with code that defines no ProcessingStage subclass returns HTTP 400
- [ ] `POST /api/text/custom/stages` with a name matching an existing builtin stage returns HTTP 400
- [ ] `POST /api/text/custom/stages` with a name matching an existing custom stage returns HTTP 400
- [ ] `DELETE /api/text/custom/stages/nonexistent-uuid` returns HTTP 404
- [ ] `POST /api/text/custom/stages/validate-name` with an available name returns `{available: true}`
- [ ] `POST /api/text/custom/stages/validate-name` with a builtin stage name returns `{available: false, reason: ...}`

**Dependencies:** cavekit-curator-test-infra R2 (TestClient fixture, temp workspace)

### R4: Job Creation and Validation

**Description:** Job creation validates inputs, persists state, and returns well-formed responses. Listing returns jobs in newest-first order.

**Acceptance Criteria:**
- [ ] `POST /api/jobs` with valid input_path (file exists), output_path, and stages returns HTTP 201
- [ ] Response contains `job_id`, `name`, `status`, `input_path`, `output_path`, `stages_count`, `created_at`, `log_file`, `config_file`
- [ ] `status` is `"pending"` for immediate jobs (no `scheduled_for`)
- [ ] `status` is `"scheduled"` when `scheduled_for` is a future timestamp
- [ ] `status` is `"pending"` when `scheduled_for` is a past timestamp (treated as immediate)
- [ ] `stages_count` equals the number of stages in the request
- [ ] `POST /api/jobs` with nonexistent `input_path` returns HTTP 400 with detail mentioning the path
- [ ] `POST /api/jobs` with an unknown stage type returns HTTP 400 with detail mentioning the stage type
- [ ] `GET /api/jobs` returns a list sorted by `created_at` descending (newest first)
- [ ] `GET /api/jobs/{job_id}` returns full detail for an existing job
- [ ] `GET /api/jobs/nonexistent` returns HTTP 404

**Dependencies:** cavekit-curator-test-infra R2 (TestClient fixture, temp workspace, fixture data)

### R5: Job State Machine

**Description:** Job status transitions follow the defined state machine. Invalid transitions return errors.

**Acceptance Criteria:**
- [ ] A pending job can be approved: `POST /api/jobs/{id}/approve` transitions status to `"running"` (with mocked subprocess)
- [ ] A pending job can be scheduled: `POST /api/jobs/{id}/schedule` with future timestamp transitions status to `"scheduled"`
- [ ] A scheduled job can be unscheduled: `POST /api/jobs/{id}/unschedule` transitions status back to `"pending"` and clears `scheduled_for`
- [ ] A scheduled job can be approved directly: `POST /api/jobs/{id}/approve` transitions to `"running"` and clears `scheduled_for`
- [ ] A running job can be cancelled via `DELETE /api/jobs/{id}` -- status becomes `"cancelled"` and `finished_at` is set
- [ ] A running job can be cancelled via `POST /api/jobs/{id}/cancel` -- same behavior as DELETE
- [ ] A pending job can be cancelled via `DELETE /api/jobs/{id}` -- status becomes `"cancelled"`
- [ ] A scheduled job can be cancelled via `DELETE /api/jobs/{id}` -- status becomes `"cancelled"`
- [ ] Approving an already-running job returns HTTP 400
- [ ] Approving a completed job returns HTTP 400
- [ ] Cancelling a completed job returns HTTP 400
- [ ] Cancelling a failed job returns HTTP 400
- [ ] Scheduling a running job returns HTTP 400
- [ ] Unscheduling a pending (non-scheduled) job returns HTTP 400

**Dependencies:** cavekit-curator-test-infra R2 (TestClient fixture, job state factory)

### R6: BUG -- output_format Config Persistence

**Description:** When a job is created with `output_format` set (e.g., `"parquet"`), that value must be written to the subprocess config JSON file on disk. Currently, the config dict in `create_job()` (main.py line ~416) omits `output_format`, so `run_pipeline.py` always falls back to `"jsonl"`.

**Acceptance Criteria:**
- [ ] Creating a job with `output_format: "parquet"` results in a config JSON file on disk that contains the key `"output_format"` with value `"parquet"`
- [ ] Creating a job with `output_format: "jsonl"` results in a config JSON file containing `"output_format"` with value `"jsonl"`
- [ ] Creating a job with no `output_format` (null/omitted) results in a config JSON file that either omits the key or sets it to `null` (allowing `run_pipeline.py` to apply its default)
- [ ] The config JSON file contains all fields from the request: `name`, `input_path`, `output_path`, `text_field`, `stages`, and `output_format`

**Dependencies:** cavekit-curator-test-infra R2 (TestClient fixture, temp workspace)
**Cross-reference:** cavekit-curator-pipeline-integration R1 (Config Round-Trip) validates the downstream consumer of this config

### R7: BUG -- Approve Failure State Consistency

**Description:** If the approve operation fails (e.g., subprocess cannot start, config file missing), the job's status must transition to `"failed"` with an error message, not remain stuck in `"running"` or silently enter an inconsistent state.

**Acceptance Criteria:**
- [ ] If `_start_job()` fails due to missing config file, job status is `"failed"` (not `"running"`)
- [ ] If `_start_job()` fails due to log file creation error, job status is `"failed"` (not `"running"`)
- [ ] After a failed approve, `GET /api/jobs/{id}` returns `error_message` describing the failure
- [ ] After a failed approve, `finished_at` is set (the job did not silently enter a stuck state)
- [ ] Approving a job that does not exist returns HTTP 404

**Dependencies:** cavekit-curator-test-infra R2 (TestClient fixture, job state factory)

### R8: BEHAVIOR -- Scheduled Jobs Explicit Non-Auto-Start

**Description:** The `_poll_jobs()` background task only monitors running jobs for completion. It does NOT auto-start scheduled jobs when their `scheduled_for` time arrives. This is intentional: the self.UI daemon is responsible for triggering scheduled jobs via the approve endpoint. This behavior must be documented by an explicit test.

**Acceptance Criteria:**
- [ ] A job with status `"scheduled"` and a `scheduled_for` time in the past does NOT automatically transition to `"running"` after `_poll_jobs()` executes
- [ ] The test includes a comment documenting that scheduled job triggering is the responsibility of the self.UI daemon, not the curator API
- [ ] After `_poll_jobs()` runs, the scheduled job's status remains `"scheduled"` with no change to `started_at`

**Dependencies:** cavekit-curator-test-infra R2 (TestClient fixture, job state factory)

### R9: Job Logs

**Description:** The logs endpoint returns log content with tail support and SSE streaming.

**Note on streaming:** TestClient cannot cleanly terminate the
streaming endpoint because `api/main.py` uses an infinite `while True`
loop in the `StreamingResponse` generator. Acceptance for the stream
contract is split between (a) route/schema verification via OpenAPI
(fast, reliable) and (b) an optional httpx.AsyncClient integration
test that actually exercises the stream (future work).

**Acceptance Criteria:**
- [ ] `GET /api/jobs/{id}/logs` returns HTTP 200 with a `lines` array
- [ ] With `tail=5`, only the last 5 lines of the log file are returned
- [ ] With no `tail` param, default is 100 (up to 100 lines returned from a file with >100 lines)
- [ ] If the log file is empty, `lines` is an empty array (not an error)
- [ ] The `GET /api/jobs/{job_id}/logs` route is registered in the OpenAPI schema and accepts the `stream` query parameter (satisfies the contract without requiring TestClient to consume an infinite stream)
- [ ] If the log file does not exist, HTTP 404 is returned
- [ ] `GET /api/jobs/nonexistent/logs` returns HTTP 404

**Dependencies:** cavekit-curator-test-infra R2 (TestClient fixture, job state factory)

### R10: Error Response Contract

**Description:** All error responses across all endpoints follow a consistent schema and return correct HTTP semantics.

**Acceptance Criteria:**
- [ ] 404 responses contain a `detail` key with a human-readable string message
- [ ] 400 responses (e.g., invalid input_path, unknown stage type) contain a `detail` key
- [ ] 422 responses (Pydantic validation errors) contain a `detail` key (Pydantic default format)
- [ ] `POST /api/jobs` with invalid JSON body returns HTTP 422
- [ ] All successful JSON responses have content-type `application/json`
- [ ] `GET /api/data` returns HTTP 200 with keys `data_dir` and `files`
- [ ] `GET /api/data` `files` array contains objects with keys: `path`, `name`, `size_bytes`, `relative_path`

**Dependencies:** cavekit-curator-test-infra R2 (TestClient fixture)

### R11: Concurrent State Safety

**Description:** Concurrent operations on the job store do not corrupt state or produce inconsistent reads.

**Acceptance Criteria:**
- [ ] Creating 10 jobs concurrently (via threaded TestClient calls) results in exactly 10 jobs in `_jobs` with unique `job_id` values
- [ ] Reading `GET /api/jobs` while a concurrent write (`POST /api/jobs`) is in progress returns a valid JSON response (no partial writes)
- [ ] The `jobs.json` state file is never left in a corrupted state after concurrent operations (file parses as valid JSON)

**Dependencies:** cavekit-curator-test-infra R2 (TestClient fixture, temp workspace)

### R12: SECURITY -- Custom Stage Code Execution Surface

**Description:** The `POST /api/text/custom/stages` endpoint writes
user-submitted Python to disk and executes it via `importlib` inside
the curator container. Execution is unsandboxed. The endpoint has no
authentication. This is a deferred security concern (a plugin sandbox
is planned but out of scope for this test cycle). The kit must
explicitly document the resulting operational constraint so the
deferral is visible.

**Acceptance Criteria:**
- [ ] README or kit prose explicitly states: "custom stage code executes unrestricted inside the curator container; the `/api/text/custom/stages` endpoints MUST NOT be exposed on an untrusted network until a plugin sandbox is implemented"
- [ ] No test in this cavekit asserts sandboxing behavior (sandbox is deferred)
- [ ] A test OR comment in `tests/api/test_api_contract.py` references this deferral so future maintainers don't mistake the gap for an oversight

**Dependencies:** none (documentation-only requirement)

### R13: _poll_jobs Direct Invocation Test

**Description:** R8 claims the `_poll_jobs()` background task does not
auto-start scheduled jobs. The existing tests only check job state
after `job_factory` creates it — they never actually invoke
`_poll_jobs()`. To prove the acceptance criterion, the poll logic must
be exercised directly against a scheduled, past-due job.

**Acceptance Criteria:**
- [ ] A `_poll_jobs_once()` helper exists (or the test extracts the per-iteration body) that runs a single poll iteration without `await asyncio.sleep(5)`
- [ ] A test creates a job with `status=SCHEDULED` and `scheduled_for` in the past, invokes the poll logic, asserts status remains `scheduled` and `started_at` remains `None`
- [ ] A test creates a job with `status=RUNNING` with a completed mock subprocess, invokes the poll logic, asserts status transitions to `completed` (positive control that the poll does do its job for RUNNING)

**Dependencies:** cavekit-curator-test-infra R2 (job state factory)

## UI-SIDE FLAGS (Deferred -- Do Not Spec Fixes)

The following issues exist on the self.UI side and are documented here for awareness. No acceptance criteria or fix specifications are included in this kit.

- **`validate-name` missing proxy route:** The `POST /api/text/custom/stages/validate-name` endpoint exists in the curator API but has no corresponding proxy route in `self.UI/backend/selfai_ui/routers/curator.py`. Custom stage name validation is not accessible from the UI.
- **GPU queue daemon assumes approve always succeeds:** `self.UI/backend/selfai_ui/utils/gpu_queue.py` calls the approve endpoint but does not handle failure responses. If approve fails, the daemon does not retry or revert queue state.
- **`_finalize_curator_job()` has no retry on Knowledge creation failure:** If the post-job Knowledge base creation call fails, the completed curation output exists on disk but is not registered. No retry or recovery mechanism exists.

## Out of Scope

- Testing `run_pipeline.py` subprocess execution (covered by cavekit-curator-pipeline-integration)
- Testing NeMo Curator stage behavior/correctness (covered by cavekit-curator-test-infra R5 node tests)
- Testing self.UI proxy routes or frontend code
- Load testing or performance benchmarking of the API
- Authentication or authorization (not implemented in curator API)
- Testing the `/api/data` endpoint's file listing against specific filesystem layouts beyond basic schema validation

## Cross-References

- See also: `cavekit-curator-test-infra.md` -- provides TestClient fixture (R2), markers (R3), temp workspace (R2)
- See also: `cavekit-curator-pipeline-integration.md` -- R1 (Config Round-Trip) is the downstream consumer of the config file validated in R6
- See also: `cavekit-curator-test-overview.md` -- master index

## Changes

- 2026-04-12: R2 rewritten — the cavekit's original reference to `_FILTER_CLASS_REGISTRY`(35) / `_MODIFIER_CLASS_REGISTRY`(9) / `_CLASSIFIER_CLASS_REGISTRY`(8) was wrong; the `/api/text` endpoint exposes the stage_registry ProcessingStage catalog (~37 stages across 7 categories), not those wrapper registries. AC updated to match reality. (Inspection finding — kit vs. reality drift.)
- 2026-04-12: R9 AC for `stream=true` reworded to OpenAPI-schema assertion. TestClient cannot terminate `while True` StreamingResponse. Future work: add httpx.AsyncClient integration test. (Finding F-002 / AC F-005.)
- 2026-04-12: R10 AC1 expanded to explicitly cover 404/400/422 detail-key presence (previously only 404 was covered).
- 2026-04-12: Added R12 (custom stage security deferral documentation) — surfaces the unsandboxed `exec_module` risk that was previously only noted in user memory (finding F-016).
- 2026-04-12: Added R13 (`_poll_jobs` direct invocation test) — closes the vacuous R8 test gap (finding F-002).
