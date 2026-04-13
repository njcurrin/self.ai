---
created: "2026-04-12"
last_edited: "2026-04-12"
---

# Cavekit: UI Router Tests — Jobs

## Scope

Lifecycle and correctness tests for job management routers: training (courses and jobs), evaluations (lm-eval and bigcode-eval jobs), and tasks (completion generators for titles, tags, queries, emoji, MoA, autocompletion). Validates job state machines, scheduling and approval flows, status sync from external services (mocked), SSE streaming correctness, and business-logic correctness of task completion payloads. Input validation for raw-dict endpoints is covered by `cavekit-ui-security-tests.md`; this kit covers the functional contract beyond validation.

Source analysis: `context/refs/research-brief-ui-test-suite.md` Sections 1 (coverage gaps), 3 (fire-and-forget background tasks), 4 (respx for external service mocking).

## Requirements

### R1: Training Courses

**Description:** The training courses subrouter must implement CRUD for training courses (reusable training recipe definitions) with user-scoped listing and status transitions.

**Acceptance Criteria:**
- [ ] Listing training courses returns only courses visible to the caller (own plus any shared or public)
- [ ] Creating a course with a valid recipe payload persists it and returns the created record
- [ ] Reading a course by identifier as the owner returns its full recipe
- [ ] Reading a course owned by a different user returns a not-found or forbidden status when the course is not shared
- [ ] Updating an owned course's recipe persists the change and is reflected on subsequent reads
- [ ] Deleting an owned course removes it from subsequent list and read results
- [ ] The status of a course transitions between its defined states (draft, active, archived, or equivalent) only through documented operations

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R3 (TrainingCourse factory if present, otherwise inline)

### R2: Training Jobs

**Description:** The training jobs subrouter must implement job submission against a course, approval/rejection, cancellation, scheduling, and status synchronization from Llamolotl (mocked at HTTP level).

**Acceptance Criteria:**
- [ ] Submitting a training job referencing a valid course creates a job in the pending state and associates it with the course
- [ ] Submitting a training job referencing a non-existent course returns an error status
- [ ] Approving a pending job transitions it to the scheduled or queued state
- [ ] Rejecting a pending job transitions it to cancelled with a rejection marker in the job record (distinguishable from a user-initiated cancel) and prevents further dispatch — see `cavekit-ui-job-state-machines.md` R1 for the canonical state set
- [ ] Cancelling a job in any pre-running state transitions it to the cancelled state
- [ ] Cancelling a running job signals cancellation and transitions to cancelling or cancelled
- [ ] Scheduling a job with a specific target window or time persists the schedule and is reflected in queue ordering
- [ ] Syncing status from Llamolotl (mocked) updates the job's state according to the upstream response (pending → queued → running → completed or failed)
- [ ] Status sync handles upstream errors (4xx, 5xx, timeout) without crashing the router and leaves the job state consistent
- [ ] Listing training jobs returns only the caller's jobs for a user-scoped call, and all jobs for an admin-scoped call

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R3 (TrainingJob factory), R4 (Llamolotl mock)

### R3: Eval Jobs

**Description:** The evaluations router must implement eval job submission for both lm-eval and bigcode-eval types, approval/rejection, cancellation, scheduling, and live SSE streaming of eval events from the harness (mocked).

**Acceptance Criteria:**
- [ ] Submitting an lm-eval job with a valid task specification creates a job in the pending state with type lm-eval
- [ ] Submitting a bigcode-eval job with a valid task specification creates a job in the pending state with type bigcode-eval
- [ ] Submitting an eval job with an unknown type returns an error status
- [ ] Approving a pending eval job transitions it to scheduled or queued
- [ ] Rejecting a pending eval job transitions it to cancelled with a rejection marker (see `cavekit-ui-job-state-machines.md` R1 — no distinct "rejected" state)
- [ ] Cancelling an eval job transitions it to cancelled (or cancelling, then cancelled)
- [ ] Scheduling an eval job against a target window persists the schedule
- [ ] The SSE event stream for a running eval job yields well-formed event chunks (event-type/data shape) when the harness mock emits events
- [ ] The SSE stream closes cleanly when the harness mock signals completion
- [ ] The SSE stream surfaces harness errors as error events without terminating the HTTP connection abnormally
- [ ] Eval job results persist after completion and are readable via the job's read endpoint

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R3 (EvalJob factory), R4 (eval harness mock)

### R4: Tasks (Completions)

**Description:** Each task endpoint (title, tag, query, emoji, autocompletion, MoA) must build a task-specific prompt, forward to the mocked chat completions handler, aggregate multi-agent responses correctly for MoA, and sanitize upstream errors so no raw upstream body leaks into responses.

**Acceptance Criteria:**
- [ ] For each of title, tag, query, emoji, autocompletion: the mocked completions handler receives a payload whose prompt substitutes the input conversation or text into the task-specific template, and contains a task-identifying substring unique to that task (title-related text for title calls, tag-related text for tag calls, etc.)
- [ ] No task template leaks into another task's prompt (a title call never contains tag-template text, and vice versa for all task pairs)
- [ ] For MoA with N submitted agent responses: the aggregated output contains every submitted response as a substring, in submission order, with no silent drops
- [ ] For MoA where one agent's mocked completion returns an error: the aggregated output includes the successful responses and identifies the failed agent distinctly (the response body contains a marker or field naming which agent failed); the whole call does not fail because one agent failed
- [ ] MoA coverage tests include N=1, N=3, and N=5 agents
- [ ] For each non-MoA task: the chat completion response body from the mocked handler appears unchanged in the task's response body (pass-through content)
- [ ] For each task when the mocked completions handler returns a 4xx: the task endpoint returns the same 4xx status; when it returns 5xx or times out: the task endpoint returns 500
- [ ] For error responses: the response `detail` field identifies which task failed (e.g., "title generation failed"), and the raw upstream response body does not appear anywhere in the task endpoint's response bytes
- [ ] Each single-task endpoint triggers exactly one upstream chat completion call (no fan-out); MoA with N agents triggers exactly N upstream calls

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R4 (chat completions mock)

## Out of Scope

- Authentication enforcement (covered by `cavekit-ui-security-tests.md` R1, R2)
- Input validation on raw-dict payloads (covered by `cavekit-ui-security-tests.md` R5)
- Real GPU execution or real model outputs
- Real Llamolotl service behavior (mocked at HTTP level)
- Real eval harness execution (mocked at HTTP level)
- Training or eval result quality (what the model learns or how well it scores)
- Window scheduling semantics beyond the job's schedule field (covered by `cavekit-ui-router-tests-admin.md` R4)
- Queue ordering semantics (covered by `cavekit-ui-router-tests-admin.md` R5)

## Cross-References

- See also: `cavekit-ui-test-infrastructure.md` — provides fixtures, factories, and respx service mocks
- See also: `cavekit-ui-security-tests.md` — covers auth and input validation
- See also: `cavekit-ui-router-tests-admin.md` — covers windows and queue which job lifecycle interacts with
- See also: `cavekit-ui-router-tests-proxies.md` — covers the proxy contract between this app and Llamolotl/eval harnesses
- See also: `cavekit-ui-router-tests-overview.md` — master index
- Source: `context/refs/research-brief-ui-test-suite.md` — Section 1 (coverage gaps), Section 3 (background tasks), Section 4 (respx)

## Changelog
- 2026-04-12: Tightened R4 (Tasks Completions) with prompt-shape, MoA aggregation, and error-without-leakage contracts — drives T-R15
