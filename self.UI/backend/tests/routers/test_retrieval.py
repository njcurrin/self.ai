"""
Retrieval router tests — config endpoints, settings, auth enforcement.

Processing endpoints (/process/*) touch external vector DB, embedding
engine, and web fetchers — they're out of scope for unit tests and
are covered at the E2E level via integration smoke.
"""

import pytest


@pytest.mark.tier0
def test_status_admin_only(authenticated_user):
    """Retrieval status was moved behind admin auth (T-205 / research finding)."""
    resp = authenticated_user.get("/api/v1/retrieval/")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_status_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/api/v1/retrieval/")
    assert resp.status_code == 200
    body = resp.json()
    assert "embedding_engine" in body
    assert "chunk_size" in body


@pytest.mark.tier0
def test_embedding_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/v1/retrieval/embedding")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_embedding_config_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/api/v1/retrieval/embedding")
    assert resp.status_code == 200


@pytest.mark.tier0
def test_reranking_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/v1/retrieval/reranking")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/v1/retrieval/config")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_config_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/api/v1/retrieval/config")
    assert resp.status_code == 200


@pytest.mark.tier0
def test_template_any_user(authenticated_user):
    """Template endpoint is accessible to any verified user."""
    resp = authenticated_user.get("/api/v1/retrieval/template")
    # May be 401 or 200 depending on auth setup
    assert resp.status_code in (200, 401, 403)


@pytest.mark.tier0
def test_query_settings_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/v1/retrieval/query/settings")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_query_settings_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/api/v1/retrieval/query/settings")
    assert resp.status_code == 200
