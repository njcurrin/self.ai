"""
FastAPI server for controlling training jobs (HF Trainer + DeepSpeed + PEFT).
Runs on port 8093, manages job lifecycle and progress monitoring.
"""

import asyncio
import json
import os
import re
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

WORKSPACE = Path("/workspace/training")
CONFIGS_DIR = WORKSPACE / "configs"
OUTPUTS_DIR = WORKSPACE / "outputs"
LOGS_DIR = WORKSPACE / "logs"
JOBS_STATE_FILE = WORKSPACE / "jobs.json"
PIPELINE_STATE_FILE = WORKSPACE / "pipeline_tasks.json"
VENV_BIN = Path("/opt/venv/bin")
ACCELERATE = VENV_BIN / "accelerate"
PYTHON = VENV_BIN / "python"
TRAIN_SCRIPT = Path("/workspace/training/api/train.py")
MERGE_SCRIPT = Path("/workspace/training/api/merge_lora.py")
MODELS_DIR = Path(os.environ.get("LLAMA_ARG_MODELS_DIR", "/models"))
TOKENIZED_DATASETS = Path(os.environ.get("TOKENIZED_DATASETS", "/workspace/cache/tokenized-datasets"))
LLAMA_QUANTIZE = Path("/app/llama-quantize")
CONVERT_HF_TO_GGUF = Path("/app/convert/convert_hf_to_gguf.py")
CONVERT_LORA_TO_GGUF = Path("/app/convert/convert_lora_to_gguf.py")
BAKE_SCRIPT = Path("/workspace/training/api/bake_model.py")
HERETIC_SCRIPT = Path("/workspace/training/api/heretic_run.py")
HERETIC_DIR = WORKSPACE / "heretic"
HERETIC_DEFAULT_CONFIG = HERETIC_DIR / "config.default.toml"
LLAMA_SERVER_ARGS_FILE = Path("/app/llama-server.args")
MODELS_META_FILE = MODELS_DIR / "models_meta.json"

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
    base_model: Optional[str] = None

    class Config:
        example = {
            "config_path": "my-config",
            "base_model": "NousResearch/Meta-Llama-3-8B-Instruct",
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
    approved: bool = False


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


# ─── Pipeline Models ───────────────────────────────────────────────────

class HfModelPullRequest(BaseModel):
    """Download a full HuggingFace model (safetensors) for conversion."""
    repo_id: str  # HuggingFace repo ID, e.g. "NousResearch/Llama-3.2-1B"
    revision: Optional[str] = None  # Branch, tag, or commit hash
    output_name: Optional[str] = None  # Directory name in OUTPUTS_DIR; defaults to repo name


class PipelineTaskType(str, Enum):
    PULL_HF_MODEL = "pull_hf_model"
    MERGE_LORA = "merge_lora"
    CONVERT_TO_GGUF = "convert_to_gguf"
    CONVERT_LORA_TO_GGUF = "convert_lora_to_gguf"
    QUANTIZE = "quantize"
    BAKE = "bake"
    HERETIC = "heretic"


class PipelineTaskStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineTask(BaseModel):
    task_id: str
    task_type: PipelineTaskType
    status: PipelineTaskStatus
    pid: Optional[int] = None
    created_at: datetime
    finished_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    log_file: str
    error_message: Optional[str] = None
    input_path: str
    output_path: str


class MergeLoraRequest(BaseModel):
    """Merge a LoRA/QLoRA adapter into its base model."""
    model_output: str  # Name of training output dir in OUTPUTS_DIR (e.g. "qlora-out")


class ConvertToGgufRequest(BaseModel):
    """Convert a HuggingFace-format model to GGUF."""
    model_path: str  # Path relative to OUTPUTS_DIR (e.g. "qlora-out/merged") or absolute
    outtype: str = "f16"  # f32, f16, bf16, q8_0, auto
    model_name: Optional[str] = None  # Optional name for the output file


class QuantizeRequest(BaseModel):
    """Quantize a GGUF model file."""
    model_file: str  # GGUF filename in MODELS_DIR
    quant_type: str = "Q4_K_M"  # Q4_K_M, Q4_K_S, Q5_K_M, Q5_K_S, Q6_K, Q8_0, etc.


class ConvertLoraToGgufRequest(BaseModel):
    """Convert a LoRA adapter to GGUF format for dynamic loading."""
    model_output: str  # Training output dir name in OUTPUTS_DIR
    base_model: Optional[str] = None  # HF model ID; if None, read from adapter config
    outtype: str = "f32"  # f32, f16, bf16, q8_0
    output_name: Optional[str] = None  # Output filename; defaults to <model_output>-lora.gguf


class ApplyLorasRequest(BaseModel):
    """Configure llama-server to load LoRA adapters at inference time."""
    loras: List[Dict[str, Any]]  # [{"file": "coding-lora.gguf", "scale": 0.7}, ...]
    # If empty list, removes all LoRAs and restarts with base model only


class LoraAdapter(BaseModel):
    path: str  # Path relative to OUTPUTS_DIR
    weight: float = 1.0


class BakeRequest(BaseModel):
    """Bake multiple LoRA adapters into a single GGUF model."""
    base_model: str  # HF model ID or path in OUTPUTS_DIR
    adapters: List[LoraAdapter]
    output_name: str  # Name for the final GGUF file
    outtype: str = "f16"  # f32, f16, bf16, q8_0
    quant_type: Optional[str] = None  # Q4_K_M, Q8_0, etc. If None, skip quantization


class HereticJobCreate(BaseModel):
    """Run heretic abliteration on a model."""
    model_name: str  # HuggingFace repo ID, e.g. "meta-llama/Llama-3.1-8B-Instruct"
    quantization: str = "none"  # "none" or "bnb_4bit"
    n_trials: Optional[int] = None  # Override default trial count
    save_strategy: str = "merge"  # "merge" (full model) or "adapter" (LoRA only)


# ─── State ──────────────────────────────────────────────────────────────

_jobs: Dict[str, Job] = {}
_processes: Dict[str, subprocess.Popen] = {}
_active_downloads: Dict[str, threading.Event] = {}  # name -> cancel event
_pipeline_tasks: Dict[str, PipelineTask] = {}
_pipeline_processes: Dict[str, subprocess.Popen] = {}

app = FastAPI(title="Training API", version=API_VERSION)


# ─── Initialization ─────────────────────────────────────────────────────

def _ensure_dirs():
    """Create all required directories."""
    for d in [CONFIGS_DIR, OUTPUTS_DIR, LOGS_DIR, TOKENIZED_DATASETS]:
        d.mkdir(parents=True, exist_ok=True)


# ─── Model Metadata ─────────────────────────────────────────────────────

# Common GGUF quant suffixes, ordered longest-first so greedy match works.
_QUANT_TYPES = [
    "IQ1_S", "IQ1_M", "IQ2_XXS", "IQ2_XS", "IQ2_S", "IQ2_M",
    "IQ3_XXS", "IQ3_XS", "IQ3_S", "IQ3_M", "IQ4_XS", "IQ4_NL",
    "Q2_K_S", "Q2_K", "Q3_K_S", "Q3_K_M", "Q3_K_L",
    "Q4_0", "Q4_1", "Q4_K_S", "Q4_K_M", "Q4_K_L",
    "Q5_0", "Q5_1", "Q5_K_S", "Q5_K_M", "Q5_K_L",
    "Q6_K", "Q8_0", "Q8_1",
    "F16", "F32", "BF16",
]
_QUANT_PATTERN = re.compile(
    r"[-_.](" + "|".join(re.escape(q) for q in sorted(_QUANT_TYPES, key=len, reverse=True)) + r")(?:[-_.]|\.gguf$)",
    re.IGNORECASE,
)


def _parse_quant_from_filename(filename: str) -> Optional[str]:
    """Extract the quantization type from a GGUF filename, e.g. 'Q4_K_M' from 'Model-Q4_K_M.gguf'."""
    m = _QUANT_PATTERN.search(filename)
    return m.group(1).upper() if m else None


def _load_models_meta() -> Dict[str, Any]:
    """Load model metadata from JSON sidecar file."""
    if MODELS_META_FILE.exists():
        try:
            return json.loads(MODELS_META_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_models_meta(meta: Dict[str, Any]):
    """Persist model metadata (atomic write)."""
    tmp = MODELS_META_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, indent=2, default=str))
    tmp.replace(MODELS_META_FILE)


def _record_model_meta(
    model_filename: str,
    hf_repo: str,
    hf_filename: Optional[str],
    source_type: str,
    quant: Optional[str] = None,
    bake_info: Optional[Dict[str, Any]] = None,
):
    """Record metadata for a newly pulled or baked model."""
    if quant is None and hf_filename:
        quant = _parse_quant_from_filename(hf_filename)
    if quant is None:
        quant = _parse_quant_from_filename(model_filename)

    meta = _load_models_meta()
    entry = {
        "hf_repo": hf_repo,
        "hf_filename": hf_filename,
        "quant": quant,
        "source_type": source_type,
        "trainable": source_type not in ("gguf", "baked"),
        "pulled_at": datetime.now().isoformat(),
    }
    if bake_info:
        entry["bake_info"] = bake_info
    meta[model_filename] = entry
    _save_models_meta(meta)


def _remove_model_meta(model_filename: str):
    """Remove metadata entry for a deleted model."""
    meta = _load_models_meta()
    if model_filename in meta:
        del meta[model_filename]
        _save_models_meta(meta)


def _save_pipeline_tasks():
    """Persist pipeline task state to JSON file."""
    tmp = PIPELINE_STATE_FILE.with_suffix(".tmp")
    data = {tid: t.model_dump(mode="json") for tid, t in _pipeline_tasks.items()}
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(PIPELINE_STATE_FILE)


def _load_pipeline_tasks():
    """Load pipeline task state from JSON file."""
    global _pipeline_tasks
    if PIPELINE_STATE_FILE.exists():
        data = json.loads(PIPELINE_STATE_FILE.read_text())
        for task_id, task_data in data.items():
            try:
                task_data["created_at"] = datetime.fromisoformat(task_data["created_at"])
                if task_data.get("finished_at"):
                    task_data["finished_at"] = datetime.fromisoformat(task_data["finished_at"])
                task = PipelineTask(**task_data)
                if task.status == PipelineTaskStatus.RUNNING:
                    task.status = PipelineTaskStatus.FAILED
                    task.error_message = "Process lost on restart"
                    task.finished_at = datetime.now()
                _pipeline_tasks[task_id] = task
            except Exception as e:
                print(f"Failed to load pipeline task {task_id}: {e}")


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


def _auto_convert_lora(job: Job):
    """Auto-convert a completed training job's LoRA adapter to GGUF format."""
    output_dir = Path(job.output_dir)
    has_adapter = (
        (output_dir / "adapter_model.safetensors").exists()
        or (output_dir / "adapter_model.bin").exists()
    )
    if not has_adapter:
        return  # Full fine-tune or no adapter — nothing to convert

    # Determine the model_output name relative to OUTPUTS_DIR
    try:
        rel_path = output_dir.relative_to(OUTPUTS_DIR)
    except ValueError:
        print(f"Output dir {output_dir} is not under {OUTPUTS_DIR}, skipping auto-convert")
        return

    # Read base model from adapter_config.json
    base_model = None
    adapter_cfg_path = output_dir / "adapter_config.json"
    if adapter_cfg_path.exists():
        try:
            cfg = json.loads(adapter_cfg_path.read_text())
            base_model = cfg.get("base_model_name_or_path")
        except Exception:
            pass

    # Build a safe output filename from the relative path
    out_name = str(rel_path).replace("/", "-").replace("\\", "-") + "-lora-f16.gguf"
    outfile = MODELS_DIR / out_name

    if outfile.exists():
        print(f"LoRA GGUF already exists: {out_name}, skipping auto-convert")
        return

    cmd = [
        str(PYTHON), str(CONVERT_LORA_TO_GGUF),
        str(output_dir),
        "--outfile", str(outfile),
        "--outtype", "f16",
    ]
    if base_model:
        cmd.extend(["--base-model-id", base_model])

    env = {"NO_LOCAL_GGUF": "1"}

    # Record metadata now so the LoRA is discoverable even while converting
    _record_lora_meta(out_name, base_model, str(rel_path))

    print(f"Auto-converting LoRA to GGUF: {out_name}")
    _start_pipeline_task(
        task_type=PipelineTaskType.CONVERT_LORA_TO_GGUF,
        cmd=cmd,
        input_path=str(output_dir),
        output_path=str(outfile),
        env=env,
    )


async def _poll_jobs():
    """Background task: poll job status every 5 seconds and start pending jobs."""
    while True:
        await asyncio.sleep(5)
        any_finished = False
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
                else:
                    # Auto-convert LoRA adapter to GGUF if applicable
                    _auto_convert_lora(job)
                del _processes[job_id]
                any_finished = True

            # Refresh metrics
            _refresh_metrics(job)
            _save_jobs()

        # If a job just finished, try to start the next pending one
        if any_finished:
            _try_start_next_pending()

        # Poll pipeline tasks
        for task_id, task in list(_pipeline_tasks.items()):
            if task.status != PipelineTaskStatus.RUNNING:
                continue
            proc = _pipeline_processes.get(task_id)
            if not proc:
                continue
            rc = proc.poll()
            if rc is not None:
                task.exit_code = rc
                task.finished_at = datetime.now()
                task.status = (
                    PipelineTaskStatus.COMPLETED if rc == 0
                    else PipelineTaskStatus.FAILED
                )
                if rc != 0:
                    # Read last lines of log for error context
                    try:
                        log_lines = Path(task.log_file).read_text().splitlines()
                        tail = "\n".join(log_lines[-10:])
                        task.error_message = f"Process exited with code {rc}. Tail:\n{tail}"
                    except Exception:
                        task.error_message = f"Process exited with code {rc}"
                del _pipeline_processes[task_id]
                _save_pipeline_tasks()


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    _ensure_dirs()
    _load_jobs()
    _load_pipeline_tasks()
    # Start any pending jobs that were queued before restart
    _try_start_next_pending()
    asyncio.create_task(_poll_jobs())


# ─── Jobs Endpoints ────────────────────────────────────────────────────

def _start_job(job: Job) -> None:
    """Actually launch a pending job's training process."""
    config_path = Path(job.config_path)
    if not config_path.exists():
        job.status = JobStatus.FAILED
        job.error_message = f"Config file not found: {config_path}"
        job.finished_at = datetime.now()
        _save_jobs()
        return

    # Build command
    cmd = [
        str(ACCELERATE),
        "launch",
        str(TRAIN_SCRIPT),
        str(config_path),
    ]

    # Open log file
    log_path = Path(job.log_file)
    try:
        log_fh = open(log_path, "w")
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = f"Failed to open log: {e}"
        job.finished_at = datetime.now()
        _save_jobs()
        return

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
        job.status = JobStatus.FAILED
        job.error_message = f"Failed to start training: {e}"
        job.finished_at = datetime.now()
        _save_jobs()
        return

    job.status = JobStatus.RUNNING
    job.pid = proc.pid
    job.started_at = datetime.now()
    _processes[job.job_id] = proc
    _save_jobs()


def _try_start_next_pending() -> None:
    """If no job is running, start the next approved pending job (FIFO)."""
    for job in _jobs.values():
        if job.status == JobStatus.RUNNING:
            return  # Something is already running

    # Find oldest approved pending job
    pending = [j for j in _jobs.values() if j.status == JobStatus.PENDING and j.approved]
    if not pending:
        return
    pending.sort(key=lambda j: j.created_at)
    _start_job(pending[0])


@app.post("/api/jobs", status_code=201)
def create_job(req: JobCreate) -> Job:
    """Queue a new training job. It will start automatically when no other job is running."""
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

    # If a base_model override is provided, add it to overrides
    if req.base_model:
        overrides["base_model"] = req.base_model

    # Resolve source config path
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

    # Write a job-specific config with all overrides and dataset_prepared_path baked in
    try:
        config_data = yaml.safe_load(config_path.read_text())
        for k, v in overrides.items():
            config_data[k] = v

        # Scope output_dir under a subfolder named after the base model
        base_model_str = config_data.get("base_model", "")
        if base_model_str:
            model_slug = re.sub(r"[^\w\-.]", "_", Path(base_model_str).name)
            raw_output = config_data.get("output_dir", f"lora-{job_id}")
            output_leaf = Path(raw_output).name
            config_data["output_dir"] = str(OUTPUTS_DIR / model_slug / output_leaf)

        config_data["dataset_prepared_path"] = str(TOKENIZED_DATASETS / job_id)
        job_config_path = CONFIGS_DIR / f"job-{job_id}.yaml"
        job_config_path.write_text(yaml.dump(config_data, default_flow_style=False))
        config_path = job_config_path
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to prepare config: {e}")

    # Extract output dir
    output_dir = _extract_output_dir(config_path, None)

    log_file = LOGS_DIR / f"{job_id}.log"

    # Create job record as PENDING
    job = Job(
        job_id=job_id,
        status=JobStatus.PENDING,
        config_path=str(config_path),
        output_dir=output_dir,
        created_at=datetime.now(),
        log_file=str(log_file),
    )

    _jobs[job_id] = job
    _save_jobs()

    # Job remains pending until approved by an admin
    return _jobs[job_id]


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
    if job.status not in (JobStatus.RUNNING, JobStatus.PENDING):
        raise HTTPException(status_code=400, detail="Job is not running or pending")

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


@app.post("/api/jobs/{job_id}/approve")
def approve_job(job_id: str):
    """Approve a pending job so it can be started."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending jobs can be approved")
    if job.approved:
        raise HTTPException(status_code=400, detail="Job is already approved")

    job.approved = True
    _save_jobs()

    # Try to start immediately if nothing else is running
    _try_start_next_pending()

    return _jobs[job_id]


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

    meta = _load_models_meta()
    models = []

    def _enrich(entry: dict) -> dict:
        """Add metadata fields (hf_repo, quant, trainable, etc.) to a model entry."""
        # Look up by filename (basename) since metadata keys are basenames
        basename = Path(entry["name"]).name
        m = meta.get(basename, {})
        entry["hf_repo"] = m.get("hf_repo")
        entry["quant"] = m.get("quant")
        entry["source_type"] = m.get("source_type")
        entry["pulled_at"] = m.get("pulled_at")
        if m.get("bake_info"):
            entry["bake_info"] = m["bake_info"]
        # Derive trainable: safetensors_converted models are trainable if original files still exist
        trainable = m.get("trainable", False)
        if trainable and m.get("source_type") == "safetensors_converted" and m.get("hf_repo"):
            safetensors_dir = OUTPUTS_DIR / m["hf_repo"].split("/")[-1]
            if not safetensors_dir.exists() or not any(safetensors_dir.glob("*.safetensors")):
                trainable = False
        entry["trainable"] = trainable
        return entry

    # Standalone (non-split) models
    for f in standalone:
        # Skip symlinks (they point to split shards and are handled below)
        if f.is_symlink():
            continue
        rel_path = str(f.relative_to(MODELS_DIR))
        # A top-level file is always registered (visible to llama-server)
        is_top_level = f.parent == MODELS_DIR
        models.append(_enrich({
            "name": rel_path,
            "size": f.stat().st_size,
            "modified": f.stat().st_mtime,
            "registered": is_top_level,
        }))

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
        models.append(_enrich({
            "name": rel_path,
            "size": total_size,
            "modified": latest_modified,
            "shards": len(shards),
            "registered": registered,
        }))

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


class ModelInspectRequest(BaseModel):
    name: str


@app.post("/api/models/inspect")
async def inspect_model(req: ModelInspectRequest):
    """Query HuggingFace for model file sizes before downloading."""
    from huggingface_hub import HfApi

    repo_id = req.name.strip()

    try:
        api = HfApi()
        repo_info = api.model_info(repo_id, files_metadata=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to access repo '{repo_id}': {e}")

    def get_size(s):
        size = getattr(s, 'size', None) or 0
        if size == 0 and hasattr(s, 'lfs') and s.lfs:
            size = s.lfs.get('size', 0) if isinstance(s.lfs, dict) else getattr(s.lfs, 'size', 0)
        return size

    all_siblings = repo_info.siblings or []
    gguf_siblings = [s for s in all_siblings if s.rfilename.endswith('.gguf')]

    if gguf_siblings:
        files = [{"name": s.rfilename, "size": get_size(s)} for s in gguf_siblings]
        return {"type": "gguf", "files": files, "total_size": sum(f["size"] for f in files)}

    # No GGUFs — check for safetensors (which will be downloaded and converted)
    _allow_exts = (".safetensors", ".json", ".txt", ".model", ".py")
    _ignore_exts = (".gguf", ".bin", ".msgpack", ".h5", ".ot", ".md")
    _ignore_names = {".gitattributes"}

    st_files = []
    for s in all_siblings:
        fname = s.rfilename
        if fname in _ignore_names:
            continue
        if any(fname.endswith(ext) for ext in _ignore_exts):
            continue
        if not any(fname.endswith(ext) for ext in _allow_exts):
            continue
        st_files.append({"name": fname, "size": get_size(s)})

    if not st_files:
        raise HTTPException(status_code=400, detail=f"No downloadable files found in '{repo_id}'")

    # Show only weight shards in the file list; configs are noise to the user.
    # total_size still reflects the full download (weights + configs).
    model_files = [f for f in st_files if f["name"].endswith(".safetensors")]
    display_files = model_files if model_files else st_files
    return {"type": "safetensors", "files": display_files, "total_size": sum(f["size"] for f in st_files)}


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
                # No GGUFs — check if this is a safetensors model repo.
                # If so, download it as an HF model (safetensors + config) and
                # then convert to GGUF automatically.
                has_safetensors = any(f.endswith(".safetensors") for f in all_files)
                has_config = "config.json" in all_files
                if not has_safetensors or not has_config:
                    yield json.dumps({"error": f"No GGUF or safetensors files found in '{repo_id}'"}) + "\n"
                    return

                # Delegate to the HF-model pull + auto-convert pipeline
                output_name = repo_id.split("/")[-1]
                dest_dir = OUTPUTS_DIR / output_name
                digest_name = f"{output_name} (safetensors → GGUF)"

                from huggingface_hub import snapshot_download

                # Calculate total download size using same filters as download
                _allow_exts = (".safetensors", ".json", ".txt", ".model", ".py")
                _ignore_exts = (".gguf", ".bin", ".msgpack", ".h5", ".ot", ".md")
                _ignore_names = {".gitattributes"}
                total_size = 0
                try:
                    repo_info = api.model_info(repo_id, files_metadata=True)
                    for s in repo_info.siblings:
                        fname = s.rfilename
                        if fname in _ignore_names:
                            continue
                        if any(fname.endswith(ext) for ext in _ignore_exts):
                            continue
                        if not any(fname.endswith(ext) for ext in _allow_exts):
                            continue
                        size = getattr(s, 'size', None) or 0
                        if size == 0 and hasattr(s, 'lfs') and s.lfs:
                            size = s.lfs.get('size', 0) if isinstance(s.lfs, dict) else getattr(s.lfs, 'size', 0)
                        total_size += size
                except Exception:
                    total_size = 0

                if dest_dir.exists() and any(dest_dir.glob("*.safetensors")):
                    yield json.dumps({
                        "status": "downloading",
                        "digest": digest_name,
                        "completed": total_size,
                        "total": total_size,
                    }) + "\n"
                else:
                    download_error = []
                    download_done = threading.Event()

                    def _hf_download():
                        try:
                            snapshot_download(
                                repo_id=repo_id,
                                local_dir=str(dest_dir),
                                local_dir_use_symlinks=False,
                                allow_patterns=["*.safetensors", "*.json", "*.txt", "*.model", "*.py"],
                                ignore_patterns=["*.gguf", "*.bin", "*.msgpack", "*.h5", "*.ot", "*.md", ".gitattributes"],
                            )
                        except Exception as e:
                            download_error.append(str(e))
                        finally:
                            download_done.set()

                    thread = threading.Thread(target=_hf_download, daemon=True)
                    thread.start()

                    while not download_done.is_set():
                        current_size = 0
                        if dest_dir.exists():
                            for f in dest_dir.rglob("*"):
                                if f.is_file():
                                    try:
                                        current_size += f.stat().st_size
                                    except OSError:
                                        pass
                        if total_size > 0:
                            yield json.dumps({
                                "status": "downloading",
                                "digest": digest_name,
                                "completed": min(current_size, total_size),
                                "total": total_size,
                            }) + "\n"
                        else:
                            yield json.dumps({
                                "status": "downloading",
                                "digest": digest_name,
                                "completed": current_size,
                                "total": 0,
                            }) + "\n"
                        await asyncio.sleep(2)

                    if download_error:
                        yield json.dumps({"error": f"Download failed: {download_error[0]}"}) + "\n"
                        return

                # Auto-convert to GGUF (q8_0)
                outtype = "q8_0"
                out_name = f"{output_name}-{outtype}.gguf"
                outfile = MODELS_DIR / out_name

                if outfile.exists():
                    _record_model_meta(out_name, repo_id, None, "safetensors_converted", quant=outtype)
                    yield json.dumps({"status": "success"}) + "\n"
                    return

                # Stream conversion progress with digest so UI shows progress bar
                convert_digest = f"Converting → {out_name}"

                yield json.dumps({
                    "status": "converting",
                    "digest": convert_digest,
                    "completed": 0,
                    "total": 0,
                }) + "\n"

                convert_cmd = [
                    str(PYTHON), str(CONVERT_HF_TO_GGUF),
                    str(dest_dir),
                    "--outfile", str(outfile),
                    "--outtype", outtype,
                ]
                env = os.environ.copy()
                env["NO_LOCAL_GGUF"] = "1"

                convert_proc = await asyncio.create_subprocess_exec(
                    *convert_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    env=env,
                )
                async for raw_line in convert_proc.stdout:
                    yield json.dumps({
                        "status": "converting",
                        "digest": convert_digest,
                        "completed": 0,
                        "total": 0,
                        "log": raw_line.decode(errors="replace").rstrip(),
                    }) + "\n"
                await convert_proc.wait()

                if convert_proc.returncode != 0:
                    yield json.dumps({"error": f"GGUF conversion failed (exit code {convert_proc.returncode})"}) + "\n"
                    return

                # Restart llama-server to pick up the new model
                _restart_llama_server()

                _record_model_meta(out_name, repo_id, None, "safetensors_converted", quant=outtype)
                yield json.dumps({"status": "success"}) + "\n"
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
                _record_model_meta(first_file, repo_id, selected, "gguf")
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
        _remove_model_meta(Path(req.name).name)
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

    _remove_model_meta(Path(req.name).name)
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


# ─── Outputs Endpoint ──────────────────────────────────────────────────


@app.get("/api/outputs")
def list_outputs():
    """List completed training output directories."""
    outputs = []
    if not OUTPUTS_DIR.exists():
        return outputs

    for output_dir in sorted(OUTPUTS_DIR.iterdir()):
        if not output_dir.is_dir():
            continue

        has_model = (output_dir / "model.safetensors").exists() or (
            output_dir / "adapter_model.safetensors"
        ).exists()
        has_config = (output_dir / "config.json").exists()
        size = sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file())

        outputs.append(
            {
                "name": output_dir.name,
                "path": str(output_dir),
                "has_model": has_model,
                "has_config": has_config,
                "size_bytes": size,
                "modified": output_dir.stat().st_mtime,
            }
        )

    return sorted(outputs, key=lambda o: o["modified"], reverse=True)


# ─── Pipeline Endpoints ───────────────────────────────────────────────


def _start_pipeline_task(
    task_type: PipelineTaskType,
    cmd: List[str],
    input_path: str,
    output_path: str,
    env: Optional[Dict[str, str]] = None,
) -> PipelineTask:
    """Launch a pipeline task as a background process."""
    task_id = str(uuid.uuid4())[:8]
    log_file = LOGS_DIR / f"pipeline-{task_id}.log"

    task = PipelineTask(
        task_id=task_id,
        task_type=task_type,
        status=PipelineTaskStatus.RUNNING,
        created_at=datetime.now(),
        log_file=str(log_file),
        input_path=input_path,
        output_path=output_path,
    )

    run_env = os.environ.copy()
    run_env["PATH"] = f"{VENV_BIN}:/app:{run_env.get('PATH', '')}"
    run_env["PYTHONUNBUFFERED"] = "1"
    if env:
        run_env.update(env)

    try:
        log_fh = open(log_file, "w")
        proc = subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            env=run_env,
            cwd=str(WORKSPACE),
        )
    except Exception as e:
        task.status = PipelineTaskStatus.FAILED
        task.error_message = f"Failed to start: {e}"
        task.finished_at = datetime.now()
        _pipeline_tasks[task_id] = task
        _save_pipeline_tasks()
        return task

    task.pid = proc.pid
    _pipeline_tasks[task_id] = task
    _pipeline_processes[task_id] = proc
    _save_pipeline_tasks()
    return task


@app.post("/api/pipeline/pull-hf-model")
async def pull_hf_model(req: HfModelPullRequest):
    """Download a full HuggingFace model (safetensors, config, tokenizer) for
    use in the convert-to-gguf pipeline.

    Streams progress as NDJSON. The model is saved to OUTPUTS_DIR so it can
    be passed directly to /api/pipeline/convert-to-gguf.
    """
    from huggingface_hub import HfApi, snapshot_download

    repo_id = req.repo_id.strip()
    output_name = req.output_name or repo_id.split("/")[-1]
    dest_dir = OUTPUTS_DIR / output_name

    async def generate():
        try:
            api = HfApi()

            # Validate repo exists
            try:
                repo_info = api.model_info(repo_id, files_metadata=True)
            except Exception as e:
                yield json.dumps({"error": f"Failed to access repo '{repo_id}': {e}"}) + "\n"
                return

            if dest_dir.exists():
                # Check if it already has model files
                if any(dest_dir.glob("*.safetensors")) and (dest_dir / "config.json").exists():
                    yield json.dumps({"error": f"Model already exists at '{output_name}'. Delete it first or use a different output_name."}) + "\n"
                    return

            # Calculate total download size — must match the allow/ignore
            # patterns used by snapshot_download below so the progress bar
            # is accurate (previously we counted .bin files that were never
            # downloaded, doubling the reported total).
            _allow_exts = (".safetensors", ".json", ".txt", ".model", ".py")
            _ignore_exts = (".gguf", ".bin", ".msgpack", ".h5", ".ot", ".md")
            _ignore_names = {".gitattributes"}

            total_size = 0
            download_files = []
            for s in repo_info.siblings:
                fname = s.rfilename
                if fname in _ignore_names:
                    continue
                if any(fname.endswith(ext) for ext in _ignore_exts):
                    continue
                if not any(fname.endswith(ext) for ext in _allow_exts):
                    continue
                size = getattr(s, 'size', None) or 0
                if size == 0 and hasattr(s, 'lfs') and s.lfs:
                    size = s.lfs.get('size', 0) if isinstance(s.lfs, dict) else getattr(s.lfs, 'size', 0)
                total_size += size
                download_files.append(fname)

            # Check that repo has safetensors
            has_safetensors = any(f.endswith(".safetensors") for f in download_files)
            has_config = "config.json" in download_files
            if not has_safetensors:
                yield json.dumps({"error": f"No .safetensors files found in '{repo_id}'. This endpoint is for HF model repos, not GGUF repos."}) + "\n"
                return
            if not has_config:
                yield json.dumps({"error": f"No config.json found in '{repo_id}'. Not a valid model repo."}) + "\n"
                return

            yield json.dumps({
                "status": "downloading",
                "repo_id": repo_id,
                "total": total_size,
                "completed": 0,
                "dest": output_name,
            }) + "\n"

            # Download in background thread
            cancel_event = threading.Event()
            download_key = f"hf-model:{repo_id}"
            _active_downloads[download_key] = cancel_event

            download_error = []
            download_done = threading.Event()
            result_path = [None]

            def download_task():
                try:
                    # Only download safetensors (skip .bin duplicates) + essential config/tokenizer files
                    allow_patterns = [
                        "*.safetensors",
                        "*.json",
                        "*.txt",          # e.g. merges.txt for tokenizer
                        "*.model",        # sentencepiece .model
                        "*.py",           # modeling code if needed
                    ]
                    ignore_patterns = [
                        "*.gguf",
                        "*.bin",          # skip pytorch .bin if safetensors exist
                        "*.msgpack",
                        "*.h5",
                        "*.ot",
                        "*.md",
                        ".gitattributes",
                    ]

                    path = snapshot_download(
                        repo_id=repo_id,
                        revision=req.revision,
                        local_dir=str(dest_dir),
                        local_dir_use_symlinks=False,
                        allow_patterns=allow_patterns,
                        ignore_patterns=ignore_patterns,
                    )
                    result_path[0] = path
                    download_done.set()
                except Exception as e:
                    download_error.append(str(e))
                    download_done.set()

            thread = threading.Thread(target=download_task, daemon=True)
            thread.start()

            # Poll progress by measuring downloaded bytes
            while not download_done.is_set():
                if cancel_event.is_set():
                    yield json.dumps({"error": "Download cancelled"}) + "\n"
                    _active_downloads.pop(download_key, None)
                    # Clean up partial download
                    if dest_dir.exists():
                        shutil.rmtree(dest_dir, ignore_errors=True)
                    return

                current_size = 0
                if dest_dir.exists():
                    for f in dest_dir.rglob("*"):
                        if f.is_file():
                            try:
                                current_size += f.stat().st_size
                            except OSError:
                                pass

                yield json.dumps({
                    "status": "downloading",
                    "repo_id": repo_id,
                    "completed": current_size,
                    "total": total_size,
                }) + "\n"

                await asyncio.sleep(2)

            _active_downloads.pop(download_key, None)

            if download_error:
                yield json.dumps({"error": download_error[0]}) + "\n"
                return

            # Verify download
            if not dest_dir.exists() or not any(dest_dir.glob("*.safetensors")):
                yield json.dumps({"error": "Download completed but no safetensors files found"}) + "\n"
                return

            final_size = sum(
                f.stat().st_size for f in dest_dir.rglob("*") if f.is_file()
            )

            yield json.dumps({
                "status": "downloading",
                "repo_id": repo_id,
                "completed": final_size,
                "total": final_size,
            }) + "\n"

            yield json.dumps({
                "status": "success",
                "dest": output_name,
                "path": str(dest_dir),
                "size": final_size,
                "next_step": f"POST /api/pipeline/convert-to-gguf with model_path=\"{output_name}\"",
            }) + "\n"

        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.post("/api/pipeline/merge-lora", status_code=201)
def merge_lora(req: MergeLoraRequest) -> PipelineTask:
    """Merge a LoRA/QLoRA adapter into the base model.

    Uses PEFT to load the adapter and merge it into the base model.
    Output is saved to <output_dir>/merged/ as a full HF-format model.
    Base model is read from adapter_config.json in the output directory.
    """
    output_dir = OUTPUTS_DIR / req.model_output
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Training output '{req.model_output}' not found in {OUTPUTS_DIR}",
        )

    # Check for adapter weights (indicates LoRA was used)
    has_adapter = (output_dir / "adapter_model.safetensors").exists() or (
        output_dir / "adapter_model.bin"
    ).exists()
    if not has_adapter:
        raise HTTPException(
            status_code=400,
            detail="No adapter weights found — this may be a full fine-tune (no merge needed)",
        )

    # Verify adapter_config.json exists (needed by merge_lora.py to find base model)
    if not (output_dir / "adapter_config.json").exists():
        raise HTTPException(
            status_code=400,
            detail="adapter_config.json not found — cannot determine base model for merge",
        )

    merged_path = output_dir / "merged"

    # Check if already merged
    if merged_path.exists() and (merged_path / "model.safetensors").exists():
        raise HTTPException(
            status_code=409,
            detail=f"Merged model already exists at {merged_path}",
        )

    cmd = [
        str(PYTHON), str(MERGE_SCRIPT),
        "--adapter_path", str(output_dir),
        "--output_dir", str(output_dir),
    ]

    return _start_pipeline_task(
        task_type=PipelineTaskType.MERGE_LORA,
        cmd=cmd,
        input_path=str(output_dir),
        output_path=str(merged_path),
    )


@app.post("/api/pipeline/convert-to-gguf", status_code=201)
def convert_to_gguf(req: ConvertToGgufRequest) -> PipelineTask:
    """Convert a HuggingFace-format model (safetensors) to GGUF format.

    The resulting GGUF file is placed in MODELS_DIR ready for llama-server.
    """
    # Resolve model path
    model_path = Path(req.model_path)
    if not model_path.is_absolute():
        model_path = OUTPUTS_DIR / req.model_path

    if not model_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Model path not found: {model_path}",
        )

    # Validate it looks like a HF model directory
    has_safetensors = any(model_path.glob("*.safetensors"))
    has_config = (model_path / "config.json").exists()
    if not has_safetensors:
        raise HTTPException(
            status_code=400,
            detail="No .safetensors files found in model directory",
        )
    if not has_config:
        raise HTTPException(
            status_code=400,
            detail="No config.json found in model directory",
        )

    # Validate outtype
    valid_outtypes = ["f32", "f16", "bf16", "q8_0", "auto"]
    if req.outtype not in valid_outtypes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid outtype '{req.outtype}'. Must be one of: {valid_outtypes}",
        )

    # Determine output filename
    if req.model_name:
        out_name = f"{req.model_name}-{req.outtype}.gguf"
    else:
        out_name = f"{model_path.name}-{req.outtype}.gguf"
    outfile = MODELS_DIR / out_name

    if outfile.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Output file already exists: {out_name}",
        )

    cmd = [
        str(PYTHON), str(CONVERT_HF_TO_GGUF),
        str(model_path),
        "--outfile", str(outfile),
        "--outtype", req.outtype,
    ]

    # Set NO_LOCAL_GGUF so convert script uses the installed gguf package
    env = {"NO_LOCAL_GGUF": "1"}

    return _start_pipeline_task(
        task_type=PipelineTaskType.CONVERT_TO_GGUF,
        cmd=cmd,
        input_path=str(model_path),
        output_path=str(outfile),
        env=env,
    )


@app.post("/api/pipeline/quantize", status_code=201)
def quantize_model(req: QuantizeRequest) -> PipelineTask:
    """Quantize a GGUF model to a smaller format.

    Takes an existing GGUF file in MODELS_DIR and produces a quantized version.
    """
    model_path = MODELS_DIR / req.model_file
    if not model_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"GGUF model not found: {req.model_file}",
        )

    if not req.model_file.endswith(".gguf"):
        raise HTTPException(
            status_code=400,
            detail="Input file must be a .gguf file",
        )

    # Validate quantization type
    valid_quants = [
        "Q4_0", "Q4_1", "Q4_K_S", "Q4_K_M",
        "Q5_0", "Q5_1", "Q5_K_S", "Q5_K_M",
        "Q6_K", "Q8_0", "Q2_K", "Q3_K_S", "Q3_K_M", "Q3_K_L",
        "IQ2_XXS", "IQ2_XS", "IQ3_XXS", "IQ3_S", "IQ4_NL", "IQ4_XS",
        "F16", "F32", "BF16",
    ]
    quant_upper = req.quant_type.upper()
    if quant_upper not in valid_quants:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid quant_type '{req.quant_type}'. Common types: Q4_K_M, Q5_K_M, Q6_K, Q8_0",
        )

    # Build output filename: replace type suffix or append
    stem = req.model_file.rsplit(".gguf", 1)[0]
    out_name = f"{stem}-{quant_upper}.gguf"
    outfile = MODELS_DIR / out_name

    if outfile.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Output file already exists: {out_name}",
        )

    cmd = [
        str(LLAMA_QUANTIZE),
        str(model_path),
        str(outfile),
        quant_upper,
    ]

    return _start_pipeline_task(
        task_type=PipelineTaskType.QUANTIZE,
        cmd=cmd,
        input_path=str(model_path),
        output_path=str(outfile),
    )


@app.post("/api/pipeline/convert-lora-to-gguf", status_code=201)
def convert_lora_to_gguf(req: ConvertLoraToGgufRequest) -> PipelineTask:
    """Convert a LoRA adapter to GGUF format for dynamic loading with llama-server.

    The resulting LoRA GGUF can be applied at inference time via /api/system/apply-loras
    without merging into the base model.
    """
    output_dir = OUTPUTS_DIR / req.model_output
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Training output '{req.model_output}' not found",
        )

    # Verify adapter files exist
    has_adapter = (output_dir / "adapter_model.safetensors").exists() or (
        output_dir / "adapter_model.bin"
    ).exists()
    if not has_adapter:
        raise HTTPException(
            status_code=400,
            detail="No adapter weights found in output directory",
        )

    valid_outtypes = ["f32", "f16", "bf16", "q8_0", "auto"]
    if req.outtype not in valid_outtypes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid outtype '{req.outtype}'. Must be one of: {valid_outtypes}",
        )

    out_name = req.output_name or f"{req.model_output}-lora-{req.outtype}.gguf"
    if not out_name.endswith(".gguf"):
        out_name += ".gguf"
    outfile = MODELS_DIR / out_name

    if outfile.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Output file already exists: {out_name}",
        )

    cmd = [
        str(PYTHON), str(CONVERT_LORA_TO_GGUF),
        str(output_dir),
        "--outfile", str(outfile),
        "--outtype", req.outtype,
    ]

    if req.base_model:
        cmd.extend(["--base-model-id", req.base_model])

    env = {"NO_LOCAL_GGUF": "1"}

    # Determine base model from adapter_config.json for metadata
    base_model_id = req.base_model
    if not base_model_id:
        adapter_cfg_path = output_dir / "adapter_config.json"
        if adapter_cfg_path.exists():
            try:
                adapter_cfg = json.loads(adapter_cfg_path.read_text())
                base_model_id = adapter_cfg.get("base_model_name_or_path")
            except Exception:
                pass

    # Record in models_meta.json so the LoRA is discoverable
    _record_lora_meta(out_name, base_model_id, req.model_output)

    return _start_pipeline_task(
        task_type=PipelineTaskType.CONVERT_LORA_TO_GGUF,
        cmd=cmd,
        input_path=str(output_dir),
        output_path=str(outfile),
        env=env,
    )


def _record_lora_meta(
    lora_filename: str,
    base_model: Optional[str],
    training_output: str,
):
    """Record metadata for a LoRA GGUF file."""
    meta = _load_models_meta()
    meta[lora_filename] = {
        "source_type": "lora_gguf",
        "base_model": base_model,
        "training_output": training_output,
        "created_at": datetime.now().isoformat(),
    }
    _save_models_meta(meta)


@app.get("/api/loras/available")
def list_available_loras():
    """List LoRA GGUF files available for dynamic loading.

    Returns LoRAs from models_meta.json (source_type == lora_gguf) that
    still exist on disk, enriched with base_model info.
    """
    if not MODELS_DIR.exists():
        return []

    meta = _load_models_meta()
    loras = []

    # Gather known LoRA GGUFs from metadata
    known_lora_files = set()
    for filename, entry in meta.items():
        if entry.get("source_type") != "lora_gguf":
            continue
        fpath = MODELS_DIR / filename
        if not fpath.exists():
            continue
        known_lora_files.add(filename)
        loras.append({
            "file": filename,
            "base_model": entry.get("base_model"),
            "training_output": entry.get("training_output"),
            "size": fpath.stat().st_size,
            "modified": fpath.stat().st_mtime,
        })

    # Also scan for *-lora-*.gguf files not yet in metadata
    # (e.g. converted before this code was added)
    for f in MODELS_DIR.glob("*-lora-*.gguf"):
        if f.name in known_lora_files:
            continue
        # Try to find base_model from training output adapter_config
        base_model = None
        # Infer training output name from filename pattern: <output>-lora-<outtype>.gguf
        stem = f.stem  # e.g. "qlora-out-lora-f16"
        parts = stem.rsplit("-lora-", 1)
        if len(parts) == 2:
            training_output_name = parts[0]
            adapter_cfg = OUTPUTS_DIR / training_output_name / "adapter_config.json"
            if adapter_cfg.exists():
                try:
                    cfg = json.loads(adapter_cfg.read_text())
                    base_model = cfg.get("base_model_name_or_path")
                except Exception:
                    pass
            # Record it for future lookups
            _record_lora_meta(f.name, base_model, training_output_name)

        loras.append({
            "file": f.name,
            "base_model": base_model,
            "training_output": parts[0] if len(parts) == 2 else None,
            "size": f.stat().st_size,
            "modified": f.stat().st_mtime,
        })

    # Also scan training outputs for unconverted adapters and auto-convert them
    known_training_outputs = {l.get("training_output") for l in loras if l.get("training_output")}
    if OUTPUTS_DIR.exists():
        for output_dir in OUTPUTS_DIR.rglob("adapter_model.safetensors"):
            parent = output_dir.parent
            try:
                rel = str(parent.relative_to(OUTPUTS_DIR))
            except ValueError:
                continue
            if rel in known_training_outputs:
                continue
            # This adapter hasn't been converted yet — read its base_model
            base_model = None
            adapter_cfg = parent / "adapter_config.json"
            if adapter_cfg.exists():
                try:
                    cfg = json.loads(adapter_cfg.read_text())
                    base_model = cfg.get("base_model_name_or_path")
                except Exception:
                    pass
            out_name = rel.replace("/", "-").replace("\\", "-") + "-lora-f16.gguf"
            outfile = MODELS_DIR / out_name
            if not outfile.exists():
                # Trigger background conversion
                cmd = [
                    str(PYTHON), str(CONVERT_LORA_TO_GGUF),
                    str(parent),
                    "--outfile", str(outfile),
                    "--outtype", "f16",
                ]
                if base_model:
                    cmd.extend(["--base-model-id", base_model])
                _record_lora_meta(out_name, base_model, rel)
                print(f"Auto-converting unconverted LoRA: {out_name}")
                _start_pipeline_task(
                    task_type=PipelineTaskType.CONVERT_LORA_TO_GGUF,
                    cmd=cmd,
                    input_path=str(parent),
                    output_path=str(outfile),
                    env={"NO_LOCAL_GGUF": "1"},
                )
            # Include it in the response (converting or ready)
            loras.append({
                "file": out_name,
                "base_model": base_model,
                "training_output": rel,
                "size": 0 if not outfile.exists() else outfile.stat().st_size,
                "modified": parent.stat().st_mtime,
                "converting": not outfile.exists(),
            })

    return sorted(loras, key=lambda l: l["modified"], reverse=True)


@app.post("/api/system/apply-loras")
def apply_loras(req: ApplyLorasRequest):
    """Configure llama-server to load LoRA GGUF adapters at inference time.

    Writes the --lora / --lora-scaled flags to an args file and restarts
    llama-server. Pass an empty loras list to remove all LoRAs.
    """
    args_parts = []

    for lora in req.loras:
        lora_file = lora.get("file", "")
        if not lora_file:
            raise HTTPException(status_code=400, detail="Each lora must have a 'file' field")

        lora_path = MODELS_DIR / lora_file
        if not lora_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"LoRA file not found: {lora_file}",
            )

        scale = lora.get("scale")
        if scale is not None:
            # llama.cpp now uses colon-separated format: FNAME:SCALE
            args_parts.extend(["--lora-scaled", f"{lora_path}:{float(scale)}"])
        else:
            args_parts.extend(["--lora", str(lora_path)])

    # Write args file (empty file = no LoRAs)
    LLAMA_SERVER_ARGS_FILE.write_text(" ".join(args_parts))

    # Restart llama-server to pick up new config
    restart_result = _restart_llama_server()

    return {
        "status": "applied",
        "loras": req.loras,
        "args": " ".join(args_parts) or "(none)",
        "restart": restart_result,
    }


@app.get("/api/system/active-loras")
def get_active_loras():
    """Return the currently configured LoRA adapters for llama-server."""
    if not LLAMA_SERVER_ARGS_FILE.exists():
        return {"loras": [], "raw_args": ""}

    raw = LLAMA_SERVER_ARGS_FILE.read_text().strip()
    if not raw:
        return {"loras": [], "raw_args": ""}

    # Parse the args back into structured form
    # New format: --lora-scaled FNAME:SCALE  (colon-separated)
    loras = []
    parts = raw.split()
    i = 0
    while i < len(parts):
        if parts[i] == "--lora-scaled" and i + 1 < len(parts):
            # Parse FNAME:SCALE format
            val = parts[i + 1]
            if ":" in val:
                fname, scale_str = val.rsplit(":", 1)
                loras.append({"file": Path(fname).name, "scale": float(scale_str)})
            else:
                loras.append({"file": Path(val).name, "scale": 1.0})
            i += 2
        elif parts[i] == "--lora" and i + 1 < len(parts):
            loras.append({"file": Path(parts[i + 1]).name, "scale": 1.0})
            i += 2
        else:
            i += 1

    return {"loras": loras, "raw_args": raw}


@app.post("/api/pipeline/bake", status_code=201)
def bake_model(req: BakeRequest) -> PipelineTask:
    """Bake multiple LoRA adapters into a single GGUF model.

    This is the full pipeline: merge LoRAs with weights -> convert to GGUF -> quantize.
    Use this when users are happy with their tested LoRA combinations and want to
    produce a final production model.
    """
    if not req.adapters:
        raise HTTPException(status_code=400, detail="At least one adapter is required")

    # Validate all adapter paths exist
    for adapter in req.adapters:
        adapter_path = Path(adapter.path)
        if not adapter_path.is_absolute():
            adapter_path = OUTPUTS_DIR / adapter.path
        if not adapter_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Adapter not found: {adapter.path}",
            )
        has_adapter = (adapter_path / "adapter_model.safetensors").exists() or (
            adapter_path / "adapter_model.bin"
        ).exists()
        if not has_adapter:
            raise HTTPException(
                status_code=400,
                detail=f"No adapter weights in: {adapter.path}",
            )

    # Check output doesn't already exist
    if req.quant_type:
        final_name = f"{req.output_name}-{req.quant_type}.gguf"
    else:
        final_name = f"{req.output_name}-{req.outtype}.gguf"
    final_path = MODELS_DIR / final_name

    if final_path.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Output file already exists: {final_name}",
        )

    # Build bake config JSON
    bake_config = {
        "base_model": req.base_model,
        "adapters": [
            {
                "path": str(OUTPUTS_DIR / a.path) if not Path(a.path).is_absolute() else a.path,
                "weight": a.weight,
            }
            for a in req.adapters
        ],
        "output_name": req.output_name,
        "outtype": req.outtype,
        "models_dir": str(MODELS_DIR),
        "convert_script": str(CONVERT_HF_TO_GGUF),
        "quantize_bin": str(LLAMA_QUANTIZE),
    }
    if req.quant_type:
        bake_config["quant_type"] = req.quant_type

    # Record bake lineage in models_meta.json
    _record_model_meta(
        model_filename=final_name,
        hf_repo=req.base_model,
        hf_filename=None,
        source_type="baked",
        quant=req.quant_type or req.outtype,
        bake_info={
            "base_model": req.base_model,
            "adapters": [{"path": a.path, "weight": a.weight} for a in req.adapters],
            "outtype": req.outtype,
            "quant_type": req.quant_type,
            "baked_at": datetime.now().isoformat(),
        },
    )

    # Write config to temp file
    config_file = LOGS_DIR / f"bake-config-{uuid.uuid4().hex[:8]}.json"
    config_file.write_text(json.dumps(bake_config, indent=2))

    cmd = [
        str(PYTHON), str(BAKE_SCRIPT),
        "--config", str(config_file),
    ]

    return _start_pipeline_task(
        task_type=PipelineTaskType.BAKE,
        cmd=cmd,
        input_path=json.dumps([a.path for a in req.adapters]),
        output_path=str(final_path),
    )


@app.get("/api/pipeline/tasks")
def list_pipeline_tasks() -> List[PipelineTask]:
    """List all pipeline tasks."""
    return sorted(_pipeline_tasks.values(), key=lambda t: t.created_at, reverse=True)


@app.get("/api/pipeline/tasks/{task_id}")
def get_pipeline_task(task_id: str) -> PipelineTask:
    """Get pipeline task details."""
    task = _pipeline_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Pipeline task not found")
    return task


@app.get("/api/pipeline/tasks/{task_id}/logs")
async def get_pipeline_task_logs(
    task_id: str, tail: int = Query(100), stream: bool = Query(False)
):
    """Get pipeline task logs."""
    task = _pipeline_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Pipeline task not found")

    log_path = Path(task.log_file)
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    if not stream:
        try:
            lines = log_path.read_text().splitlines()
            return {"lines": lines[-tail:]}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def generate():
        async with aiofiles.open(log_path, "r") as f:
            await f.seek(0, 2)
            while True:
                line = await f.readline()
                if line:
                    yield line
                else:
                    await asyncio.sleep(0.3)

    return StreamingResponse(generate(), media_type="text/plain")


@app.delete("/api/pipeline/tasks/{task_id}")
def cancel_pipeline_task(task_id: str):
    """Cancel a running pipeline task."""
    task = _pipeline_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Pipeline task not found")
    if task.status != PipelineTaskStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Task is not running")

    proc = _pipeline_processes.get(task_id)
    if proc:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        del _pipeline_processes[task_id]

    task.status = PipelineTaskStatus.FAILED
    task.error_message = "Cancelled by user"
    task.finished_at = datetime.now()
    _save_pipeline_tasks()

    # Clean up partial output files
    output_path = Path(task.output_path)
    if output_path.exists() and output_path.is_file():
        output_path.unlink()

    return {"status": "cancelled", "task_id": task_id}


# ─── Heretic Endpoints ─────────────────────────────────────────────────

@app.post("/api/heretic/run", status_code=201)
def run_heretic(req: HereticJobCreate) -> PipelineTask:
    """Run heretic abliteration on a model.

    Launches the non-interactive heretic wrapper as a background process.
    The output model is saved to OUTPUTS_DIR/heretic-<model_name>/.
    """
    # Sanitize model name for directory
    safe_name = req.model_name.replace("/", "--")
    output_name = f"heretic-{safe_name}"
    output_dir = OUTPUTS_DIR / output_name

    # Build command
    cmd = [
        str(PYTHON), str(HERETIC_SCRIPT),
        "--model", req.model_name,
        "--output-dir", str(output_dir),
        "--quantization", req.quantization,
        "--save-strategy", req.save_strategy,
    ]

    if req.n_trials is not None:
        cmd.extend(["--n-trials", str(req.n_trials)])

    # Copy default config to output dir so heretic can find it
    output_dir.mkdir(parents=True, exist_ok=True)
    if HERETIC_DEFAULT_CONFIG.exists():
        config_dest = output_dir / "config.toml"
        if not config_dest.exists():
            import shutil
            shutil.copy2(HERETIC_DEFAULT_CONFIG, config_dest)
        cmd.extend(["--config", str(config_dest)])

    return _start_pipeline_task(
        task_type=PipelineTaskType.HERETIC,
        cmd=cmd,
        input_path=req.model_name,
        output_path=str(output_dir),
        env={"HERETIC_MODEL": req.model_name},
    )


@app.get("/api/heretic/status/{task_id}")
def get_heretic_status(task_id: str) -> PipelineTask:
    """Get heretic task status (delegates to pipeline task infrastructure)."""
    task = _pipeline_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Heretic task not found")
    if task.task_type != PipelineTaskType.HERETIC:
        raise HTTPException(status_code=400, detail="Task is not a heretic task")
    return task


@app.get("/api/heretic/config")
async def get_heretic_config():
    """Return the default heretic configuration."""
    if not HERETIC_DEFAULT_CONFIG.exists():
        raise HTTPException(status_code=404, detail="Default heretic config not found")
    async with aiofiles.open(HERETIC_DEFAULT_CONFIG, "r") as f:
        content = await f.read()
    return {"config": content}


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
