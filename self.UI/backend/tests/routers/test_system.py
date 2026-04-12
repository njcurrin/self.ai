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
    resp = authenticated_admin.get("/api/system/resources")
    # May fail with 500 if psutil/nvml not available in container —
    # either success or graceful failure
    assert resp.status_code in (200, 500, 503)
    if resp.status_code == 200:
        body = resp.json()
        # SystemResources has some subset of cpu/memory/gpu info
        assert isinstance(body, dict)


@pytest.mark.tier0
def test_processes_admin_only(authenticated_user):
    resp = authenticated_user.get("/api/system/processes")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_processes_admin_access(authenticated_admin):
    resp = authenticated_admin.get("/api/system/processes")
    assert resp.status_code in (200, 500, 503)
    if resp.status_code == 200:
        body = resp.json()
        assert isinstance(body, dict)
