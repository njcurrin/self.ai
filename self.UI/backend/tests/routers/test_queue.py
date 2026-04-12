"""T-319: Queue router tests."""

import pytest


@pytest.mark.tier0
def test_queue_empty(authenticated_admin):
    resp = authenticated_admin.get("/api/queue")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.tier0
def test_user_cannot_access_queue(authenticated_user):
    resp = authenticated_user.get("/api/queue")
    assert resp.status_code in (401, 403)


@pytest.mark.tier0
def test_queue_with_pending_jobs_shows_them(
    authenticated_admin, db_session, test_admin
):
    """A pending curator job appears in the queue."""
    from selfai_ui.models.curator_jobs import CuratorJob
    import uuid, time

    job = CuratorJob(
        id=str(uuid.uuid4()),
        user_id=test_admin["id"],
        pipeline_id="test-pipeline",
        status="pending",
        priority="normal",
        meta={"name": "q-test"},
        created_at=int(time.time()),
        updated_at=int(time.time()),
    )
    db_session.add(job)
    db_session.commit()

    resp = authenticated_admin.get("/api/queue")
    assert resp.status_code == 200
    body = resp.json()
    assert any(item.get("id") == job.id for item in body)


@pytest.mark.tier0
def test_run_now_nonexistent_job_rejected(authenticated_admin):
    resp = authenticated_admin.post(
        "/api/jobs/curator/nonexistent-id/run-now"
    )
    assert resp.status_code in (400, 404)


@pytest.mark.tier0
def test_promote_nonexistent_job_rejected(authenticated_admin):
    resp = authenticated_admin.post(
        "/api/jobs/curator/nonexistent-id/promote"
    )
    assert resp.status_code in (400, 404)
