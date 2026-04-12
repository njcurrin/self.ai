"""
T-R03 (part 1): lm-eval + bigcode-eval verify endpoint forwarding.

Both verify endpoints use aiohttp.ClientSession to GET {url}/health
on the provided URL. Tests use aioresponses to mock the upstream.
"""

import pytest
from aioresponses import aioresponses


@pytest.mark.tier1
def test_lm_eval_verify_success(authenticated_admin):
    """A 200 from upstream /health returns the JSON body to the caller."""
    target = "http://self-lm-eval:5000"
    with aioresponses() as m:
        m.get(f"{target}/health", status=200, payload={"status": "healthy"})
        resp = authenticated_admin.post(
            "/lm-eval/verify", json={"url": target}
        )
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


@pytest.mark.tier1
def test_lm_eval_verify_upstream_non_200_becomes_500(authenticated_admin):
    """Upstream 503 is caught and converted to 500 per router code."""
    target = "http://self-lm-eval:5000"
    with aioresponses() as m:
        m.get(f"{target}/health", status=503, payload={"error": "down"})
        resp = authenticated_admin.post(
            "/lm-eval/verify", json={"url": target}
        )
    assert resp.status_code == 500


@pytest.mark.tier1
def test_bigcode_eval_verify_success(authenticated_admin):
    target = "http://self-bigcode-eval:5001"
    with aioresponses() as m:
        m.get(f"{target}/health", status=200, payload={"status": "ok"})
        resp = authenticated_admin.post(
            "/bigcode-eval/verify", json={"url": target}
        )
    assert resp.status_code == 200


@pytest.mark.tier1
def test_bigcode_eval_verify_upstream_non_200_becomes_500(authenticated_admin):
    target = "http://self-bigcode-eval:5001"
    with aioresponses() as m:
        m.get(f"{target}/health", status=404, payload={"error": "missing"})
        resp = authenticated_admin.post(
            "/bigcode-eval/verify", json={"url": target}
        )
    assert resp.status_code == 500


@pytest.mark.tier1
def test_lm_eval_config_update_persists(authenticated_admin):
    """PUT /lm-eval/config/update persists ENABLE_LM_EVAL_API and base URLs."""
    resp = authenticated_admin.post(
        "/lm-eval/config/update",
        json={
            "ENABLE_LM_EVAL_API": True,
            "LM_EVAL_BASE_URLS": ["http://self-lm-eval:5000"],
        },
    )
    assert resp.status_code == 200
    # Re-fetch to verify persistence
    refetch = authenticated_admin.get("/lm-eval/config").json()
    assert refetch["ENABLE_LM_EVAL_API"] is True
    assert "http://self-lm-eval:5000" in refetch["LM_EVAL_BASE_URLS"]


@pytest.mark.tier1
def test_bigcode_eval_config_update_persists(authenticated_admin):
    resp = authenticated_admin.post(
        "/bigcode-eval/config/update",
        json={
            "ENABLE_BIGCODE_EVAL_API": True,
            "BIGCODE_EVAL_BASE_URLS": ["http://self-bigcode-eval:5001"],
        },
    )
    assert resp.status_code == 200
    refetch = authenticated_admin.get("/bigcode-eval/config").json()
    assert refetch["ENABLE_BIGCODE_EVAL_API"] is True
    assert "http://self-bigcode-eval:5001" in refetch["BIGCODE_EVAL_BASE_URLS"]
