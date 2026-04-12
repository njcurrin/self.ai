"""
T-R03 (part 3): Curator proxy forwarding.

Curator router uses aiohttp for verify + job submission upstream calls.
"""

import pytest
from aioresponses import aioresponses


@pytest.mark.tier1
def test_curator_verify_success(authenticated_admin):
    """POST /curator/verify returns the upstream /health body on 200."""
    target = "http://self-curator:8000"
    with aioresponses() as m:
        m.get(
            f"{target}/health",
            status=200,
            payload={"status": "healthy", "version": "1.0"},
        )
        resp = authenticated_admin.post(
            "/curator/verify", json={"url": target}
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.tier1
def test_curator_verify_upstream_error_becomes_500(authenticated_admin):
    target = "http://self-curator:8000"
    with aioresponses() as m:
        m.get(
            f"{target}/health",
            status=503,
            payload={"error": "service down"},
        )
        resp = authenticated_admin.post(
            "/curator/verify", json={"url": target}
        )
    assert resp.status_code == 500


@pytest.mark.tier1
def test_curator_verify_strips_trailing_slash(authenticated_admin):
    """Router strips trailing slash before probing /health."""
    target = "http://self-curator:8000"
    with aioresponses() as m:
        m.get(f"{target}/health", status=200, payload={"ok": True})
        resp = authenticated_admin.post(
            "/curator/verify", json={"url": target + "/"}
        )
    assert resp.status_code == 200


@pytest.mark.tier1
def test_curator_config_update_persists(authenticated_admin):
    """Config update round-trip using current config shape succeeds."""
    current = authenticated_admin.get("/curator/config").json()
    resp = authenticated_admin.post("/curator/config/update", json=current)
    assert resp.status_code == 200, (
        f"Config round-trip returned {resp.status_code}: {resp.text[:200]}"
    )
