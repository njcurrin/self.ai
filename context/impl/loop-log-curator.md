### Iteration 1 — 2026-04-11
- **Task:** T-100, T-101, T-102, T-103 (Tier 0 batch)
- **Tier:** 0
- **Status:** DONE
- **Files:** tests/nodes/__init__.py, tests/pipeline/__init__.py, tests/selfai_conftest.py, tests/api/conftest.py (updated), tests/nodes/conftest.py, tests/pipeline/conftest.py, tests/fixtures/selfai/generate_fixtures.py, tests/fixtures/selfai/sample_data.jsonl, tests/test_selfai_fixtures.py
- **Validation:** Build P, Tests 10/10 P, Acceptance: all Tier 0 AC met
- **Next:** T-104 (Pytest markers) — gates all Tier 1+ work

### Iteration 2 — 2026-04-11
- **Task:** T-104, T-105, T-107 (Tier 1 batch, excluding T-106)
- **Tier:** 1
- **Status:** DONE
- **Files:** pytest.ini, Dockerfile.selfai, tests/selfai_conftest.py (VRAM guard), tests/run_tests.sh, conftest.py updates in all sub-packages
- **Validation:** Build P, Tests 138/140 P (2 skipped by design), Acceptance: T-104/T-105/T-107 AC met
- **Next:** T-106 (node test migration), then Tier 2 API Contract + Pipeline Integration
