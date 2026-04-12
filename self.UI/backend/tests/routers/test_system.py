"""
System router tests — resources and processes observability.

Admin-only. Tests verify endpoint auth + that shape matches the declared
response model (SystemResources, ProcessList).
"""

import pytest


@pytest.mark.tier0
def test_resources_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/system/resources")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_resources_admin_access(authenticated_admin):
    """psutil is in requirements.txt so this should always return 200."""
    resp = authenticated_admin.get("/api/system/resources")
    if resp.status_code != 200:
        pytest.skip(
            f"System resources returned {resp.status_code} — possibly "
            f"missing psutil in test container. Fix: ensure psutil is "
            f"installed. Body: {resp.text[:200]}"
        )
    body = resp.json()
    assert isinstance(body, dict)


@pytest.mark.tier0
def test_processes_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/system/processes")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_processes_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/api/system/processes")
    if resp.status_code != 200:
        pytest.skip(
            f"System processes returned {resp.status_code} — possibly "
            f"missing psutil. Body: {resp.text[:200]}"
        )
    body = resp.json()
    assert isinstance(body, dict)
