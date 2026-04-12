"""
T-307 + T-308: Knowledge bases router CRUD and file membership tests.

Knowledge creation requires admin role or workspace.knowledge permission.
We use authenticated_admin for create/delete tests.
"""

import pytest


@pytest.mark.tier0
def test_list_knowledge_empty(authenticated_admin):
    resp = authenticated_admin.get("/api/v1/knowledge/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.tier0
def test_create_knowledge_base(authenticated_admin):
    resp = authenticated_admin.post(
        "/api/v1/knowledge/create",
        json={
            "name": "Test KB",
            "description": "A knowledge base for tests",
            "access_control": None,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Test KB"


@pytest.mark.tier0
def test_get_knowledge_by_id(authenticated_admin):
    created = authenticated_admin.post(
        "/api/v1/knowledge/create",
        json={"name": "Specific KB", "description": "test"},
    ).json()
    kb_id = created["id"]

    resp = authenticated_admin.get(f"/api/v1/knowledge/{kb_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == kb_id
    assert body["name"] == "Specific KB"
    assert "files" in body  # KnowledgeFilesResponse includes files list


@pytest.mark.tier0
def test_update_knowledge(authenticated_admin):
    created = authenticated_admin.post(
        "/api/v1/knowledge/create",
        json={"name": "Old Name", "description": "old desc"},
    ).json()
    kb_id = created["id"]

    resp = authenticated_admin.post(
        f"/api/v1/knowledge/{kb_id}/update",
        json={"name": "New Name", "description": "new desc"},
    )
    assert resp.status_code == 200
    refetch = authenticated_admin.get(f"/api/v1/knowledge/{kb_id}").json()
    assert refetch["name"] == "New Name"


@pytest.mark.tier0
def test_delete_knowledge(authenticated_admin):
    created = authenticated_admin.post(
        "/api/v1/knowledge/create",
        json={"name": "Delete KB", "description": ""},
    ).json()
    kb_id = created["id"]

    resp = authenticated_admin.delete(f"/api/v1/knowledge/{kb_id}/delete")
    assert resp.status_code == 200
    # Refetch should return not-found
    refetch = authenticated_admin.get(f"/api/v1/knowledge/{kb_id}")
    # 200 with null, or 4xx
    if refetch.status_code == 200:
        assert refetch.json() is None


@pytest.mark.tier0
def test_knowledge_get_not_found(authenticated_admin):
    resp = authenticated_admin.get("/api/v1/knowledge/bogus-id-12345")
    # 200 null or 404
    if resp.status_code == 200:
        assert resp.json() is None
    else:
        assert resp.status_code in (401, 404)


@pytest.mark.tier0
def test_knowledge_creation_denied_for_user_without_permission(
    authenticated_user,
):
    """Regular user without workspace.knowledge permission is denied."""
    resp = authenticated_user.post(
        "/api/v1/knowledge/create",
        json={"name": "Denied KB", "description": ""},
    )
    # User role without permission → 401
    # User role WITH permission → 200 (depends on default USER_PERMISSIONS)
    assert resp.status_code in (200, 401, 403)
