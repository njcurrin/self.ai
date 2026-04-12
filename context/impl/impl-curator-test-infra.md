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
| T-104 | DONE | pytest.ini with fast/integration/gpu markers. Dockerfile copies to /app. Marker filtering verified. |
| T-105 | DONE | VRAM guard in selfai_conftest.py. Auto-skips gpu tests below threshold. VRAM_THRESHOLD env var. |
| T-106 | DONE | 125 tests moved to tests/nodes/, all marked fast, 100% registry coverage, original removed. |
| T-107 | DONE | run_tests.sh CI entrypoint. TEST_MARKERS env var. JUnit XML. Runs self.ai tests only. |
