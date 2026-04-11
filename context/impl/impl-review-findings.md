---
created: "2026-04-11"
last_edited: "2026-04-11"
---

# Review Findings

Build site: context/plans/build-site.md

| Finding | Severity | File | Status | Task |
|---------|----------|------|--------|------|
| F-001: Queued pipeline tasks lose command on restart | P0 | state.py:638 | FIXED | T-063 |
| F-002: File handle leak on subprocess logs | P1 | state.py:556,680 | FIXED | T-064 |
| F-003: Path traversal on config GET/DELETE | P1 | routers/jobs.py:268 | FIXED | T-065 |
| F-004: Path traversal on pipeline endpoints | P1 | routers/pipeline.py:248,372,432 | FIXED | T-066 |
| F-005: All queued GPU tasks start simultaneously | P1 | state.py:605-612 | FIXED | T-067 |
| F-006: No thread safety on shared state | P2 | state.py:260 | FIXED | — |
| F-007: Inline config written before YAML validation | P2 | routers/jobs.py:74 | FIXED | — |
| F-008: create_config no YAML validation | P2 | routers/jobs.py:233 | FIXED | — |
| F-009: config_path traversal in job create | P2 | routers/jobs.py:80 | FIXED | T-065 |
| F-010: Log streaming generators never terminate | P2 | routers/jobs.py:170 | FIXED | T-068 |
| F-011: Chat template upload uses raw dict | P2 | routers/system.py:45 | FIXED | T-070 |
| F-012: GPU memory reports process-level not system-wide | P2 | state.py:733 | FIXED | T-071 |
| F-013: Remaining print() in train.py | P3 | train.py:460 | FIXED | — |
| F-015: Recursive size calc in list endpoints | P2 | routers/jobs.py:315 | FIXED | — |
| F-016: Deprecated on_event startup | P3 | main.py:28 | FIXED | — |
| F-017: No test coverage for health/system/model endpoints | P2 | tests/ | NEW | — |
| F-018: convert-to-gguf allows absolute path without validation | P2 | routers/pipeline.py:301 | FIXED | T-066 |
