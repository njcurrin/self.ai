"""Unified GPU job queue — dispatches training and eval jobs one at a time.

Both eval and training jobs share the GPU. This module provides a single
background loop that:
  1. Syncs status of running eval jobs (polls bigcode-eval / lm-eval)
  2. Checks if *any* GPU job (eval OR training) is currently running
  3. If not, picks the next due scheduled or queued job from either table
     (ordered by scheduled_for / created_at) and dispatches it

The loop replaces the separate `process_eval_queue` and adds training
scheduling in a unified way.
"""

import asyncio
import logging
import time

from selfai_ui.env import SRC_LOG_LEVELS
from selfai_ui.models.eval_jobs import EvalJobs, EvalJobStatusUpdate
from selfai_ui.models.training import TrainingJobs, TrainingJobStatusUpdate

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", logging.INFO))

# Set by the lifespan handler so dispatchers can access app config.
_app_state = None


def _any_gpu_job_running() -> bool:
    """Return True if any eval or training job has status 'running'."""
    if EvalJobs.has_running_job():
        return True
    # Check training jobs
    from selfai_ui.models.training import TrainingJob
    from selfai_ui.internal.db import get_db

    try:
        with get_db() as db:
            running = db.query(TrainingJob).filter_by(status="running").first()
            if running is not None:
                return True
    except Exception:
        pass
    # Also count 'queued' training jobs as occupying the GPU — they are
    # dispatched to llamolotl which runs them serially. A queued training
    # job means llamolotl already has it and will start it soon.
    try:
        with get_db() as db:
            queued = db.query(TrainingJob).filter_by(status="queued").first()
            if queued is not None:
                return True
    except Exception:
        pass
    return False


async def _promote_scheduled_jobs() -> None:
    """Move due scheduled jobs → queued so they enter the dispatch pipeline."""
    # Eval jobs
    for job in EvalJobs.get_due_scheduled_jobs():
        log.info(f"GPU queue: eval job {job.id} is due (scheduled_for={job.scheduled_for}), promoting to queued")
        EvalJobs.update_job_status(
            id=job.id,
            update=EvalJobStatusUpdate(status="queued"),
        )

    # Training jobs
    for job in TrainingJobs.get_due_scheduled_jobs():
        log.info(f"GPU queue: training job {job.id} is due (scheduled_for={job.scheduled_for}), promoting to pending-dispatch")
        await _dispatch_training_job(job)


async def _dispatch_training_job(job) -> None:
    """Dispatch a scheduled training job to llamolotl (same logic as approve)."""
    global _app_state
    if _app_state is None:
        log.warning("GPU queue: app state not set, cannot dispatch training job")
        TrainingJobs.update_job_status(
            id=job.id,
            update=TrainingJobStatusUpdate(
                status="failed",
                error_message="Internal error: app state not available",
            ),
        )
        return

    # Import here to avoid circular imports
    from selfai_ui.routers.training import _dispatch_scheduled_job
    await _dispatch_scheduled_job(job)


async def _dispatch_next_queued() -> None:
    """Find the next queued job (eval or training) and dispatch it.

    Picks the oldest queued job across both tables.
    """
    next_eval = EvalJobs.get_next_queued_job()
    next_training = _get_next_queued_training_job()

    if not next_eval and not next_training:
        return

    # Pick whichever was created first
    pick_eval = False
    if next_eval and next_training:
        pick_eval = next_eval.created_at <= next_training.created_at
    elif next_eval:
        pick_eval = True

    if pick_eval:
        from selfai_ui.routers.evaluations import (
            _dispatch_eval_job,
            _dispatch_lm_eval_job,
        )

        eval_type = getattr(next_eval, "eval_type", "bigcode") or "bigcode"
        log.info(f"GPU queue: dispatching {eval_type} eval job {next_eval.id}")
        if eval_type == "lm-eval":
            await _dispatch_lm_eval_job(next_eval)
        else:
            await _dispatch_eval_job(next_eval)
    else:
        log.info(f"GPU queue: dispatching training job {next_training.id}")
        await _dispatch_training_job(next_training)


def _get_next_queued_training_job():
    """Return the oldest training job with status 'queued', or None.

    Note: training jobs go pending → queued via approve, which already
    dispatches to llamolotl. For scheduled jobs, they go scheduled →
    dispatched (which sets queued). So normally there won't be orphan
    queued training jobs, but this handles edge cases.
    """
    from selfai_ui.models.training import TrainingJob
    from selfai_ui.internal.db import get_db

    try:
        with get_db() as db:
            job = (
                db.query(TrainingJob)
                .filter_by(status="queued")
                .order_by(TrainingJob.created_at.asc())
                .first()
            )
            if job:
                from selfai_ui.models.training import TrainingJobModel
                return TrainingJobModel.model_validate(job)
    except Exception:
        pass
    return None


async def process_gpu_queue() -> None:
    """Main background loop — replaces process_eval_queue.

    Polls every 10 seconds.
    """
    while True:
        try:
            # 1. Sync running eval jobs with their remote services
            from selfai_ui.routers.evaluations import _sync_running_jobs
            await _sync_running_jobs()

            # 2. Promote any due scheduled jobs
            await _promote_scheduled_jobs()

            # 3. If nothing is running, dispatch the next queued job
            if not _any_gpu_job_running():
                await _dispatch_next_queued()

        except Exception as e:
            log.error(f"GPU queue processor error: {e}")

        await asyncio.sleep(10)
