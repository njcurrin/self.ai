"""
FastAPI server for controlling axolotl fine-tuning jobs.
Runs on port 8093, manages job lifecycle and progress monitoring.
"""

import asyncio
import json
import os
import shutil
import subprocess
import threading
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
MODELS_DIR = Path(os.environ.get("LLAMA_ARG_MODELS_DIR", "/models"))

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


class ModelPullRequest(BaseModel):
    name: str  # HuggingFace repo ID, e.g. "bartowski/Llama-3.2-1B-Instruct-GGUF"
    filename: Optional[str] = None  # Specific GGUF file in the repo

class ModelDeleteRequest(BaseModel):
    name: str  # Filename in models dir to delete


# ─── State ──────────────────────────────────────────────────────────────

_jobs: Dict[str, Job] = {}
_processes: Dict[str, subprocess.Popen] = {}
_active_downloads: Dict[str, threading.Event] = {}  # name -> cancel event

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
    env["PYTORCH_JIT"] = "0"  # Prevents SIGSEGV from torch.jit.script during torch.distributed.optim import

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


# ─── GGUF Model Management ────────────────────────────────────────────


import re

_SPLIT_SHARD_RE = re.compile(r"-(\d{5})-of-(\d{5})\.gguf$")


@app.get("/api/models/available")
def list_available_models():
    """List GGUF model files in the models directory (recursive).
    Split GGUF shards are grouped: only the first shard is shown with the
    combined size of all parts."""
    if not MODELS_DIR.exists():
        return []

    # Clean up any dangling symlinks first
    for f in MODELS_DIR.iterdir():
        if f.is_symlink() and not f.resolve().exists():
            f.unlink()

    # Collect all GGUF files, skipping .cache, .downloading, and symlinks
    all_files = []
    for f in sorted(MODELS_DIR.rglob("*.gguf")):
        if f.name.endswith(".downloading"):
            continue
        if f.is_symlink():
            continue
        try:
            f.relative_to(MODELS_DIR / ".cache")
            continue
        except ValueError:
            pass
        all_files.append(f)

    # Group split shards by their base name
    # e.g. "Model-00001-of-00004.gguf" -> base "Model"
    grouped: Dict[str, List[Path]] = {}
    standalone: List[Path] = []

    for f in all_files:
        m = _SPLIT_SHARD_RE.search(f.name)
        if m:
            base = f.name[:m.start()]
            key = str(f.parent / base)
            grouped.setdefault(key, []).append(f)
        else:
            standalone.append(f)

    models = []

    # Standalone (non-split) models
    for f in standalone:
        # Skip symlinks (they point to split shards and are handled below)
        if f.is_symlink():
            continue
        rel_path = str(f.relative_to(MODELS_DIR))
        # A top-level file is always registered (visible to llama-server)
        is_top_level = f.parent == MODELS_DIR
        models.append({
            "name": rel_path,
            "size": f.stat().st_size,
            "modified": f.stat().st_mtime,
            "registered": is_top_level,
        })

    # Split models — show first shard with combined size
    for key, shards in grouped.items():
        shards.sort(key=lambda p: p.name)
        first_shard = shards[0]
        total_size = sum(s.stat().st_size for s in shards)
        latest_modified = max(s.stat().st_mtime for s in shards)
        rel_path = str(first_shard.relative_to(MODELS_DIR))
        # Registered if first shard (or a symlink to it) exists at top level
        top_level_path = MODELS_DIR / first_shard.name
        registered = (
            (first_shard.parent == MODELS_DIR) or
            (top_level_path.is_symlink() or top_level_path.exists())
        )
        models.append({
            "name": rel_path,
            "size": total_size,
            "modified": latest_modified,
            "shards": len(shards),
            "registered": registered,
        })

    return models


class ModelRegisterRequest(BaseModel):
    name: str  # Relative path to first shard or file within MODELS_DIR


@app.post("/api/models/register")
def register_model(req: ModelRegisterRequest):
    """Register a model in a subdirectory by symlinking its first shard
    to the top level of MODELS_DIR so llama-server can discover it."""
    model_path = (MODELS_DIR / req.name).resolve()
    # Path traversal protection
    if not str(model_path).startswith(str(MODELS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid model path")
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model file not found")

    # Already at top level — nothing to do
    if model_path.parent == MODELS_DIR.resolve():
        return {"registered": True, "name": req.name, "action": "already_top_level"}

    symlink_path = MODELS_DIR / model_path.name
    if symlink_path.exists() or symlink_path.is_symlink():
        return {"registered": True, "name": req.name, "action": "already_registered"}

    symlink_path.symlink_to(model_path)

    # Restart llama-server so it discovers the newly registered model
    _restart_llama_server()

    return {"registered": True, "name": model_path.name, "action": "symlinked"}


@app.post("/api/models/pull")
async def pull_model(req: ModelPullRequest):
    """Pull a GGUF model from HuggingFace. Streams progress as NDJSON."""
    from huggingface_hub import HfApi, hf_hub_download

    repo_id = req.name.strip()
    filename = req.filename

    async def generate():
        try:
            api = HfApi()

            # List repo files to find GGUFs
            try:
                all_files = api.list_repo_files(repo_id)
            except Exception as e:
                yield json.dumps({"error": f"Failed to access repo '{repo_id}': {e}"}) + "\n"
                return

            gguf_files = [f for f in all_files if f.endswith(".gguf")]

            if not gguf_files:
                yield json.dumps({"error": f"No GGUF files found in '{repo_id}'"}) + "\n"
                return

            # Group GGUFs: detect split shard sets vs standalone files
            # Split shards look like: Model-00001-of-00004.gguf, Model-00002-of-00004.gguf
            shard_groups: Dict[str, List[str]] = {}  # base -> [files]
            standalone_gguf: List[str] = []

            for gf in gguf_files:
                m = _SPLIT_SHARD_RE.search(gf)
                if m:
                    base = gf[:gf.rfind("-", 0, m.start()) + 1] if "-" in gf[:m.start()] else gf[:m.start()]
                    # Use directory + base as key to group shards
                    parent = str(Path(gf).parent)
                    key = f"{parent}/{Path(gf).name[:m.start()]}"
                    shard_groups.setdefault(key, []).append(gf)
                else:
                    standalone_gguf.append(gf)

            # Build selectable options: standalone files + shard groups (by first shard)
            selectable = list(standalone_gguf)
            shard_first_to_group: Dict[str, List[str]] = {}
            for key, shards in shard_groups.items():
                shards.sort()
                first = shards[0]
                selectable.append(first)
                shard_first_to_group[first] = shards

            # If no filename specified and multiple options, return list for selection
            if not filename:
                if len(selectable) == 1:
                    selected = selectable[0]
                else:
                    yield json.dumps({"status": "select_file", "files": selectable}) + "\n"
                    return
            else:
                if filename not in gguf_files and filename not in selectable:
                    yield json.dumps({"error": f"File '{filename}' not found in repo. Available: {selectable}"}) + "\n"
                    return
                selected = filename

            # Determine all files to download (single file or all shards in group)
            files_to_download = shard_first_to_group.get(selected, [selected])
            is_split = len(files_to_download) > 1

            # Check if already exists
            dest_path = MODELS_DIR / Path(files_to_download[0]).name
            if dest_path.exists():
                yield json.dumps({"error": f"Model '{dest_path.name}' already exists"}) + "\n"
                return

            # Get total file size for progress tracking
            try:
                file_info = api.model_info(repo_id, files_metadata=True)
                total_size = 0
                sibling_sizes = {}
                for s in file_info.siblings:
                    size = getattr(s, 'size', None) or 0
                    if size == 0 and hasattr(s, 'lfs') and s.lfs:
                        size = s.lfs.get('size', 0) if isinstance(s.lfs, dict) else getattr(s.lfs, 'size', 0)
                    sibling_sizes[s.rfilename] = size
                for dl_file in files_to_download:
                    total_size += sibling_sizes.get(dl_file, 0)
            except Exception:
                total_size = 0

            # Set up cancel event
            cancel_event = threading.Event()
            download_key = f"{repo_id}/{selected}"
            _active_downloads[download_key] = cancel_event

            download_error = []
            download_done = threading.Event()

            def download_task():
                try:
                    for dl_file in files_to_download:
                        if cancel_event.is_set():
                            return
                        hf_hub_download(
                            repo_id=repo_id,
                            filename=dl_file,
                            local_dir=str(MODELS_DIR),
                            local_dir_use_symlinks=False,
                        )
                    download_done.set()
                except Exception as e:
                    download_error.append(str(e))
                    download_done.set()

            thread = threading.Thread(target=download_task, daemon=True)
            thread.start()

            status_label = Path(selected).name
            if is_split:
                status_label = f"{Path(selected).name} ({len(files_to_download)} shards)"
            yield json.dumps({"status": f"downloading {status_label}"}) + "\n"

            # Poll file size for progress
            while not download_done.is_set():
                if cancel_event.is_set():
                    # Clean up partial downloads
                    for dl_file in files_to_download:
                        for cleanup in [MODELS_DIR / Path(dl_file).name, MODELS_DIR / dl_file]:
                            if cleanup.exists():
                                cleanup.unlink()
                    yield json.dumps({"error": "Download cancelled"}) + "\n"
                    _active_downloads.pop(download_key, None)
                    return

                # Sum up downloaded bytes across all files
                current_size = 0
                seen_inodes = set()
                for dl_file in files_to_download:
                    dl_name = Path(dl_file).name
                    # Check completed file at top-level or in repo subdir
                    for check_path in [MODELS_DIR / dl_name, MODELS_DIR / dl_file]:
                        if check_path.exists():
                            try:
                                st = check_path.stat()
                                if st.st_ino not in seen_inodes:
                                    seen_inodes.add(st.st_ino)
                                    current_size += st.st_size
                            except OSError:
                                pass
                            break

                    # Check for .incomplete temp file for THIS specific file
                    if current_size == 0:
                        for incomplete_path in [
                            MODELS_DIR / f"{dl_name}.incomplete",
                            MODELS_DIR / dl_file / ".incomplete",
                            MODELS_DIR / f"{dl_file}.incomplete",
                        ]:
                            if incomplete_path.exists():
                                try:
                                    current_size += incomplete_path.stat().st_size
                                except OSError:
                                    pass
                                break

                # Last resort: check HF cache for this specific repo's incomplete files
                if current_size == 0:
                    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
                    # HF cache uses a sanitized repo name
                    cache_repo_dir = hf_cache / ("models--" + repo_id.replace("/", "--"))
                    if cache_repo_dir.exists():
                        for incomplete in cache_repo_dir.rglob("*.incomplete"):
                            try:
                                current_size += incomplete.stat().st_size
                            except OSError:
                                pass

                # Always send progress updates so the UI shows something
                if total_size > 0:
                    yield json.dumps({
                        "status": "downloading",
                        "digest": Path(selected).name,
                        "completed": min(current_size, total_size),
                        "total": total_size,
                    }) + "\n"
                else:
                    # No total_size known — still report bytes downloaded
                    yield json.dumps({
                        "status": "downloading",
                        "digest": Path(selected).name,
                        "completed": current_size,
                        "total": 0,
                    }) + "\n"

                await asyncio.sleep(1)

            _active_downloads.pop(download_key, None)

            if download_error:
                yield json.dumps({"error": download_error[0]}) + "\n"
                return

            # Post-download: ensure files are accessible to llama-server
            # hf_hub_download may place files in subdirs matching repo structure
            for dl_file in files_to_download:
                final_name = Path(dl_file).name
                top_level = MODELS_DIR / final_name
                repo_subpath = MODELS_DIR / dl_file

                if not top_level.exists() and repo_subpath.exists() and repo_subpath != top_level:
                    if not is_split:
                        # Single file: move to top level
                        shutil.move(str(repo_subpath), str(top_level))
                    # For split shards: leave in subdir, we'll symlink the first shard below

            # For split models: symlink first shard to top level so llama-server discovers it
            if is_split:
                first_shard_name = Path(files_to_download[0]).name
                symlink_path = MODELS_DIR / first_shard_name
                actual_path = MODELS_DIR / files_to_download[0]

                if not symlink_path.exists() and actual_path.exists():
                    symlink_path.symlink_to(actual_path)
                    yield json.dumps({"status": f"registered split model ({len(files_to_download)} shards)"}) + "\n"

            # Clean up empty parent dirs from hf_hub_download
            if not is_split:
                for dl_file in files_to_download:
                    repo_subpath = MODELS_DIR / dl_file
                    parent = repo_subpath.parent
                    while parent != MODELS_DIR:
                        try:
                            parent.rmdir()
                        except OSError:
                            break
                        parent = parent.parent

            # Verify success
            first_file = Path(files_to_download[0]).name
            check_path = MODELS_DIR / first_file
            if check_path.exists() or check_path.is_symlink():
                if is_split:
                    combined_size = sum(
                        (MODELS_DIR / f).stat().st_size
                        for f in files_to_download
                        if (MODELS_DIR / f).exists()
                    )
                    # Fall back to checking top-level if subdir paths don't exist
                    if combined_size == 0:
                        combined_size = check_path.stat().st_size
                    yield json.dumps({
                        "status": "downloading",
                        "digest": first_file,
                        "completed": combined_size,
                        "total": combined_size,
                    }) + "\n"
                else:
                    yield json.dumps({
                        "status": "downloading",
                        "digest": check_path.name,
                        "completed": check_path.stat().st_size,
                        "total": check_path.stat().st_size,
                    }) + "\n"
                # Restart llama-server so it discovers the new model
                _restart_llama_server()
                yield json.dumps({"status": "success"}) + "\n"
            else:
                yield json.dumps({"error": "Download completed but file not found in models directory"}) + "\n"

        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.post("/api/models/pull/cancel")
def cancel_pull(req: ModelPullRequest):
    """Cancel an active model download."""
    download_key = f"{req.name.strip()}/{req.filename or ''}"
    # Try exact match first, then prefix match
    event = _active_downloads.get(download_key)
    if not event:
        for key, evt in _active_downloads.items():
            if key.startswith(req.name.strip()):
                event = evt
                download_key = key
                break
    if not event:
        raise HTTPException(status_code=404, detail="No active download found")
    event.set()
    return {"status": "cancelling", "name": download_key}


@app.post("/api/models/delete")
def delete_gguf_model(req: ModelDeleteRequest):
    """Delete a GGUF model file from the models directory.
    If the file is part of a split GGUF set, all shards and symlinks are deleted."""
    raw_path = MODELS_DIR / req.name

    # Handle symlinks (resolve=False so we can check the link itself)
    if raw_path.is_symlink():
        # It's a symlink — delete it and the target shards if they exist
        target = raw_path.resolve()
        raw_path.unlink()
        deleted = [req.name]
        # If target was a split shard, also delete sibling shards
        if target.exists():
            m = _SPLIT_SHARD_RE.search(target.name)
            if m:
                base = target.name[:m.start()]
                for shard in target.parent.glob(f"{base}-*-of-*.gguf"):
                    if _SPLIT_SHARD_RE.search(shard.name):
                        shard.unlink()
                        deleted.append(str(shard))
        return {"deleted": True, "name": req.name, "files_removed": deleted}

    model_path = raw_path.resolve()
    # Path traversal protection
    if not str(model_path).startswith(str(MODELS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid model path")
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model not found")

    deleted = []
    m = _SPLIT_SHARD_RE.search(model_path.name)
    if m:
        # Delete all shards with the same base name in the same directory
        base = model_path.name[:m.start()]
        for shard in model_path.parent.glob(f"{base}-*-of-*.gguf"):
            if _SPLIT_SHARD_RE.search(shard.name):
                shard.unlink()
                deleted.append(shard.name)
        # Also remove any top-level symlinks pointing to deleted shards
        for link in MODELS_DIR.iterdir():
            if link.is_symlink() and link.name.endswith(".gguf"):
                try:
                    link_target = link.resolve()
                    if not link_target.exists():
                        link.unlink()
                        deleted.append(f"symlink:{link.name}")
                except Exception:
                    pass
    else:
        model_path.unlink()
        deleted.append(req.name)

    # Restart llama-server so it rescans the models directory
    _restart_llama_server()

    return {"deleted": True, "name": req.name, "files_removed": deleted}


# ─── llama-server Management ──────────────────────────────────────────


def _restart_llama_server() -> dict:
    """Restart llama-server via supervisord to rescan models directory."""
    try:
        result = subprocess.run(
            ["supervisorctl", "restart", "llama-server"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return {"status": "restarted"}
        else:
            return {"status": "error", "message": result.stderr.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/system/restart-llama-server")
def restart_llama_server():
    """Restart llama-server to rescan models directory."""
    return _restart_llama_server()


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
