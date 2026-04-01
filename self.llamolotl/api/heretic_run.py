"""
Non-interactive wrapper for heretic abliteration.

Usage:
    python heretic_run.py --model <hf_model_id> --output-dir <path> [--config <config.toml>] [--quantization none|bnb_4bit]

Runs the full heretic optimization loop and auto-saves the best trial
(lowest refusals, then lowest KL divergence) as a merged model.
"""

import argparse
import math
import logging
import os
import sys
import time
import warnings
from dataclasses import asdict
from os.path import commonprefix
from pathlib import Path

# Must set before importing torch
if (
    "PYTORCH_ALLOC_CONF" not in os.environ
    and "PYTORCH_CUDA_ALLOC_CONF" not in os.environ
):
    os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"

import optuna
import torch
import torch.nn.functional as F
import transformers
from optuna import Trial, TrialPruned
from optuna.exceptions import ExperimentalWarning
from optuna.samplers import TPESampler
from optuna.storages import JournalStorage
from optuna.storages.journal import JournalFileBackend, JournalFileOpenLock
from optuna.study import StudyDirection
from optuna.trial import TrialState

from heretic.config import Settings
from heretic.evaluator import Evaluator
from heretic.model import AbliterationParameters, Model
from heretic.utils import (
    empty_cache,
    format_duration,
    get_trial_parameters,
    load_prompts,
    print_memory_usage,
)
# Use standard print since heretic overrides it with rich
from builtins import print


def parse_args():
    parser = argparse.ArgumentParser(description="Non-interactive heretic abliteration")
    parser.add_argument("--model", required=True, help="HuggingFace model ID or path")
    parser.add_argument("--output-dir", required=True, help="Directory to save the output model")
    parser.add_argument("--config", default=None, help="Path to config.toml (optional)")
    parser.add_argument("--quantization", default="none", choices=["none", "bnb_4bit"],
                        help="Quantization method for loading the model")
    parser.add_argument("--n-trials", type=int, default=None,
                        help="Override number of optimization trials")
    parser.add_argument("--save-strategy", default="merge", choices=["merge", "adapter"],
                        help="How to save the result: merge (full model) or adapter (LoRA only)")
    return parser.parse_args()


def run_heretic(args):
    print(f"[heretic] Starting abliteration for model: {args.model}")
    print(f"[heretic] Output directory: {args.output_dir}")

    # Build settings kwargs
    settings_kwargs = {
        "model": args.model,
    }
    if args.quantization != "none":
        settings_kwargs["quantization"] = args.quantization
    if args.n_trials is not None:
        settings_kwargs["n_trials"] = args.n_trials

    # If config file provided, copy it to CWD as config.toml so pydantic-settings picks it up
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            cwd_config = Path("config.toml")
            if not cwd_config.exists():
                import shutil
                shutil.copy2(config_path, cwd_config)
                print(f"[heretic] Using config from {config_path}")

    # Suppress noisy logs
    transformers.logging.set_verbosity_error()
    logging.getLogger("lm_eval").setLevel(logging.ERROR)
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    warnings.filterwarnings("ignore", category=ExperimentalWarning)

    torch.set_grad_enabled(False)
    torch._dynamo.config.cache_size_limit = 64

    # Build settings - CLI args override config file via init_settings
    # We pass them directly to avoid interactive prompts
    settings = Settings(**settings_kwargs)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    settings.study_checkpoint_dir = str(checkpoint_dir)

    # Print GPU info
    if torch.cuda.is_available():
        count = torch.cuda.device_count()
        total_vram = sum(torch.cuda.mem_get_info(i)[1] for i in range(count))
        print(f"[heretic] Detected {count} CUDA device(s) ({total_vram / (1024**3):.2f} GB total VRAM)")
        for i in range(count):
            vram = torch.cuda.mem_get_info(i)[1] / (1024**3)
            print(f"[heretic]   GPU {i}: {torch.cuda.get_device_name(i)} ({vram:.2f} GB)")

    # Load model
    print(f"[heretic] Loading model {settings.model}...")
    model = Model(settings)
    print_memory_usage()

    # Load prompts
    print(f"[heretic] Loading good prompts from {settings.good_prompts.dataset}...")
    good_prompts = load_prompts(settings, settings.good_prompts)
    print(f"[heretic] {len(good_prompts)} good prompts loaded")

    print(f"[heretic] Loading bad prompts from {settings.bad_prompts.dataset}...")
    bad_prompts = load_prompts(settings, settings.bad_prompts)
    print(f"[heretic] {len(bad_prompts)} bad prompts loaded")

    # Auto batch size
    if settings.batch_size == 0:
        print("[heretic] Determining optimal batch size...")
        batch_size = 1
        best_batch_size = 1
        best_performance = -1

        while batch_size <= settings.max_batch_size:
            prompts = good_prompts * math.ceil(batch_size / len(good_prompts))
            prompts = prompts[:batch_size]
            try:
                model.get_responses(prompts)
                start_time = time.perf_counter()
                model.get_responses(prompts)
                end_time = time.perf_counter()
            except Exception:
                break

            response_lengths = [len(model.tokenizer.encode(r)) for r in model.get_responses(prompts)]
            performance = sum(response_lengths) / max(end_time - start_time, 0.001)

            if performance > best_performance:
                best_batch_size = batch_size
                best_performance = performance

            batch_size *= 2

        settings.batch_size = best_batch_size
        print(f"[heretic] Chosen batch size: {settings.batch_size}")

    # Check for response prefix
    print("[heretic] Checking for common response prefix...")
    prefix_check_prompts = good_prompts[:100] + bad_prompts[:100]
    responses = model.get_responses_batched(prefix_check_prompts)
    model.response_prefix = commonprefix(responses).rstrip(" ")

    recheck_prefix = False
    if model.response_prefix:
        recheck_prefix = True
        if model.response_prefix.startswith("<think>"):
            model.response_prefix = "<think></think>"
        elif model.response_prefix.startswith("<|channel|>analysis<|message|>"):
            model.response_prefix = "<|channel|>analysis<|message|><|end|><|start|>assistant<|channel|>final<|message|>"
        elif model.response_prefix.startswith("<thought>"):
            model.response_prefix = "<thought></thought>"
        elif model.response_prefix.startswith("[THINK]"):
            model.response_prefix = "[THINK][/THINK]"
        else:
            recheck_prefix = False

    if model.response_prefix:
        print(f"[heretic] Prefix found: {model.response_prefix!r}")

    if recheck_prefix:
        responses = model.get_responses_batched(prefix_check_prompts)
        additional_prefix = commonprefix(responses).rstrip(" ")
        if additional_prefix:
            model.response_prefix += additional_prefix

    evaluator = Evaluator(settings, model)

    # Calculate refusal directions
    print("[heretic] Calculating per-layer refusal directions...")
    good_residuals = model.get_residuals_batched(good_prompts)
    bad_residuals = model.get_residuals_batched(bad_prompts)

    good_means = good_residuals.mean(dim=0)
    bad_means = bad_residuals.mean(dim=0)
    refusal_directions = F.normalize(bad_means - good_means, p=2, dim=1)

    if settings.orthogonalize_direction:
        good_directions = F.normalize(good_means, p=2, dim=1)
        projection_vector = torch.sum(refusal_directions * good_directions, dim=1)
        refusal_directions = refusal_directions - projection_vector.unsqueeze(1) * good_directions
        refusal_directions = F.normalize(refusal_directions, p=2, dim=1)

    del good_residuals, bad_residuals
    empty_cache()

    # Setup study
    study_file = os.path.join(
        settings.study_checkpoint_dir,
        "".join([(c if (c.isalnum() or c in ["_", "-"]) else "--") for c in settings.model]) + ".jsonl",
    )
    lock_obj = JournalFileOpenLock(study_file)
    backend = JournalFileBackend(study_file, lock_obj=lock_obj)
    storage = JournalStorage(backend)

    # Check for existing study - auto-restart in non-interactive mode
    try:
        existing_study = storage.get_all_studies()[0]
        if existing_study is not None:
            print("[heretic] Found existing study, restarting from scratch for clean run...")
            os.unlink(study_file)
            backend = JournalFileBackend(study_file, lock_obj=lock_obj)
            storage = JournalStorage(backend)
    except IndexError:
        pass

    trial_index = 0
    start_time = time.perf_counter()

    def objective(trial: Trial) -> tuple:
        nonlocal trial_index
        trial_index += 1
        trial.set_user_attr("index", trial_index)

        direction_scope = trial.suggest_categorical("direction_scope", ["global", "per layer"])
        last_layer_index = len(model.get_layers()) - 1

        direction_index = trial.suggest_float("direction_index", 0.4 * last_layer_index, 0.9 * last_layer_index)
        if direction_scope == "per layer":
            direction_index = None

        parameters = {}
        for component in model.get_abliterable_components():
            max_weight = trial.suggest_float(f"{component}.max_weight", 0.8, 1.5)
            max_weight_position = trial.suggest_float(f"{component}.max_weight_position", 0.6 * last_layer_index, 1.0 * last_layer_index)
            min_weight = trial.suggest_float(f"{component}.min_weight", 0.0, 1.0)
            min_weight_distance = trial.suggest_float(f"{component}.min_weight_distance", 1.0, 0.6 * last_layer_index)

            parameters[component] = AbliterationParameters(
                max_weight=max_weight,
                max_weight_position=max_weight_position,
                min_weight=(min_weight * max_weight),
                min_weight_distance=min_weight_distance,
            )

        trial.set_user_attr("direction_index", direction_index)
        trial.set_user_attr("parameters", {k: asdict(v) for k, v in parameters.items()})

        print(f"[heretic] Running trial {trial_index}/{settings.n_trials}...")
        model.reset_model()
        model.abliterate(refusal_directions, direction_index, parameters)
        score, kl_divergence, refusals = evaluator.get_score()

        elapsed = time.perf_counter() - start_time
        remaining = (elapsed / trial_index) * (settings.n_trials - trial_index)
        print(f"[heretic] Trial {trial_index}: refusals={refusals}, KL={kl_divergence:.4f}, "
              f"elapsed={format_duration(elapsed)}, remaining~{format_duration(remaining)}")

        trial.set_user_attr("kl_divergence", kl_divergence)
        trial.set_user_attr("refusals", refusals)
        return score

    study = optuna.create_study(
        sampler=TPESampler(n_startup_trials=settings.n_startup_trials, n_ei_candidates=128, multivariate=True),
        directions=[StudyDirection.MINIMIZE, StudyDirection.MINIMIZE],
        storage=storage,
        study_name="heretic",
        load_if_exists=True,
    )
    study.set_user_attr("settings", settings.model_dump_json())
    study.set_user_attr("finished", False)

    print(f"[heretic] Starting optimization with {settings.n_trials} trials...")
    study.optimize(objective, n_trials=settings.n_trials)
    study.set_user_attr("finished", True)

    # Select best trial (lowest refusals, then lowest KL)
    completed_trials = [t for t in study.trials if t.state == TrialState.COMPLETE]
    if not completed_trials:
        print("[heretic] ERROR: No trials completed successfully!")
        sys.exit(1)

    sorted_trials = sorted(
        completed_trials,
        key=lambda t: (t.user_attrs["refusals"], t.user_attrs["kl_divergence"]),
    )
    best_trial = sorted_trials[0]

    print(f"[heretic] Best trial: #{best_trial.user_attrs['index']} "
          f"(refusals={best_trial.user_attrs['refusals']}, "
          f"KL={best_trial.user_attrs['kl_divergence']:.4f})")

    # Restore and save best trial
    print("[heretic] Restoring best trial model...")
    model.reset_model()
    model.abliterate(
        refusal_directions,
        best_trial.user_attrs["direction_index"],
        {k: AbliterationParameters(**v) for k, v in best_trial.user_attrs["parameters"].items()},
    )

    save_path = output_dir / "model"
    save_path.mkdir(parents=True, exist_ok=True)

    if args.save_strategy == "adapter":
        print(f"[heretic] Saving LoRA adapter to {save_path}...")
        model.model.save_pretrained(str(save_path))
    else:
        print(f"[heretic] Saving merged model to {save_path}...")
        merged_model = model.get_merged_model()
        merged_model.save_pretrained(str(save_path))
        del merged_model
        empty_cache()

    model.tokenizer.save_pretrained(str(save_path))

    # Write metadata
    import json
    meta = {
        "source_model": args.model,
        "quantization": args.quantization,
        "n_trials": settings.n_trials,
        "best_trial_index": best_trial.user_attrs["index"],
        "best_refusals": best_trial.user_attrs["refusals"],
        "best_kl_divergence": best_trial.user_attrs["kl_divergence"],
        "save_strategy": args.save_strategy,
        "parameters": {name: str(value) for name, value in get_trial_parameters(best_trial).items()},
    }
    (output_dir / "heretic_meta.json").write_text(json.dumps(meta, indent=2))

    print(f"[heretic] Done! Model saved to {save_path}")
    print(f"[heretic] Metadata saved to {output_dir / 'heretic_meta.json'}")


if __name__ == "__main__":
    args = parse_args()
    run_heretic(args)
