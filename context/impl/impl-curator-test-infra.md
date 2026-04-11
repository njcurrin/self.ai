---
created: "2026-04-11"
last_edited: "2026-04-11"
---
# Implementation Tracking: Curator Test Infrastructure

Build site: context/plans/build-site-curator-tests.md

| Task | Status | Notes |
|------|--------|-------|
| T-100 | DONE | Created tests/nodes/, tests/pipeline/ with __init__.py. tests/api/ pre-existed. |
| T-101 | DONE | selfai_conftest.py: TestClient, temp_workspace, job_factory fixtures. Sub-package conftest.py files import them. |
| T-102 | DONE | 30-record JSONL + Parquet fixtures with exact dups, near dups, short text, URLs. generate_fixtures.py for in-container Parquet gen. |
| T-103 | DONE | Verified upstream conftest.py untouched. shared_ray_cluster available via conftest hierarchy. |
