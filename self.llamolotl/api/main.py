"""
FastAPI server for controlling axolotl fine-tuning jobs.
Runs on port 8093, manages job lifecycle and progress monitoring.
"""

import asyncio
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ─── Constants ──────────────────────────────────────────────────────────

WORKSPACE = Path("/workspace/axolotl")
CONFIGS_DIR = WORKSPACE / "configs"
OUTPUTS_DIR = WORKSPACE / "outputs"
LOGS_DIR = WORKSPACE / "logs"
JOBS_STATE_FILE = WORKSPACE / "jobs.json"
VENV_BIN = Path("/opt/venv/bin")
ACCELERATE = VENV_BIN / "accelerate"
PYTHON = VENV_BIN / "python"

API_VERSION = "1.0.0"

# ─── Enums and Models ───────────────────────────────────────────────────

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobCreate(BaseModel):
    config_path: Optional[str] = None
    config_inline: Optional[str] = None
    overrides: Optional[Dict[str, Any]] = None

    class Config:
        example = {
            "config_path": "my-config",
            "overrides": {"lora_r": 64, "num_epochs": 2},
        }


class Job(BaseModel):
    job_id: str
    status: JobStatus
    config_path: str
    output_dir: str
    pid: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    log_file: str
    metrics: List[Dict[str, Any]] = []
    error_message: Optional[str] = None


class ConfigCreate(BaseModel):
    name: str
    content: str


class HealthResponse(BaseModel):
    status: str
    running_jobs: int
    jobs_total: int
    api_version: str


# ─── State ──────────────────────────────────────────────────────────────

_jobs: Dict[str, Job] = {}
_processes: Dict[str, subprocess.Popen] = {}

app = FastAPI(title="Axolotl Training API", version=API_VERSION)


# ─── Initialization ─────────────────────────────────────────────────────

def _ensure_dirs():
    """Create all required directories."""
    for d in [CONFIGS_DIR, OUTPUTS_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _load_jobs():
    """Load job state from JSON file."""
    global _jobs
    if JOBS_STATE_FILE.exists():
        data = json.loads(JOBS_STATE_FILE.read_text())
        for job_id, job_data in data.items():
            try:
                job_data["created_at"] = datetime.fromisoformat(
                    job_data["created_at"]
                )
                if job_data.get("started_at"):
                    job_data["started_at"] = datetime.fromisoformat(
                        job_data["started_at"]
                    )
                if job_data.get("finished_at"):
                    job_data["finished_at"] = datetime.fromisoformat(
                        job_data["finished_at"]
                    )
                job = Job(**job_data)
                # Mark any RUNNING jobs as FAILED (process lost on restart)
                if job.status == JobStatus.RUNNING:
                    job.status = JobStatus.FAILED
                    job.error_message = "Process lost on restart"
                    job.finished_at = datetime.now()
                _jobs[job_id] = job
            except Exception as e:
                print(f"Failed to load job {job_id}: {e}")


def _save_jobs():
    """Persist job state to JSON file (atomic write)."""
    tmp = JOBS_STATE_FILE.with_suffix(".tmp")
    data = {jid: j.model_dump(mode="json") for jid, j in _jobs.items()}
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(JOBS_STATE_FILE)


def _refresh_metrics(job: Job):
    """Read latest metrics from trainer_state.json."""
    try:
        output_path = Path(job.output_dir)
        checkpoints = sorted(output_path.glob("checkpoint-*/trainer_state.json"))
        if checkpoints:
            data = json.loads(checkpoints[-1].read_text())
            job.metrics = data.get("log_history", [])
    except Exception:
        pass


def _extract_output_dir(config_path: Path, overrides: Optional[Dict]) -> str:
    """Extract and resolve output_dir from config YAML."""
    try:
        config_data = yaml.safe_load(config_path.read_text())
        output_dir = config_data.get("output_dir")
        # Override takes precedence
        if overrides and "output_dir" in overrides:
            output_dir = overrides["output_dir"]
    except Exception:
        output_dir = None

    if not output_dir:
        output_dir = "outputs"

    output_path = Path(output_dir)
    if not output_path.is_absolute():
        output_path = WORKSPACE / output_path

    return str(output_path)


def _build_override_args(overrides: Optional[Dict]) -> List[str]:
    """Convert override dict to CLI args."""
    if not overrides:
        return []
    return [
        f"--{k.replace('_', '-')}={v}" for k, v in overrides.items()
    ]


async def _poll_jobs():
    """Background task: poll job status every 5 seconds."""
    while True:
        await asyncio.sleep(5)
        for job_id, job in list(_jobs.items()):
            if job.status != JobStatus.RUNNING:
                continue

            proc = _processes.get(job_id)
            if not proc:
                continue

            rc = proc.poll()
            if rc is not None:
                # Process finished
                job.exit_code = rc
                job.finished_at = datetime.now()
                job.status = (
                    JobStatus.COMPLETED if rc == 0 else JobStatus.FAILED
                )
                if rc != 0:
                    job.error_message = f"Process exited with code {rc}"
                del _processes[job_id]

            # Refresh metrics
            _refresh_metrics(job)
            _save_jobs()


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    _ensure_dirs()
    _load_jobs()
    asyncio.create_task(_poll_jobs())


# ─── Jobs Endpoints ────────────────────────────────────────────────────

@app.post("/api/jobs", status_code=201)
def create_job(req: JobCreate) -> Job:
    """Start a new training job."""
    # Check if any job is already running
    for job in _jobs.values():
        if job.status == JobStatus.RUNNING:
            raise HTTPException(
                status_code=409,
                detail=f"A training job is already running (job_id: {job.job_id})",
            )

    # Validate config input
    if not req.config_path and not req.config_inline:
        raise HTTPException(
            status_code=400,
            detail="Either config_path or config_inline must be provided",
        )
    if req.config_path and req.config_inline:
        raise HTTPException(
            status_code=400,
            detail="Only one of config_path or config_inline should be provided",
        )

    job_id = str(uuid.uuid4())[:8]
    overrides = req.overrides or {}

    # Resolve config path
    if req.config_inline:
        config_path = CONFIGS_DIR / f"job-{job_id}.yaml"
        try:
            config_path.write_text(req.config_inline)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")
    else:
        config_path = CONFIGS_DIR / f"{req.config_path}.yaml"
        if not config_path.exists():
            raise HTTPException(status_code=404, detail="Config file not found")

    # Extract output dir
    output_dir = _extract_output_dir(config_path, overrides)

    # Build command
    override_args = _build_override_args(overrides)
    cmd = [
        str(ACCELERATE),
        "launch",
        "-m",
        "axolotl.cli.train",
        str(config_path),
    ] + override_args

    # Open log file
    log_file = LOGS_DIR / f"{job_id}.log"
    try:
        log_fh = open(log_file, "w")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open log: {e}")

    # Launch process
    env = os.environ.copy()
    env["PATH"] = f"{VENV_BIN}:{env.get('PATH', '')}"
    env["PYTHONUNBUFFERED"] = "1"

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=str(WORKSPACE),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start training: {e}",
        )

    # Create job record
    job = Job(
        job_id=job_id,
        status=JobStatus.RUNNING,
        config_path=str(config_path),
        output_dir=output_dir,
        pid=proc.pid,
        created_at=datetime.now(),
        started_at=datetime.now(),
        log_file=str(log_file),
    )

    _jobs[job_id] = job
    _processes[job_id] = proc
    _save_jobs()

    return job


@app.get("/api/jobs")
def list_jobs() -> List[Job]:
    """List all jobs."""
    for job in _jobs.values():
        if job.status == JobStatus.RUNNING:
            _refresh_metrics(job)
    return sorted(_jobs.values(), key=lambda j: j.created_at, reverse=True)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> Job:
    """Get job details."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == JobStatus.RUNNING:
        _refresh_metrics(job)
    return job


@app.get("/api/jobs/{job_id}/logs")
async def get_job_logs(
    job_id: str, tail: int = Query(100), stream: bool = Query(False)
):
    """Get job logs."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    log_path = Path(job.log_file)
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    if not stream:
        # Return last N lines
        try:
            lines = log_path.read_text().splitlines()
            return {"lines": lines[-tail:]}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Stream response
    async def generate():
        async with aiofiles.open(log_path, "r") as f:
            # Seek to end for live tailing
            await f.seek(0, 2)
            while True:
                line = await f.readline()
                if line:
                    yield line
                else:
                    await asyncio.sleep(0.3)

    return StreamingResponse(generate(), media_type="text/plain")


@app.delete("/api/jobs/{job_id}")
def cancel_job(job_id: str):
    """Cancel a running job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Job is not running")

    proc = _processes.get(job_id)
    if proc:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        del _processes[job_id]

    job.status = JobStatus.CANCELLED
    job.finished_at = datetime.now()
    _save_jobs()

    return {"status": "cancelled", "job_id": job_id}


# ─── Config Endpoints ──────────────────────────────────────────────────

@app.post("/api/configs", status_code=201)
def create_config(req: ConfigCreate):
    """Save a new config file."""
    # Validate name
    if not req.name or "/" in req.name or "\\" in req.name:
        raise HTTPException(status_code=400, detail="Invalid config name")

    config_path = CONFIGS_DIR / f"{req.name}.yaml"
    if config_path.exists():
        raise HTTPException(status_code=409, detail="Config already exists")

    try:
        config_path.write_text(req.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

    return {"name": req.name, "created": True}


@app.get("/api/configs")
def list_configs():
    """List all saved configs."""
    configs = []
    for path in sorted(CONFIGS_DIR.glob("*.yaml")):
        configs.append(
            {
                "name": path.stem,
                "path": str(path),
                "size": path.stat().st_size,
                "modified": path.stat().st_mtime,
            }
        )
    return configs


@app.get("/api/configs/{config_name}")
def get_config(config_name: str):
    """Get config content."""
    config_path = CONFIGS_DIR / f"{config_name}.yaml"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config not found")
    return {"name": config_name, "content": config_path.read_text()}


@app.delete("/api/configs/{config_name}")
def delete_config(config_name: str):
    """Delete a config."""
    config_path = CONFIGS_DIR / f"{config_name}.yaml"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config not found")

    # Safety check: reject if any RUNNING job uses this config
    for job in _jobs.values():
        if job.status == JobStatus.RUNNING and job.config_path == str(
            config_path
        ):
            raise HTTPException(
                status_code=409,
                detail="Cannot delete config: job is using it",
            )

    config_path.unlink()
    return {"deleted": True}


# ─── Models Endpoint ───────────────────────────────────────────────────

@app.get("/api/models")
def list_models():
    """List completed model outputs."""
    models = []
    if not OUTPUTS_DIR.exists():
        return models

    for model_dir in sorted(OUTPUTS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue

        has_model = (model_dir / "model.safetensors").exists() or (
            model_dir / "adapter_model.safetensors"
        ).exists()
        has_config = (model_dir / "config.json").exists()

        # Calculate size
        size = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())

        models.append(
            {
                "name": model_dir.name,
                "path": str(model_dir),
                "has_model": has_model,
                "has_config": has_config,
                "size_bytes": size,
                "modified": model_dir.stat().st_mtime,
            }
        )

    return sorted(models, key=lambda m: m["modified"], reverse=True)


# ─── Health Endpoint ───────────────────────────────────────────────────

@app.get("/health")
def health() -> HealthResponse:
    """API health check."""
    running_count = sum(
        1 for j in _jobs.values() if j.status == JobStatus.RUNNING
    )
    return HealthResponse(
        status="ok",
        running_jobs=running_count,
        jobs_total=len(_jobs),
        api_version=API_VERSION,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8093, log_level="info")
