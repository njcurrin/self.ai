---
created: "2026-04-12"
last_edited: "2026-04-13"
---

# Implementation Tracking: State Machines + Deferred Router Tests

Build site: context/plans/build-site-state-machines.md

| Task | Status | Notes |
|------|--------|-------|
| T-500 | DONE | Canonical 7-state vocabulary writable across training/eval/pipeline job models — 3 tests in test_job_state_machines.py |
| T-501 | DONE | Parametrized illegal-transition matrix for approve/reject/schedule/unschedule × (training, eval) × each illegal from-state. 42 new tests, all pass. Also surfaced + fixed 3 eval-router bugs (reject-scheduled, cancel-cancelled 2xx no-op, cancel-from-scheduled) mirroring the training fixes from T-503/T-504. |
| T-502 | DONE | Reject marker `error_message="Rejected by administrator"` distinguishes from user-cancel — 2 tests |
| T-503 | DONE | Approve illegal-state matrix (queued/running/completed 4xx) + cancel-completed/failed 4xx + cancel-cancelled 2xx no-op. Fixed training.py:310 for idempotent cancel. 6 tests. |
| T-504 | DONE | Sync no longer resurrects cancelled/completed/failed local state. Fixed training.py sync_job_status with sticky-terminal guard. 1 test. |
| T-505 | DONE | Sync advances non-terminal local to upstream status; upstream 5xx surfaces as 502 (not silent 200). Fixed training.py sync_job_status with resp.status >= 400 check on both heretic + standard paths. 2 tests. |
| T-506 | DONE | Cancel issues DELETE /api/jobs/:id to upstream; local cancels regardless of upstream response. 2 tests. |
| T-507 | TODO | training submit/approve/dispatch lifecycle |
| T-508 | TODO | Llamolotl status mapping + idempotent completion |
| T-509 | TODO | eval submission + harness dispatch routing |
| T-510 | TODO | SSE streaming-harness fixture |
| T-511 | TODO | SSE pass-through content-equality + done frame (blocked on T-510) |
| T-512 | TODO | SSE error + contract-shape |
| T-513 | TODO | pipeline graph preservation + R1 table compliance |
| T-514 | TODO | pipeline dataset-write exactly-once + cancel-clean-output |
| T-515 | TODO | GPU queue promotion ordering |
| T-516 | TODO | per-task prompt-shape tests |
| T-517 | TODO | MoA aggregation happy path (N=1,3,5) |
| T-518 | TODO | MoA partial failure + error-without-leakage |
| T-519 | DONE | reactions idempotency/scoping/shape/remove-nonexistent — 4 tests (1 xfail, 3 pass), 3 real findings |
| T-520 | DONE | threads + cascade + grandchild — 5 tests (3 xfail, 2 pass), 3 real findings |

## Findings

### Training state-machine router — FIXED 2026-04-13

All four fixed in `selfai_ui/routers/training.py`; xfail markers removed from `tests/routers/test_job_state_machines.py`; suite went 448→452 pass / 8→4 xfail with zero regressions.

1. **Reject rejected `scheduled` jobs** — `reject_job` now allows both `pending` and `scheduled` per R1-AC8.
2. **Cancel-on-cancelled returned 400** — `cancel_job` now returns the job 2xx no-op when already cancelled per R2-AC1; completed/failed still 4xx.
3. **Sync overwrote terminal local** — `sync_job_status` now short-circuits when local is `completed/failed/cancelled` per R3-AC1/AC2.
4. **Sync silently 200'd on upstream 5xx** — `sync_job_status` now raises 502 when upstream returns ≥400 (not 404) on both heretic and standard paths per R3-AC4.

### Eval state-machine router — FIXED 2026-04-13 (during T-501)

Three bugs parallel to the training fixes, surfaced by the T-501 parametrized matrix and fixed in `selfai_ui/routers/evaluations.py` before the matrix landed green:

1. **`reject_eval_job`** only allowed `pending` (evaluations.py:1093) — now allows `pending` or `scheduled` per R1-AC8.
2. **`cancel_eval_job`** returned 400 on already-cancelled (evaluations.py:739) — now returns 2xx no-op per R2-AC1.
3. **`cancel_eval_job`** was missing `scheduled` from its legal set — now accepts pending/scheduled/queued/running per R1.

### Channel router — xfailed, not yet fixed

Documented as xfailed tests in `tests/routers/test_channels.py` with file:line pointers:

1. **Reaction idempotency broken**: `Messages.add_reaction_to_message` (messages.py:211-227) inserts a new row every call — no dedup on `(user_id, message_id, name)`. Violates core-data R2 new-AC1.

2. **Grandchild replies not enforced**: `channels.py::post_new_message` accepts any `parent_id` without validating that the target itself has `parent_id=null`. Violates core-data R2 new-AC6.

3. **Parent delete does not cascade**: `Messages.delete_message_by_id` (messages.py:268-276) only deletes the single message and its reactions. `delete_replies_by_id` exists as a separate method but is never called. Violates core-data R2 new-AC8.

4. **Reply listing appends parent**: `Messages.get_messages_by_parent_id` (messages.py:174-196) appends the parent message to the thread list when under the limit. Violates core-data R2 new-AC7 (listing must exclude parent).
