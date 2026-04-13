---
created: "2026-04-12"
last_edited: "2026-04-12"
---

# Implementation Tracking: State Machines + Deferred Router Tests

Build site: context/plans/build-site-state-machines.md

| Task | Status | Notes |
|------|--------|-------|
| T-500 | TODO | state-machine constants + transition matrix guard |
| T-501 | TODO | illegal-transition matrix (L, biggest task) |
| T-502 | TODO | reject-vs-cancel marker distinguishability |
| T-503 | TODO | transition endpoint idempotency |
| T-504 | TODO | upstream sync sticky-terminal |
| T-505 | TODO | upstream sync forward-only |
| T-506 | TODO | cancel propagation to upstream |
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

## Findings surfaced so far

All documented as xfailed tests in `tests/routers/test_channels.py` with file:line pointers:

1. **Reaction idempotency broken**: `Messages.add_reaction_to_message` (messages.py:211-227) inserts a new row every call — no dedup on `(user_id, message_id, name)`. Violates core-data R2 new-AC1.

2. **Grandchild replies not enforced**: `channels.py::post_new_message` accepts any `parent_id` without validating that the target itself has `parent_id=null`. Violates core-data R2 new-AC6.

3. **Parent delete does not cascade**: `Messages.delete_message_by_id` (messages.py:268-276) only deletes the single message and its reactions. `delete_replies_by_id` exists as a separate method but is never called. Violates core-data R2 new-AC8.

4. **Reply listing appends parent**: `Messages.get_messages_by_parent_id` (messages.py:174-196) appends the parent message to the thread list when under the limit. Violates core-data R2 new-AC7 (listing must exclude parent).
