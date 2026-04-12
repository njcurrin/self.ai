## Agent: existing-art — Research Findings

**Note:** WebSearch blocked in environment. Findings are knowledge-based (cutoff Aug 2025). Verify URLs before relying.

### Q1: Open-WebUI Test Suite
- Minimal/no formal test suite as of early 2025. No comprehensive pytest suite in main repo. Cypress stub exists. Known gap acknowledged in issues/PRs.
- **Confidence: Medium**

### Q2: Large SvelteKit App Testing Patterns
- **Vitest** for unit/component tests with `@testing-library/svelte`
- **Playwright** for E2E — SvelteKit ships with first-class integration
- Must mock `$app/navigation`, `$app/stores`, `$app/environment` (runtime-injected)
- Real examples: sveltejs/svelte (vitest), melt-ui (vitest+playwright), shadcn-svelte (vitest)
- **Confidence: High**

### Q3: FastAPI Production Test Patterns
- `httpx.AsyncClient` + `pytest-asyncio` is canonical (replaced TestClient for async)
- `app.dependency_overrides[get_db] = override_get_db` for DI testing
- `testcontainers-python` for real Postgres/Redis in CI
- Reference: `tiangolo/full-stack-fastapi-template`
- **Confidence: High**

### Q4: LLM/Chat App Testing (Streaming, Model Switching)
- Streaming: `httpx.AsyncClient` with `stream=True`, assert SSE/NDJSON structure not token content
- Model switching: `pytest.mark.parametrize` across model identifiers + `MockLLM` fixture
- `respx` for mocking Ollama/OpenAI HTTP endpoints
- `syrupy` for prompt template snapshot testing
- **Confidence: Medium-High**

### Q5: Python + JS Monorepo Test Organization
- Split CI jobs: pytest and vitest/playwright run in parallel
- `Makefile` or `justfile` as unified runner
- Root `pyproject.toml` for pytest, root `vitest.config.ts` for frontend
- Separate coverage: `coverage.py` + `v8`/`istanbul`
- **Confidence: Medium**

### Q6: CI/CD with External Service Dependencies
- GitHub Actions `services:` for Postgres, Redis, Qdrant containers
- Tiered markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.gpu`
- Mock Ollama with `respx` or `pytest-httpserver` for unit/integration
- Self-hosted GPU runners for nightly live Ollama tests only
- `testcontainers-python` has Qdrant/Weaviate support
- Reference: `deepset-ai/haystack` tiered test system
- **Confidence: High**
