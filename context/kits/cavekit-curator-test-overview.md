---
created: "2026-04-11"
last_edited: "2026-04-12"
---

# Cavekit: Curator Test Suite Overview

## Purpose

Master index for the self.curator test suite kits. These kits specify the complete testing strategy for the custom FastAPI wrapper around NeMo Curator, covering test infrastructure, API contract validation, and pipeline integration testing.

All tests run inside the curator Docker container (CUDA 12.8.1, Ubuntu 24.04, Python 3.12, Ray, NeMo Curator) with a 24 GB VRAM budget.

## Domain Index

| Kit | Domain | File | Requirements | Acceptance Criteria |
|-----|--------|------|:------------:|:-------------------:|
| Test Infrastructure | Test layout, fixtures, markers, VRAM guard, node test migration | `cavekit-curator-test-infra.md` | R1-R6 | 40 |
| API Contract | HTTP endpoint testing, schema validation, bug regression, state machine, custom-stage security deferral, poll-loop test | `cavekit-curator-api-contract.md` | R1-R13 | 98 |
| Pipeline Integration | End-to-end pipeline execution, registry, dedup (deferred), IO formats, error paths, cache cleanup, _detect_filetype regression | `cavekit-curator-pipeline-integration.md` | R1-R12 | 76 |

**Totals:** 3 domains, 31 requirements, ~214 acceptance criteria (post-revision)

## Dependency Graph

```
cavekit-curator-test-infra
    |
    +---> cavekit-curator-api-contract
    |         (uses: TestClient fixture, temp workspace, job state factory,
    |          markers, fixture data)
    |
    +---> cavekit-curator-pipeline-integration
              (uses: fixture data, temp workspace, markers, VRAM guard,
               Ray cluster fixture)
```

**Build order:** Test Infrastructure MUST be implemented first. API Contract and Pipeline Integration can be implemented in parallel after Test Infrastructure is complete.

There are no circular dependencies between kits.

## Cross-Reference Map

### Test Infrastructure provides to other kits:

| Infra Requirement | Consumed By |
|-------------------|-------------|
| R1 (Unified Test Layout) | All kits -- directory structure |
| R2 (Shared Fixtures: TestClient) | API Contract R1-R11 |
| R2 (Shared Fixtures: temp workspace) | API Contract R3, R4, R6, R11; Pipeline R1, R3-R9 |
| R2 (Shared Fixtures: job state factory) | API Contract R5, R7, R8, R9 |
| R2 (Shared Fixtures: fixture data) | API Contract R4; Pipeline R1, R3-R9 |
| R3 (Pytest Markers) | API Contract (all `fast`); Pipeline (mix of `fast`, `integration`, `gpu`) |
| R4 (VRAM Guard) | Pipeline R5, R6, R10 |

### Cross-kit bug references:

| Bug | API Contract | Pipeline Integration |
|-----|-------------|---------------------|
| output_format not in config JSON | R6 (config file validation) | R1 (config round-trip consumer) |
| text_field mutation via pop() | -- | R4 (build_pipeline param safety) |
| Approve failure state desync | R7 (HTTP-level state check) | -- |
| Scheduled jobs non-auto-start | R8 (poll behavior test) | -- |

### UI-side issues (flagged, not spec'd):

These are documented in `cavekit-curator-api-contract.md` under "UI-SIDE FLAGS" for awareness. No acceptance criteria or fixes are specified in any kit.

- `validate-name` endpoint missing proxy route in self.UI
- GPU queue daemon assumes approve always succeeds
- `_finalize_curator_job()` has no retry on Knowledge creation failure

## Known Bugs Summary

| # | Bug | Root Cause Location | Kit / Requirement |
|---|-----|-------------------|-------------------|
| 1 | `output_format` not written to subprocess config JSON | `api/main.py` line ~416-424, config dict omits `output_format` | API Contract R6, Pipeline R1 |
| 2 | `text_field` mutation in `build_pipeline()` | `api/run_pipeline.py` line ~224, `stage_params.pop('text_field', ...)` | Pipeline R4 |
| 3 | Approve-failure state desync | `api/main.py` `_start_job()` sets status to FAILED but approve flow depends on this | API Contract R7 |
| 4 | Scheduled jobs never auto-start | `api/main.py` `_poll_jobs()` only monitors RUNNING jobs | API Contract R8 (intentional, documented) |
| 5 | `validate-name` no UI proxy | `self.UI/backend/selfai_ui/routers/curator.py` | UI-SIDE (deferred) |

## Implementation Notes

- **Marker strategy:** API Contract tests are all `fast` (TestClient, no subprocess, no Ray). Pipeline Integration tests use `integration` (Ray needed) or `gpu` (CUDA needed). Node tests (migrated) are `fast`.
- **Existing tests:** 125 node tests in `tests/api/test_pipeline_nodes.py` are migrated to `tests/nodes/` per Test Infrastructure R5. No tests are deleted -- only moved and fixed if incorrect.
- **Existing conftest:** The upstream NeMo Curator `tests/conftest.py` provides Ray cluster fixtures and modality-based collection hooks. These are preserved and extended, not replaced.
- **Container execution:** All tests run via `docker compose exec curator pytest tests/` or the CI entrypoint script (Test Infrastructure R6).
