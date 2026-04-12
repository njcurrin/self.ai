---
created: "2026-04-11"
last_edited: "2026-04-12"
---

# Review Findings — Router Tests Cycle

Source: `/ck:check` inspection on 2026-04-12 after build-site-ui-router-tests completed.

## Summary

| Severity | Count |
|----------|-------|
| P0 (blocker) | 2 |
| P1 (critical) | 7 |
| P2 (medium) | 6 |
| P3 (minor) | 7 |
| **Total** | **22** |

Verdict: **REJECT**. Two P0 blockers prevent the cycle from being closed.

## Findings Table

| Finding | Severity | File | Status |
|---------|----------|------|--------|
| F-001: Proxies tests miss respx-forwarding mandate | P0 | tests/routers/test_proxies.py | NEW |
| F-002: 14+ tasks marked DONE with unimplemented AC | P0 | impl-ui-router-tests.md | NEW |
| F-003: 6 `cannot_X` tests accept 200 | P1 | test_tools/prompts/models/training/evaluations/knowledge | NEW |
| F-004: test_task_endpoint_rejects_unknown_model accepts 200 | P1 | tests/routers/test_tasks.py:22-32 | NEW |
| F-005: test_signin_unknown_user_rejected accepts 500 | P1 | tests/routers/test_auths.py:47-54 | NEW |
| F-006: authenticated_admin sets global Content-Type | P1 | tests/conftest.py:380-384 | NEW |
| F-007: pytest markers not registered → 218 warnings | P1 | missing pytest.ini / pyproject.toml | NEW |
| F-008: test_upload mutates FILE_MAX_SIZE with no restore | P1 | tests/routers/test_files.py:20-42 | NEW |
| F-009: test_audio accepts 500/502/503 on models/voices | P1 | tests/routers/test_audio.py:18-35 | NEW |
| F-010: Not-found tests with multi-branch pass conditions | P2 | 8 files | NEW |
| F-011: test_system accepts 500/503 on admin endpoints | P2 | tests/routers/test_system.py:17-42 | NEW |
| F-012: test_curator_config_admin_access accepts 502/503 | P2 | tests/routers/test_proxies.py:88-91 | NEW |
| F-013: Dead/misleading docstrings admitting scope cuts | P2 | test_proxies/retrieval/memories | NEW |
| F-014: test_list_pipelines_admin_access accepts 500/502/503 | P2 | tests/routers/test_pipelines.py:18-28 | NEW |
| F-015: CuratorJobFactory change with no migration-parity test | P2 | tests/factories.py:282-297 | NEW |
| F-016: test_update_group accepts 400 | P3 | tests/routers/test_groups.py:35-55 | NEW |
| F-017: test_create_eval_job_* accepts 400 | P3 | tests/routers/test_evaluations.py:28-48 | NEW |
| F-018: test_api_key_create accepts 400 without distinguishing | P3 | tests/routers/test_auths.py:84-95 | NEW |
| F-019: test_list_chats_empty stateful-leak-sensitive | P3 | tests/routers/test_chats.py:17-21 | NEW |
| F-020: test_memories cross-user delete lacks HTTP assertion | P3 | tests/routers/test_memories.py:103-137 | NEW |
| F-021: Empty __init__.py with no comment | P3 | tests/routers/__init__.py | NEW |
| F-022: factories.py has unaudited dead code | P3 | tests/factories.py | NEW |

## Gap Analysis Summary

- 0/27 requirements COMPLETE
- 23 PARTIAL, 4 MISSING
- ~95/234 acceptance criteria actually met (~40%)
- Proxies domain (8 requirements, 50 AC) ~90% unmet
- Jobs state-machine requirements (training R2 approve/reject/cancel/schedule/sync, eval R3 SSE) mostly untested

## Proposed Cavekit Additions

These have been applied to the kits (see Changelog sections):

1. **Overview R-new:** DONE criteria for router-test tasks
   - Every AC must have at least one test with strict assertions
   - No test may assert `(success, failure)` status simultaneously
   - "rejects/forbidden/not-found" tests must not accept 200
   - Proxies kit tests must use `respx` + assert-no-unmatched-requests

2. **test-infrastructure R-new:** Pytest marker registration
   - All markers registered in pyproject.toml
   - filterwarnings = `error::pytest.PytestUnknownMarkWarning`

3. **proxies R-new:** Enforce `assert_all_called=True, assert_all_mocked=True`

## Next Cycle Priorities

1. Add respx-based proxy forwarding tests (F-001 / P0)
2. Fix impl tracking to reflect real coverage (F-002 / P0)
3. Tighten permissive assertions (F-003, F-004, F-005, F-009, F-010, F-011, F-012, F-014)
4. Register pytest markers (F-007)
5. Fix conftest Content-Type issue (F-006)
6. Fix FILE_MAX_SIZE mutation leak (F-008)
7. Cover the MISSING state-machine AC (training jobs + eval jobs + queue ordering)
8. Add kits for over-built routers (users, auths, pipelines, system, utils)
