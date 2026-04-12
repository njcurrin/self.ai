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
    """Current behavior: router converts upstream 401 to 500 with detail.

    Real finding: same class as the Ollama 4xx→500 router bug.
    The response body wraps the upstream error rather than preserving
    the status code. Pin to current behavior; flip to == 401 when
    the router is fixed to pass through upstream status codes.
    """
    mocked_openai.get(
        f"{mocked_openai.base_url}/models",
        status=401,
        payload={"error": {"message": "Invalid API key"}},
    )
    resp = authenticated_admin.get("/openai/models/0")
    assert resp.status_code == 500
    assert "Invalid" in resp.text or "Unexpected error" in resp.text


@pytest.mark.tier1
def test_openai_no_unmocked_call(authenticated_admin):
    """Without aioresponses, unmocked upstream calls return 5xx with
    a connection-error body.

    We assert specifically that the response is NOT a 2xx (real network
    success) AND NOT a 4xx (auth/validation issue in our test harness).
    The only acceptable state when there's no mock is a 5xx
    connection-error from the router's aiohttp exception handler.
    """
    resp = authenticated_admin.get("/openai/models/0")
    # 5xx = router failed to reach upstream (expected without mock).
    # Any 2xx would mean the real OpenAI API was hit — test env failure.
    # Any 4xx would mean auth/payload mismatch — harness misconfiguration.
    assert 500 <= resp.status_code < 600, (
        f"Expected 5xx connection error without mock, got "
        f"{resp.status_code}: {resp.text[:200]}"
    )
