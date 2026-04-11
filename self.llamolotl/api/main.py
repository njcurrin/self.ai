"""
FastAPI server for controlling training jobs (HF Trainer + DeepSpeed + PEFT).
Runs on port 8093, manages job lifecycle and progress monitoring.
"""

import asyncio

from fastapi import FastAPI

from .state import (
    API_VERSION,
    _ensure_dirs,
    _load_jobs,
    _load_pipeline_tasks,
    _poll_jobs,
    _try_start_next_pending,
)
from .routers import jobs, models, pipeline, system

app = FastAPI(title="Training API", version=API_VERSION)

app.include_router(jobs.router)
app.include_router(models.router)
app.include_router(pipeline.router)
app.include_router(system.router)


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    _ensure_dirs()
    _load_jobs()
    _load_pipeline_tasks()
    # Start any pending jobs that were queued before restart
    _try_start_next_pending()
    asyncio.create_task(_poll_jobs())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8093, log_level="info")
