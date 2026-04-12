"""
T-302 + T-303: Channels router CRUD + message operations.

Channels are admin-created. Users can list channels they're members of.
Messages can be posted by verified users, with reactions and threads.
"""

import pytest


@pytest.mark.tier0
def test_list_channels_empty_for_user(authenticated_user):
    resp = authenticated_user.get("/api/v1/channels/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.tier0
def test_create_channel_user_forbidden(authenticated_user):
    """User-role cannot create channels."""
    resp = authenticated_user.post(
        "/api/v1/channels/create",
        json={"name": "user-channel", "description": "test"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_create_channel_admin_succeeds(authenticated_admin):
    """Admin creates a channel."""
    resp = authenticated_admin.post(
        "/api/v1/channels/create",
        json={"name": "admin-channel", "description": "test"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "admin-channel"


@pytest.mark.tier0
def test_update_channel(authenticated_admin):
    created = authenticated_admin.post(
        "/api/v1/channels/create",
        json={"name": "original", "description": ""},
    ).json()
    resp = authenticated_admin.post(
        f"/api/v1/channels/{created['id']}/update",
        json={"name": "updated", "description": "new"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "updated"


@pytest.mark.tier0
def test_delete_channel(authenticated_admin):
    created = authenticated_admin.post(
        "/api/v1/channels/create",
        json={"name": "to-delete", "description": ""},
    ).json()
    resp = authenticated_admin.delete(
        f"/api/v1/channels/{created['id']}/delete"
    )
    assert resp.status_code == 200


@pytest.mark.tier0
def test_post_message_to_channel(authenticated_admin):
    """Admin posts a message to a channel."""
    channel = authenticated_admin.post(
        "/api/v1/channels/create",
        json={"name": "msg-channel", "description": ""},
    ).json()
    resp = authenticated_admin.post(
        f"/api/v1/channels/{channel['id']}/messages/post",
        json={"content": "Hello channel", "data": {}},
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Hello channel"


@pytest.mark.tier0
def test_list_channel_messages(authenticated_admin):
    channel = authenticated_admin.post(
        "/api/v1/channels/create",
        json={"name": "list-msgs", "description": ""},
    ).json()
    authenticated_admin.post(
        f"/api/v1/channels/{channel['id']}/messages/post",
        json={"content": "msg1", "data": {}},
    )
    authenticated_admin.post(
        f"/api/v1/channels/{channel['id']}/messages/post",
        json={"content": "msg2", "data": {}},
    )
    resp = authenticated_admin.get(f"/api/v1/channels/{channel['id']}/messages")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 2
    contents = [m["content"] for m in body]
    assert "msg1" in contents
    assert "msg2" in contents
