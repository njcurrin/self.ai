---
created: "2026-04-12"
last_edited: "2026-04-12"
---


# Cavekit: UI Job State Machines

## Scope

Test contract for the shared state machine governing every GPU-queued job (training, eval, pipeline). Pins state vocabulary, transition rules, idempotency, upstream-sync conflict resolution, and per-type lifecycle differences. Covers deferred tasks T-R13 (training state machine + Llamolotl sync) and T-R14 (eval state machine + SSE). The shared machine exists because all three job types flow through one GPU queue so they can coordinate across N ≥ 1 GPUs.

## Requirements

### R1: Shared State Vocabulary and Transition Table

**Description:** All GPU-queued jobs (training, eval, pipeline) share a single state vocabulary and a single transition matrix. Illegal transitions must never occur via any endpoint or background sync path.

**Acceptance Criteria:**
- [ ] The canonical state set is exactly: pending, scheduled, queued, running, completed, failed, cancelled
- [ ] From pending: valid next states are scheduled, queued (via approve), cancelled (via cancel), or cancelled (via reject)
- [ ] From scheduled: valid next states are pending (via unschedule), queued (via approve or queue promotion), cancelled
- [ ] From queued: valid next states are running (via dispatch), cancelled
- [ ] From running: valid next states are completed, failed, cancelled, cancelling (intermediate)
- [ ] From cancelling: valid next states are cancelled (nominal), completed (upstream finished before cancel landed), failed (upstream errored before cancel landed)
- [ ] From completed, failed, cancelled: no further transitions are allowed
- [ ] Reject is a verb that transitions pending or scheduled into cancelled (with a rejection marker in the job record — the test asserts the job is readable and distinguishable from a user-initiated cancel); there is no distinct "rejected" state in the canonical set
- [ ] Attempting an illegal transition through any transition endpoint returns a 4xx status and does not change the stored state
- [ ] The state stored after every transition endpoint call matches the transition table exactly

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R3 (factories for each job type)

### R2: Transition Endpoint Idempotency

**Description:** Transition endpoints follow an honest-API idempotency rule: same-state transitions are 2xx no-ops, illegal-state transitions are 4xx conflicts. No silent data corruption, no silent success on impossible operations.

**Acceptance Criteria:**
- [ ] Cancelling a job that is already cancelled returns 2xx and the stored record is unchanged
- [ ] Rejecting a job that is already in a terminal state (completed, failed, cancelled) returns 4xx and the stored record is unchanged
- [ ] Approving a job in exactly pending or scheduled state returns 2xx and transitions to queued; approving a job in any other state (queued, running, cancelling, completed, failed, cancelled) returns 4xx and the stored record is unchanged
- [ ] Cancelling a job in completed or failed state returns 4xx (cannot undo a finished job)

**Dependencies:** R1

### R3: Upstream Sync Conflict Resolution

**Description:** When local state diverges from upstream (Llamolotl for training, lm-eval/bigcode-eval harnesses for eval) during a sync, the local terminal state is sticky and the sync pathway only ever advances the lifecycle, never rewinds. Local cancellation propagates outward to the upstream service so distributed state converges.

**Acceptance Criteria:**
- [ ] When local state is cancelled, completed, or failed, an upstream sync that returns a non-terminal or different status does not modify the stored local state
- [ ] When local state is cancelled and upstream still reports running, the sync operation either issues a cancel request to the upstream or is a no-op; in neither case is local state flipped back to running
- [ ] When local state is non-terminal (pending, scheduled, queued, running) and upstream reports a valid forward transition (running, completed, failed, cancelled), the local state is updated to match upstream
- [ ] When upstream returns a 4xx, 5xx, or times out, the local state is not modified and the sync operation returns an error-but-non-crashing status
- [ ] A cancel operation on a non-terminal job triggers an upstream cancel call (the test asserts the upstream mock received the cancel); the local transition to cancelled happens regardless of the upstream response

**Dependencies:** R1, R2; `cavekit-ui-router-tests-proxies.md` (upstream HTTP contract)

### R4: Training-Specific Lifecycle

**Description:** Training jobs reference a training course (recipe) and submit to Llamolotl on dispatch. Upstream Llamolotl status maps into the shared state vocabulary through a documented mapping.

**Acceptance Criteria:**
- [ ] Submitting a training job referencing a non-existent course returns 4xx and no job record is created
- [ ] Approving a pending or scheduled training job transitions to queued and, on dispatch by the GPU queue, issues a Llamolotl submit request
- [ ] The upstream Llamolotl status set (whatever its vocabulary) maps into the shared state vocabulary through a single documented mapping function; tests cover each upstream status value and assert the correct local state
- [ ] On successful completion, the completed state is written exactly once; repeated sync calls after completion are no-ops

**Dependencies:** R1, R3

### R5: Eval-Specific Lifecycle and SSE Stream

**Description:** Eval jobs specify one of a known set of eval types; dispatch fans out to the matching harness; running eval jobs expose a pass-through SSE stream.

**Acceptance Criteria:**
- [ ] Submitting an eval job with a known type (lm-eval or bigcode-eval) creates a pending job with that type recorded
- [ ] Submitting an eval job with an unknown type returns 4xx and no job record is created
- [ ] On dispatch, the request is sent to the harness matching the job type; tests use transport mocks to assert the correct harness URL received the request
- [ ] The SSE stream for a running eval job is a pass-through: every JSON line emitted by the harness appears as exactly one `data: {json}\n\n` frame in the stream, in the same order; content equality is asserted at the parsed-JSON level (object equality after deserialization), so whitespace and key ordering may be normalized by the serializer but no field may be added, removed, or modified
- [ ] The stream terminates with a final `event: done\ndata: {json}` frame whose JSON object includes the terminal status (completed, failed, or cancelled)
- [ ] When the harness disconnects mid-stream unexpectedly, the stream emits an error-indicating frame (not an HTTP-level error) and then closes cleanly
- [ ] The SSE contract does not pin any fields beyond the transport shape — harness-specific JSON fields are not asserted, so new eval types can be added without modifying this kit

**Dependencies:** R1, R3

### R6: Pipeline-Specific Lifecycle

**Description:** Pipeline jobs flow through the shared state machine identically to training and eval jobs. Pipeline-specific payload (the node graph) is preserved across state transitions. Downstream side effects (dataset writes from a completed pipeline) execute exactly once.

**Acceptance Criteria:**
- [ ] A pipeline job's node graph payload is readable at every state in its lifecycle and is semantically equal to the submitted payload (parsed-JSON equality; the router may normalize representation but must not add, remove, or modify nodes, edges, or field values)
- [ ] The shared transition table from R1 applies to pipeline jobs without any pipeline-specific exceptions
- [ ] Downstream dataset write side effects execute exactly once, on the running-to-completed transition; retries or redundant sync calls after completion do not re-trigger the write
- [ ] A pipeline job cancelled mid-run leaves no partial dataset output in the final state (either no output or a fully-written output, never a half-written one)

**Dependencies:** R1, R3; `cavekit-curator-pipeline-integration.md` (for the downstream dataset write contract)

### R7: GPU Queue Promotion Ordering

**Description:** When multiple jobs compete for a free GPU, the queue promotes them in a deterministic order governed by priority, schedule, and creation time.

**Acceptance Criteria:**
- [ ] A job with priority run_now promotes ahead of any job with priority high or normal
- [ ] Among jobs with the same priority, a scheduled job whose scheduled time has passed promotes ahead of a pending job
- [ ] Among jobs with the same priority and same scheduling status, the job created earliest promotes first (FIFO)
- [ ] A job that becomes run_now after another job has already started running does not preempt the running job (no preemption in the queue)
- [ ] The promotion order is observable: listing the queue returns jobs in the exact order they will be dispatched given current GPU availability

**Dependencies:** R1; `cavekit-ui-router-tests-admin.md` R5 (queue endpoint coverage)

## Out of Scope

- Concurrent-transition race condition tests (hard to make deterministic; defer to app-level locking design)
- Real GPU execution, real model outputs, real training or eval results
- Real Llamolotl or harness behavior (mocked at HTTP level)
- Authentication enforcement on transition endpoints (covered by `cavekit-ui-security-tests.md`)
- Input validation on raw-dict transition payloads (covered by `cavekit-ui-security-tests.md` R5)
- Window scheduling semantics beyond the job's schedule field (covered by `cavekit-ui-router-tests-admin.md` R4)

## Cross-References

- See also: `cavekit-ui-router-tests-jobs.md` — existing R2/R3/R4 for per-domain CRUD; this kit tightens the state machine portion
- See also: `cavekit-ui-router-tests-admin.md` — queue endpoints observing the order defined by R7
- See also: `cavekit-ui-router-tests-proxies.md` — Llamolotl and harness HTTP contracts used by R3/R4/R5
- See also: `cavekit-curator-pipeline-integration.md` — pipeline downstream dataset write contract
- See also: `cavekit-ui-router-tests-overview.md` — master index
- Source: `context/refs/research-brief-ui-test-suite.md` — Section 1 (coverage gaps), Section 3 (fire-and-forget background tasks)
