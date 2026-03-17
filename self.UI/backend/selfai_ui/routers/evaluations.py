import html
import json
import logging
import math
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from selfai_ui.models.users import Users, UserModel
from selfai_ui.models.feedbacks import (
    FeedbackModel,
    FeedbackResponse,
    FeedbackForm,
    Feedbacks,
)

from selfai_ui.constants import ERROR_MESSAGES
from selfai_ui.utils.auth import get_admin_user, get_verified_user

log = logging.getLogger(__name__)

router = APIRouter()

BIGCODE_RESULTS_DIR = Path(
    os.environ.get("BIGCODE_RESULTS_DIR", "/app/backend/data/bigcode-results")
)


############################
# GetConfig
############################


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_EVALUATION_ARENA_MODELS": request.app.state.config.ENABLE_EVALUATION_ARENA_MODELS,
        "EVALUATION_ARENA_MODELS": request.app.state.config.EVALUATION_ARENA_MODELS,
    }


############################
# UpdateConfig
############################


class UpdateConfigForm(BaseModel):
    ENABLE_EVALUATION_ARENA_MODELS: Optional[bool] = None
    EVALUATION_ARENA_MODELS: Optional[list[dict]] = None


@router.post("/config")
async def update_config(
    request: Request,
    form_data: UpdateConfigForm,
    user=Depends(get_admin_user),
):
    config = request.app.state.config
    if form_data.ENABLE_EVALUATION_ARENA_MODELS is not None:
        config.ENABLE_EVALUATION_ARENA_MODELS = form_data.ENABLE_EVALUATION_ARENA_MODELS
    if form_data.EVALUATION_ARENA_MODELS is not None:
        config.EVALUATION_ARENA_MODELS = form_data.EVALUATION_ARENA_MODELS
    return {
        "ENABLE_EVALUATION_ARENA_MODELS": config.ENABLE_EVALUATION_ARENA_MODELS,
        "EVALUATION_ARENA_MODELS": config.EVALUATION_ARENA_MODELS,
    }


class FeedbackUserResponse(FeedbackResponse):
    user: Optional[UserModel] = None


@router.get("/feedbacks/all", response_model=list[FeedbackUserResponse])
async def get_all_feedbacks(user=Depends(get_admin_user)):
    feedbacks = Feedbacks.get_all_feedbacks()
    return [
        FeedbackUserResponse(
            **feedback.model_dump(), user=Users.get_user_by_id(feedback.user_id)
        )
        for feedback in feedbacks
    ]


@router.delete("/feedbacks/all")
async def delete_all_feedbacks(user=Depends(get_admin_user)):
    success = Feedbacks.delete_all_feedbacks()
    return success


@router.get("/feedbacks/all/export", response_model=list[FeedbackModel])
async def get_all_feedbacks(user=Depends(get_admin_user)):
    feedbacks = Feedbacks.get_all_feedbacks()
    return [
        FeedbackModel(
            **feedback.model_dump(), user=Users.get_user_by_id(feedback.user_id)
        )
        for feedback in feedbacks
    ]


@router.get("/feedbacks/user", response_model=list[FeedbackUserResponse])
async def get_feedbacks(user=Depends(get_verified_user)):
    feedbacks = Feedbacks.get_feedbacks_by_user_id(user.id)
    return feedbacks


@router.delete("/feedbacks", response_model=bool)
async def delete_feedbacks(user=Depends(get_verified_user)):
    success = Feedbacks.delete_feedbacks_by_user_id(user.id)
    return success


@router.post("/feedback", response_model=FeedbackModel)
async def create_feedback(
    request: Request,
    form_data: FeedbackForm,
    user=Depends(get_verified_user),
):
    feedback = Feedbacks.insert_new_feedback(user_id=user.id, form_data=form_data)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    return feedback


@router.get("/feedback/{id}", response_model=FeedbackModel)
async def get_feedback_by_id(id: str, user=Depends(get_verified_user)):
    feedback = Feedbacks.get_feedback_by_id_and_user_id(id=id, user_id=user.id)

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return feedback


@router.post("/feedback/{id}", response_model=FeedbackModel)
async def update_feedback_by_id(
    id: str, form_data: FeedbackForm, user=Depends(get_verified_user)
):
    feedback = Feedbacks.update_feedback_by_id_and_user_id(
        id=id, user_id=user.id, form_data=form_data
    )

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return feedback


@router.delete("/feedback/{id}")
async def delete_feedback_by_id(id: str, user=Depends(get_verified_user)):
    if user.role == "admin":
        success = Feedbacks.delete_feedback_by_id(id=id)
    else:
        success = Feedbacks.delete_feedback_by_id_and_user_id(id=id, user_id=user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return success


############################
# Code Tests (BigCode Eval)
############################

# Sanitization for model-generated content in evaluation results.
# Model output can contain arbitrary strings (XSS payloads, control chars, etc.)
# that must be neutralized before serving to the UI.

_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-]{0,127}$")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MAX_STRING_LEN = 512 * 1024


def _sanitize_string(s: str) -> str:
    s = _CONTROL_CHAR_RE.sub("", s)
    if len(s) > _MAX_STRING_LEN:
        s = s[:_MAX_STRING_LEN] + "\n... [truncated]"
    return html.escape(s, quote=True)


def _sanitize_value(obj: Any) -> Any:
    if isinstance(obj, str):
        return _sanitize_string(obj)
    elif isinstance(obj, dict):
        return {k: _sanitize_value(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_value(item) for item in obj]
    return obj


def _validate_result_id(result_id: str) -> str:
    if not _SAFE_ID_RE.match(result_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid result ID",
        )
    return result_id


def _extract_base_id(results_filename: str) -> str:
    """Extract the base id from a results filename stem (remove '-results' suffix)."""
    stem = Path(results_filename).stem if results_filename.endswith(".json") else results_filename
    if stem.endswith("-results"):
        return stem[:-len("-results")]
    return stem


def _list_result_files() -> list[dict]:
    """Scan the bigcode results directory for *-results.json summary files."""
    results = []
    if not BIGCODE_RESULTS_DIR.is_dir():
        return results

    for path in sorted(BIGCODE_RESULTS_DIR.glob("*-results.json")):
        try:
            data = json.loads(path.read_text())
            config = data.get("config", {})
            model_name = config.get("model", path.stem)
            tasks = config.get("tasks", "unknown")
            base_id = _extract_base_id(path.name)

            # Try to get created_at from .jobs.json
            created_at = None
            jobs_file = BIGCODE_RESULTS_DIR / ".jobs.json"
            if jobs_file.is_file():
                try:
                    jobs = json.loads(jobs_file.read_text())
                    if base_id in jobs:
                        created_at = jobs[base_id].get("created_at")
                except Exception:
                    pass

            # Build a summary entry
            scores = {k: v for k, v in data.items() if k != "config"}
            results.append(_sanitize_value(
                {
                    "id": base_id,
                    "filename": path.name,
                    "model": model_name,
                    "tasks": tasks,
                    "scores": scores,
                    "config": config,
                    "created_at": created_at,
                }
            ))
        except Exception as e:
            log.warning(f"Failed to parse {path}: {e}")

    return results


def _load_details(base_id: str) -> list[dict] | None:
    """Load per-task details for a given result set."""
    if not BIGCODE_RESULTS_DIR.is_dir():
        return None

    # Details files: {base_id}-details_{task}_{timestamp}.json or {base_id}-details_{task}.json
    matches = sorted(BIGCODE_RESULTS_DIR.glob(f"{base_id}-details_*.json"))
    if not matches:
        # Fallback: try the old pattern
        matches = sorted(BIGCODE_RESULTS_DIR.glob(f"{base_id}_*.json"))

    for path in matches:
        # Skip generation files
        if "-generations_" in path.name or path.name.endswith("-results.json"):
            continue
        try:
            data = json.loads(path.read_text())
            if isinstance(data, list):
                return _sanitize_value(data)
        except Exception as e:
            log.warning(f"Failed to parse details {path}: {e}")

    return None


def _compute_quartile_scores(details: list[dict]) -> dict:
    """Compute pass rates for each quartile of tasks."""
    total = len(details)
    if total == 0:
        return {"q1": 0, "q2": 0, "q3": 0, "q4": 0, "total": 0}

    q_size = math.ceil(total / 4)
    quartiles = {}
    for i, label in enumerate(["q1", "q2", "q3", "q4"]):
        start = i * q_size
        end = min(start + q_size, total)
        chunk = details[start:end]
        if chunk:
            passed = sum(1 for t in chunk if all(s.get("passed", False) for s in t.get("samples", [])))
            quartiles[label] = round(passed / len(chunk) * 100, 1)
        else:
            quartiles[label] = 0

    all_passed = sum(1 for t in details if all(s.get("passed", False) for s in t.get("samples", [])))
    quartiles["total"] = round(all_passed / total * 100, 1)
    return quartiles


@router.get("/codetests")
async def get_code_tests(user=Depends(get_admin_user)):
    """List all bigcode evaluation result summaries."""
    return _list_result_files()


@router.get("/codetests/summary")
async def get_code_tests_summary(user=Depends(get_admin_user)):
    """Aggregate results by model across all benchmarks.

    Returns a list of models with their pass@1 scores per benchmark and average.
    """
    all_results = _list_result_files()

    # Group by model: for each model+benchmark, keep the best (latest) score
    model_data: dict[str, dict] = defaultdict(lambda: {"benchmarks": {}, "runs": 0})
    benchmarks_seen: set[str] = set()

    for r in all_results:
        model = r["model"]
        task = r["tasks"]
        benchmarks_seen.add(task)
        model_data[model]["runs"] += 1

        # Extract pass@1 score
        for _task_key, metrics in r["scores"].items():
            if isinstance(metrics, dict) and "pass@1" in metrics:
                score = round(metrics["pass@1"] * 100, 1)
                # Keep the latest (highest id) score per benchmark
                if task not in model_data[model]["benchmarks"] or score > model_data[model]["benchmarks"][task]:
                    model_data[model]["benchmarks"][task] = score

    # Build response
    summary = []
    for model_name, data in sorted(model_data.items()):
        benchmarks = data["benchmarks"]
        scores_list = list(benchmarks.values())
        avg = round(sum(scores_list) / len(scores_list), 1) if scores_list else 0
        summary.append({
            "model": model_name,
            "benchmarks": benchmarks,
            "average": avg,
            "runs": data["runs"],
        })

    return {
        "models": summary,
        "benchmark_names": sorted(benchmarks_seen),
    }


@router.get("/codetests/benchmark/{benchmark_name}")
async def get_code_tests_benchmark(benchmark_name: str, user=Depends(get_admin_user)):
    """Get per-model quartile pass rates for a specific benchmark."""
    if not _SAFE_ID_RE.match(benchmark_name):
        raise HTTPException(status_code=400, detail="Invalid benchmark name")

    all_results = _list_result_files()
    # Filter to this benchmark
    benchmark_results = [r for r in all_results if r["tasks"] == benchmark_name]

    # Group by model, use latest run per model
    model_latest: dict[str, dict] = {}
    for r in benchmark_results:
        model = r["model"]
        if model not in model_latest:
            model_latest[model] = r
        else:
            # Keep the one with the higher id (later run)
            if r["id"] > model_latest[model]["id"]:
                model_latest[model] = r

    rows = []
    for model_name, result in sorted(model_latest.items()):
        details = _load_details(result["id"])
        if details:
            quartiles = _compute_quartile_scores(details)
        else:
            # Fall back to overall score
            score = 0
            for _k, metrics in result["scores"].items():
                if isinstance(metrics, dict) and "pass@1" in metrics:
                    score = round(metrics["pass@1"] * 100, 1)
            quartiles = {"q1": score, "q2": score, "q3": score, "q4": score, "total": score}

        rows.append({
            "model": model_name,
            "result_id": result["id"],
            **quartiles,
        })

    return {"benchmark": benchmark_name, "rows": rows}


@router.get("/codetests/model-runs/{model_name:path}")
async def get_model_runs(model_name: str, user=Depends(get_admin_user)):
    """List all evaluation runs for a specific model."""
    all_results = _list_result_files()
    runs = [r for r in all_results if r["model"] == model_name]

    # Sort by created_at descending if available, else by id
    runs.sort(key=lambda r: r.get("created_at") or r["id"], reverse=True)

    return runs


@router.get("/codetests/{result_id}")
async def get_code_test_details(result_id: str, user=Depends(get_admin_user)):
    """Get per-task details for a specific evaluation run."""
    _validate_result_id(result_id)
    details = _load_details(result_id)
    if details is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Details file not found for this evaluation run.",
        )
    return details
