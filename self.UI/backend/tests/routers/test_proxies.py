"""
T-327 through T-334: External service proxy router smoke tests.

These routers proxy to external services. Detailed streaming/forwarding
tests would require extensive respx setup; here we focus on:
- Status/health endpoints (unauthenticated where appropriate)
- Config get/set (admin-gated)
- Auth enforcement
"""

import pytest


# ---------------------------------------------------------------------------
# T-327: Ollama proxy
# ---------------------------------------------------------------------------

@pytest.mark.tier0
def test_ollama_status_unauthenticated(client):
    """GET /ollama/ is an unauthenticated health check."""
    resp = client.get("/ollama/")
    # 200 if Ollama configured, 500/502 if not reachable — both acceptable
    assert resp.status_code in (200, 500, 502)


@pytest.mark.tier0
def test_ollama_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/ollama/config")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_ollama_config_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/ollama/config")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# T-328: OpenAI proxy
# ---------------------------------------------------------------------------

@pytest.mark.tier0
def test_openai_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/openai/config")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_openai_config_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/openai/config")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# T-329: Llamolotl proxy
# ---------------------------------------------------------------------------

@pytest.mark.tier0
def test_llamolotl_status_unauthenticated(client):
    """GET /llamolotl/ is an unauthenticated health check."""
    resp = client.get("/llamolotl/")
    # Upstream may or may not be reachable in test env
    assert resp.status_code in (200, 500, 502, 503)


@pytest.mark.tier0
def test_llamolotl_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/llamolotl/config")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_llamolotl_config_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/llamolotl/config")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# T-330: Curator proxy
# ---------------------------------------------------------------------------

@pytest.mark.tier0
def test_curator_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/curator/config")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_curator_config_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/curator/config")
    assert resp.status_code in (200, 502, 503)


# ---------------------------------------------------------------------------
# T-331: Audio (STT/TTS)
# ---------------------------------------------------------------------------

@pytest.mark.tier0
def test_audio_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/v1/audio/config")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_audio_config_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/api/v1/audio/config")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# T-332: Images
# ---------------------------------------------------------------------------

@pytest.mark.tier0
def test_images_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/v1/images/config")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_images_config_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/api/v1/images/config")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# T-333: Retrieval (config moved behind auth in T-205 fixes)
# ---------------------------------------------------------------------------

@pytest.mark.tier0
def test_retrieval_status_requires_admin(authenticated_user):
    """Retrieval status was moved behind admin auth in security fixes."""
    resp = authenticated_user.get("/api/v1/retrieval/")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_retrieval_status_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/api/v1/retrieval/")
    assert resp.status_code == 200


@pytest.mark.tier0
def test_retrieval_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/v1/retrieval/config")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# T-334: Eval proxies (lm-eval + bigcode-eval)
# ---------------------------------------------------------------------------

@pytest.mark.tier0
def test_lm_eval_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/lm-eval/config")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_lm_eval_config_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/lm-eval/config")
    assert resp.status_code == 200


@pytest.mark.tier0
def test_bigcode_eval_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/bigcode-eval/config")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_bigcode_eval_config_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/bigcode-eval/config")
    assert resp.status_code == 200
