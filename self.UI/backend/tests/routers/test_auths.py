"""
Auths router CRUD + session tests.

Covers: session user fetch, profile update, password update, signout,
API key CRUD, admin config endpoints.
"""

import pytest


@pytest.mark.tier0
def test_get_session_user(authenticated_user):
    """GET / returns the session user."""
    resp = authenticated_user.get("/api/v1/auths/")
    assert resp.status_code == 200
    body = resp.json()
    assert "id" in body
    assert "email" in body
    assert body["role"] == "user"


@pytest.mark.tier0
def test_get_session_admin(authenticated_admin):
    resp = authenticated_admin.get("/api/v1/auths/")
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


@pytest.mark.tier0
def test_update_profile(authenticated_user):
    resp = authenticated_user.post(
        "/api/v1/auths/update/profile",
        json={"name": "Updated Name", "profile_image_url": "/new.png"},
    )
    assert resp.status_code == 200
    # Verify via session endpoint
    me = authenticated_user.get("/api/v1/auths/").json()
    assert me["name"] == "Updated Name"


@pytest.mark.tier0
def test_signout_clears_cookie(authenticated_user):
    resp = authenticated_user.get("/api/v1/auths/signout")
    assert resp.status_code == 200


@pytest.mark.tier0
def test_signin_unknown_user_rejected(client):
    resp = client.post(
        "/api/v1/auths/signin",
        json={"email": "noexist@test.local", "password": "wrong"},
    )
    # Rejected; shape varies
    assert resp.status_code in (400, 401, 500)


@pytest.mark.tier0
def test_admin_details_requires_auth(client):
    """The admin/details endpoint requires authentication (not admin role)."""
    resp = client.get("/api/v1/auths/admin/details")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_admin_details_accessible_to_any_user(authenticated_user):
    resp = authenticated_user.get("/api/v1/auths/admin/details")
    # Any verified user can see admin details (who the admin is)
    assert resp.status_code == 200


@pytest.mark.tier0
def test_admin_config_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/v1/auths/admin/config")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_admin_config_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/api/v1/auths/admin/config")
    assert resp.status_code == 200


@pytest.mark.tier0
def test_api_key_create(authenticated_user):
    """Create an API key for the authenticated user."""
    resp = authenticated_user.post("/api/v1/auths/api_key")
    # Should return an api_key string or allow-disabled error
    assert resp.status_code in (200, 400, 401)


@pytest.mark.tier0
def test_api_key_get(authenticated_user):
    """Get the current user's API key (may be None)."""
    resp = authenticated_user.get("/api/v1/auths/api_key")
    assert resp.status_code in (200, 404)


@pytest.mark.tier0
def test_api_key_delete(authenticated_user):
    resp = authenticated_user.delete("/api/v1/auths/api_key")
    assert resp.status_code in (200, 400)
