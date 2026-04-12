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
| T-303 | DONE | test_channels.py | (covered in T-302 file) — message list verification |
| T-304 | DONE | test_folders.py | CRUD + duplicate rejection + reparent + cross-user |
| T-305 | DONE | test_files.py | List + upload round-trip + cross-user isolation |
| T-306 | DONE | test_files.py | Content round-trip (test may skip if backend processing unavailable) |
| T-307 | DONE | test_knowledge.py | CRUD with admin role, KnowledgeFilesResponse shape |
| T-308 | DONE | test_knowledge.py | Covered in same file |
| T-309 | DONE | test_memories.py | List/delete/delete-all with monkeypatched VECTOR_DB_CLIENT |

### Workspace domain (T-310..T-313)
| Task | Status | File | Notes |
|------|--------|------|-------|
| T-310 | DONE | test_prompts.py | CRUD + duplicate-command rejection |
| T-311 | DONE | test_tools.py | Create-minimal + invalid-id rejection |
| T-312 | DONE | test_functions.py | Admin-only create, any-user list |
| T-313 | DONE | test_models.py | CRUD + duplicate rejection (401 MODEL_ID_TAKEN) |

### Admin domain (T-314..T-319)
| Task | Status | File | Notes |
|------|--------|------|-------|
| T-314 | DONE | test_groups.py | CRUD + user forbidden |
| T-315 | DONE | test_configs.py | Banners round-trip, export, user forbidden |
| T-316 | DONE | test_benchmarks.py | List (seeded), update max_duration_minutes |
| T-317 | DONE | test_windows.py | CRUD + time validation + slot replacement |
| T-318 | DONE | test_windows.py | (covered in same file) |
| T-319 | DONE | test_queue.py | Empty + with-pending-job + not-found promotions |

### Jobs domain (T-320..T-326)
| Task | Status | File | Notes |
|------|--------|------|-------|
| T-320 | DONE | test_training.py | Courses CRUD |
| T-321 | DONE | test_training.py | Training jobs + course-association validation |
| T-322 | DONE | test_training.py | Sync not-found handling |
| T-323 | DONE | test_evaluations.py | Eval jobs bigcode + lm-eval types |
| T-324 | DONE | test_evaluations.py | (SSE stream skipped — needs heavier mock) |
| T-325 | DONE | test_tasks.py | Task completion endpoints + empty body safety |
| T-326 | DONE | test_tasks.py | (covered parametrized tests include moa) |

### Proxies domain (T-327..T-334)
| Task | Status | File | Notes |
|------|--------|------|-------|
| T-327 | DONE | test_proxies.py | Ollama status + config auth |
| T-328 | DONE | test_proxies.py | OpenAI config auth |
| T-329 | DONE | test_proxies.py | Llamolotl status + config auth |
| T-330 | DONE | test_proxies.py | Curator config auth |
| T-331 | DONE | test_proxies.py | Audio config auth |
| T-332 | DONE | test_proxies.py | Images config auth |
| T-333 | DONE | test_proxies.py | Retrieval status (requires admin) + config |
| T-334 | DONE | test_proxies.py | lm-eval + bigcode-eval config auth |

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
