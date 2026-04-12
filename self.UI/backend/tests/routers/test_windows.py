"""T-317 + T-318: Job Windows router CRUD and validation tests."""

import time
import pytest


def _future_window(name="test-window", offset=3600, duration=7200):
    """Build a window form starting in the future."""
    start = int(time.time()) + offset
    return {
        "name": name,
        "notes": "test",
        "start_at": start,
        "end_at": start + duration,
        "preferred_job_type": "training",
        "enabled": True,
        "slots": [
            {"job_type": "training", "max_concurrent": 1, "min_remaining_minutes": 0}
        ],
    }


@pytest.mark.tier0
def test_list_windows_empty(authenticated_admin):
    resp = authenticated_admin.get("/api/windows")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.tier0
def test_create_window(authenticated_admin):
    resp = authenticated_admin.post("/api/windows", json=_future_window())
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "test-window"
    assert len(body["slots"]) == 1


@pytest.mark.tier0
def test_create_window_invalid_times_rejected(authenticated_admin):
    """end_at before start_at returns 400."""
    w = _future_window()
    w["end_at"] = w["start_at"] - 100
    resp = authenticated_admin.post("/api/windows", json=w)
    assert resp.status_code == 400


@pytest.mark.tier0
def test_get_window_by_id(authenticated_admin):
    created = authenticated_admin.post(
        "/api/windows", json=_future_window("fetch-me")
    ).json()
    resp = authenticated_admin.get(f"/api/windows/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "fetch-me"


@pytest.mark.tier0
def test_get_window_not_found(authenticated_admin):
    resp = authenticated_admin.get("/api/windows/nonexistent-window")
    assert resp.status_code == 404


@pytest.mark.tier0
def test_update_window(authenticated_admin):
    created = authenticated_admin.post(
        "/api/windows", json=_future_window("old-name")
    ).json()
    updated = _future_window("new-name")
    resp = authenticated_admin.put(
        f"/api/windows/{created['id']}", json=updated
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "new-name"


@pytest.mark.tier0
def test_delete_window(authenticated_admin):
    created = authenticated_admin.post(
        "/api/windows", json=_future_window("del-me")
    ).json()
    resp = authenticated_admin.delete(f"/api/windows/{created['id']}")
    assert resp.status_code == 200


@pytest.mark.tier0
def test_update_window_slots_replaced(authenticated_admin):
    """Updating a window with a new slot set replaces the slots."""
    created = authenticated_admin.post(
        "/api/windows", json=_future_window("slot-test")
    ).json()
    # New config with different slots
    updated = _future_window("slot-test")
    updated["slots"] = [
        {"job_type": "training", "max_concurrent": 2, "min_remaining_minutes": 10},
        {"job_type": "eval", "max_concurrent": 1, "min_remaining_minutes": 5},
    ]
    resp = authenticated_admin.put(
        f"/api/windows/{created['id']}", json=updated
    )
    assert resp.status_code == 200
    assert len(resp.json()["slots"]) == 2


@pytest.mark.tier0
def test_user_cannot_access_windows(authenticated_user):
    resp = authenticated_user.get("/api/windows")
    assert resp.status_code in (401, 403)
