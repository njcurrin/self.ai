"""
Pipelines router smoke tests.

Pipelines is an admin-only proxy layer for OpenAI-compatible pipeline
endpoints. Tests focus on auth enforcement and reasonable behavior when
upstream is not configured.
"""

import pytest


@pytest.mark.tier0
def test_list_pipelines_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/v1/pipelines/list")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_list_pipelines_admin_access(authenticated_admin):
    """Admin can reach the endpoint; may return empty data if no pipeline
    upstream is configured."""
    resp = authenticated_admin.get("/api/v1/pipelines/list")
    # Either 200 with data or 502/503 if upstream unreachable
    assert resp.status_code in (200, 500, 502, 503)
    if resp.status_code == 200:
        body = resp.json()
        assert "data" in body
        assert isinstance(body["data"], list)


@pytest.mark.tier0
def test_get_pipelines_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/v1/pipelines/")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_upload_pipeline_admin_only(authenticated_user):
    import io
    resp = authenticated_user.post(
        "/api/v1/pipelines/upload",
        files={"file": ("bogus.py", io.BytesIO(b"pass"), "text/x-python")},
        data={"urlIdx": "0"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_delete_pipeline_admin_only(authenticated_user):
    resp = authenticated_user.delete(
        "/api/v1/pipelines/delete",
        params={"id": "x", "urlIdx": 0},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_add_pipeline_admin_only(authenticated_user):
    resp = authenticated_user.post(
        "/api/v1/pipelines/add",
        json={"url": "https://example.com/p.py", "urlIdx": 0},
    )
    assert resp.status_code in (401, 403)
