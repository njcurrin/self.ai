"""
External service mock fixtures for backend tests.

Provides respx-based fixtures that intercept outbound HTTP calls to each
external service. Each fixture supports success, error, and streaming
response scenarios.

Usage in tests:
    def test_something(mock_ollama):
        mock_ollama.success()
        # ... test code that hits Ollama endpoints ...
"""

import json
import httpx
import pytest
import respx


# ---------------------------------------------------------------------------
# Service base URLs (match selfai_ui/config.py and env defaults)
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = "http://self-ollama:11434"
OPENAI_BASE_URL = "https://api.openai.com"
LLAMOLOTL_BASE_URL = "http://self-llamolotl:8080"
CURATOR_BASE_URL = "http://self-curator:8000"
LM_EVAL_BASE_URL = "http://self-lm-eval:5000"
BIGCODE_EVAL_BASE_URL = "http://self-bigcode-eval:5001"


# ---------------------------------------------------------------------------
# Helper: SSE stream builder
# ---------------------------------------------------------------------------

def _sse_stream(events: list[dict]) -> bytes:
    """Build a well-formed SSE byte stream from a list of event dicts."""
    lines = []
    for event in events:
        lines.append(f"data: {json.dumps(event)}\n\n")
    lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()


# ---------------------------------------------------------------------------
# Mock wrapper class
# ---------------------------------------------------------------------------

class ServiceMock:
    """Wrapper around a respx router for a single external service."""

    def __init__(self, router: respx.MockRouter, base_url: str):
        self.router = router
        self.base_url = base_url

    def success(self, path: str = "", method: str = "GET",
                json_body: dict | None = None, status_code: int = 200):
        """Mock a successful JSON response."""
        body = json_body or {"status": "ok"}
        route = self.router.request(method, f"{self.base_url}{path}")
        route.mock(return_value=httpx.Response(status_code, json=body))
        return route

    def error(self, path: str = "", method: str = "GET",
              status_code: int = 500, detail: str = "Internal Server Error"):
        """Mock an error response."""
        route = self.router.request(method, f"{self.base_url}{path}")
        route.mock(return_value=httpx.Response(
            status_code, json={"detail": detail}
        ))
        return route

    def timeout(self, path: str = "", method: str = "GET"):
        """Mock a connection timeout."""
        route = self.router.request(method, f"{self.base_url}{path}")
        route.mock(side_effect=httpx.ConnectTimeout("Connection timed out"))
        return route

    def stream(self, path: str = "", method: str = "POST",
               events: list[dict] | None = None):
        """Mock an SSE streaming response."""
        events = events or [{"token": "Hello"}, {"token": " world"}]
        content = _sse_stream(events)
        route = self.router.request(method, f"{self.base_url}{path}")
        route.mock(return_value=httpx.Response(
            200,
            content=content,
            headers={"content-type": "text/event-stream"},
        ))
        return route

    def catch_all(self, status_code: int = 200, json_body: dict | None = None):
        """Mock all requests to this service's base URL."""
        body = json_body or {"status": "ok"}
        route = self.router.route(url__startswith=self.base_url)
        route.mock(return_value=httpx.Response(status_code, json=body))
        return route


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ollama():
    """Mock all outbound HTTP to Ollama."""
    with respx.mock(assert_all_mocked=False) as router:
        mock = ServiceMock(router, OLLAMA_BASE_URL)
        # Default: health check returns OK
        router.get(f"{OLLAMA_BASE_URL}/").mock(
            return_value=httpx.Response(200, text="Ollama is running")
        )
        router.head(f"{OLLAMA_BASE_URL}/").mock(
            return_value=httpx.Response(200)
        )
        yield mock


@pytest.fixture
def mock_openai():
    """Mock all outbound HTTP to OpenAI-compatible endpoints."""
    with respx.mock(assert_all_mocked=False) as router:
        mock = ServiceMock(router, OPENAI_BASE_URL)
        yield mock


@pytest.fixture
def mock_llamolotl():
    """Mock all outbound HTTP to Llamolotl training server."""
    with respx.mock(assert_all_mocked=False) as router:
        mock = ServiceMock(router, LLAMOLOTL_BASE_URL)
        # Default: health check
        router.get(f"{LLAMOLOTL_BASE_URL}/").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        router.head(f"{LLAMOLOTL_BASE_URL}/").mock(
            return_value=httpx.Response(200)
        )
        yield mock


@pytest.fixture
def mock_curator():
    """Mock all outbound HTTP to Curator data pipeline service."""
    with respx.mock(assert_all_mocked=False) as router:
        mock = ServiceMock(router, CURATOR_BASE_URL)
        router.get(f"{CURATOR_BASE_URL}/health").mock(
            return_value=httpx.Response(200, json={"status": "healthy"})
        )
        yield mock


@pytest.fixture
def mock_eval_harness():
    """Mock all outbound HTTP to lm-eval and bigcode-eval harnesses."""
    with respx.mock(assert_all_mocked=False) as router:
        lm_mock = ServiceMock(router, LM_EVAL_BASE_URL)
        bigcode_mock = ServiceMock(router, BIGCODE_EVAL_BASE_URL)
        yield {"lm_eval": lm_mock, "bigcode_eval": bigcode_mock}
