---
created: "2026-04-12"
last_edited: "2026-04-12"
---
# Implementation Tracking: UI Router Tests

Build site: context/plans/build-site-ui-router-tests.md

## Tasks Completed

### Core Data domain (T-300..T-309)
| Task | Status | File | Notes |
|------|--------|------|-------|
| T-300 | DONE | test_chats.py | List/create/read/update/delete + pagination + cross-user isolation |
| T-301 | DONE | test_chats.py | Import/export/clone round-trip |
| T-302 | DONE | test_channels.py | Channels + message CRUD (admin-only create) |
| T-303 | PARTIAL | test_channels.py | Message list verified. Missing R2 AC11-13: reactions add/remove + thread replies. Tracked T-R17. |
| T-304 | PARTIAL | test_folders.py | CRUD + duplicate rejection + reparent + cross-user. Missing R3 AC6 cycle rejection, AC8 delete with children, AC9/10 chat assign/unassign. |
| T-305 | DONE | test_files.py | List + upload round-trip + cross-user isolation |
| T-306 | PARTIAL | test_files.py | Metadata round-trip only. Missing R4 AC7: content byte-for-byte equivalence (upload → GET /content/ → compare). Upload may also skip if retrieval backend unavailable. |
| T-307 | DONE | test_knowledge.py | CRUD with admin role, KnowledgeFilesResponse shape |
| T-308 | PARTIAL | test_knowledge.py | Only basic CRUD covered. Missing R5 AC7-9, 11: file add/remove/reset + mocked query scoping. Tracked T-R18. |
| T-309 | DONE | test_memories.py | List/delete/delete-all with monkeypatched VECTOR_DB_CLIENT |

### Workspace domain (T-310..T-313)
| Task | Status | File | Notes |
|------|--------|------|-------|
| T-310 | DONE | test_prompts.py | CRUD + duplicate-command rejection |
| T-311 | PARTIAL | test_tools.py | Create-minimal + invalid-id rejection. Missing R2 AC5/6 content update, AC7 delete owned, AC8/9 valves, AC10 access control. |
| T-312 | PARTIAL | test_functions.py | Admin-only create, any-user list. Missing R3 AC5/6 update + active toggle, AC7/8 valves. |
| T-313 | PARTIAL | test_models.py | CRUD + duplicate rejection. Missing R4 AC4 read-not-found, AC5/6 param/system-prompt overrides, AC7 access control, AC8 reset-to-default. |

### Admin domain (T-314..T-319)
| Task | Status | File | Notes |
|------|--------|------|-------|
| T-314 | PARTIAL | test_groups.py | CRUD + user forbidden. Missing R1 AC4 read-not-found, AC6 update permissions, AC7/8 add/remove member, AC9 user-membership query. |
| T-315 | PARTIAL | test_configs.py | Banners round-trip, export, user forbidden. Missing R2 AC3-8: default models, prompt suggestions, user permissions get+set. |
| T-316 | DONE | test_benchmarks.py | List (seeded), update max_duration_minutes |
| T-317 | DONE | test_windows.py | CRUD + time validation + slot replacement |
| T-318 | PARTIAL | test_windows.py | Missing R4 AC7 active-window lookup by timestamp, AC8/9 enable/disable state transitions. Tracked T-R19. |
| T-319 | PARTIAL | test_queue.py | Empty + with-pending-job + not-found promotions only. Missing R5 AC2-7: priority ordering, run_now/high promotion happy paths, demotion, scope filters, entry shape. Tracked T-R16. |

### Jobs domain (T-320..T-326)
| Task | Status | File | Notes |
|------|--------|------|-------|
| T-320 | DONE | test_training.py | Courses CRUD |
| T-321 | PARTIAL | test_training.py | Only invalid-course reject. Missing R2 AC3-7: approve/reject/cancel/schedule state machine, AC10 list scope. Tracked T-R13. |
| T-322 | PARTIAL | test_training.py | Only not-found. Missing R2 AC8-9: Llamolotl sync with respx, 4xx/5xx/timeout resilience. Tracked T-R13. |
| T-323 | DONE | test_evaluations.py | Eval jobs bigcode + lm-eval types |
| T-324 | PARTIAL | test_evaluations.py | SSE stream deferred. Missing R3 AC8-10: SSE event shape, clean close, error surfacing. Tracked T-R14. |
| T-325 | PARTIAL | test_tasks.py | Empty body + unknown model only. Missing R4 AC1-4,6,7: prompt-shape assertion via respx mock + response passthrough. Tracked T-R15. |
| T-326 | PARTIAL | test_tasks.py | Missing R4 AC5 MoA aggregation, AC8 error-without-data-leakage. Tracked T-R15. |

### Proxies domain (T-327..T-334)
| Task | Status | File | Notes |
|------|--------|------|-------|
| T-327 | PARTIAL | test_proxies.py | Only status ping + config auth. Missing R1 AC1-7: list/generate/chat/streaming/mgmt/passthrough forwarding with respx. Tracked T-R01. |
| T-328 | PARTIAL | test_proxies.py | Only config auth. Missing R2 AC1-6: chat completions (streaming + non-streaming), model listing, 4xx/5xx passthrough. Tracked T-R02. |
| T-329 | PARTIAL | test_proxies.py | Only status + config auth. Missing R3 AC1-6: load/unload/sync/chat forwarding. Tracked T-R02. |
| T-330 | PARTIAL | test_proxies.py | Only config auth. Missing R4 AC1-6: pipeline config write, job submit, stage registry, error preserve. Tracked T-R02. |
| T-331 | PARTIAL | test_proxies.py | Only config auth. Missing R5 AC1-2, 4-6: transcribe, synthesize, config update persist, upstream error passthrough. Tracked T-R03/T-R11. |
| T-332 | PARTIAL | test_proxies.py | Only config auth. Missing R6 AC2-5: update persist, generate forward, upstream error, zero-network enforcement. Tracked T-R03. |
| T-333 | PARTIAL | test_proxies.py + test_retrieval.py | Status + config auth only. Missing R7 AC1-6: RAG query, crawl config update, file process, upstream error. Tracked T-R03. |
| T-334 | PARTIAL | test_proxies.py | Config read only. Missing R8 AC2-8: config update, verify success/failure for both lm-eval and bigcode-eval. Tracked T-R03. |

## Extra Work Beyond Build Site

Added during execution since the research brief flagged these as gaps:

| Scope | File | Notes |
|-------|------|-------|
| Users router | test_users.py | Session user CRUD, settings, info, permissions |
| Auths router | test_auths.py | Session, profile, signout, admin config, API keys |
| Pipelines router | test_pipelines.py | Admin-only enforcement |
| System router | test_system.py | Resources/processes observability |
| Migration integrity | test_migration_integrity.py | Hybrid Peewee+Alembic schema correctness |

## Real Bug Discovered & Fixed

- **users.py:48 and :58** — `Users.get_user_groups(user.id)` was called but
  this method doesn't exist on UsersTable. The endpoints
  `/api/v1/users/groups` and `/api/v1/users/permissions` were raising
  AttributeError for every caller. Fixed by replacing with
  `Groups.get_groups_by_member_id(user.id)`. Caught by a literal
  "does it return 200" test (the simplest possible coverage).

## Final Test Counts

- 143 router tests (this build site)
- 35 extra tests (users, auths, pipelines, system, migration integrity)
- 163 security tests (from previous cavekit)
- 52 model unit tests (existing)
- 9 infrastructure validation tests
- **360 total tests passing, 0 failing, 0 xfailed, 0 xpassed**

## Coverage Summary

Routers with tests: ~30 of 32 (webhook and some smaller ones not specifically
targeted; security-matrix tests blanket them all for auth coverage).
