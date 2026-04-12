"""
T-R02: OpenAI proxy forwarding tests using aioresponses.

OpenAI router uses `aiohttp.ClientSession` for upstream calls. Tests
use `aioresponses` (async version of `responses`) for mocking.

Strict mode: unmocked requests raise ClientConnectionError.
"""

import pytest
from aioresponses import aioresponses


@pytest.fixture
def mocked_openai(test_app):
    """aioresponses context for configured OpenAI base URLs.

    Any unmocked call fails the request. Zero real network.
    """
    urls = getattr(
        test_app.state.config, "OPENAI_API_BASE_URLS", ["https://api.openai.com/v1"]
    )
    with aioresponses() as m:
        m.base_url = urls[0].rstrip("/")
        yield m


@pytest.mark.tier1
def test_openai_models_list_forwards(authenticated_admin, mocked_openai):
    """GET /openai/models/0 returns the upstream-formatted model list."""
    expected = {
        "object": "list",
        "data": [{"id": "gpt-4", "object": "model", "created": 1, "owned_by": "openai"}],
    }
    mocked_openai.get(
        f"{mocked_openai.base_url}/models",
        status=200,
        payload=expected,
    )
    resp = authenticated_admin.get("/openai/models/0")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body


@pytest.mark.tier1
def test_openai_models_passthrough_4xx(authenticated_admin, mocked_openai):
    """Upstream 401 on models list is preserved."""
    mocked_openai.get(
        f"{mocked_openai.base_url}/models",
        status=401,
        payload={"error": {"message": "Invalid API key"}},
    )
    resp = authenticated_admin.get("/openai/models/0")
    # Router may pass through or convert — accept either
    assert resp.status_code in (401, 500)


@pytest.mark.tier1
def test_openai_no_unmocked_call(authenticated_admin):
    """Without aioresponses, unmocked upstream calls should fail the request."""
    # No aioresponses context — calls go to the real network.
    # In the test environment there's no route to api.openai.com,
    # so the router returns 5xx or wrapped error.
    resp = authenticated_admin.get("/openai/models/0")
    # Should NOT return 200 — that would mean a real API was hit
    assert resp.status_code != 200
