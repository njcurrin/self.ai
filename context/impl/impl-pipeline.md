---
created: "2026-04-11"
last_edited: "2026-04-11"
---
# Implementation Tracking: Pipeline

Build site: context/plans/build-site.md

| Task | Status | Notes |
|------|--------|-------|
| T-013 | DONE | Existing code: BakeRequest accepts adapters list with per-adapter weight. Single + multi-adapter merge via bake_model.py step_merge(). Verified at main.py:2482, bake_model.py:38-110 |
| T-014 | DONE | Existing code: validates adapter paths exist, checks weights, 409 on output conflict, records bake lineage in metadata. Verified at main.py:2482-2570 |
| T-015 | DONE | Existing code: /api/pipeline/convert-to-gguf validates outtype against [f32,f16,bf16,q8_0,auto], runs convert_hf_to_gguf.py. Verified at main.py:2019 |
| T-016 | DONE | Existing code: input validation (safetensors + config.json checks), progress via pipeline task polling. Cleanup on cancel. Verified at main.py:2019-2080 |
| T-017 | DONE | Existing code: /api/pipeline/convert-lora-to-gguf auto-detects base model from adapter_config.json. Verified at main.py:2150 |
| T-018 | DONE | Existing code: uses _start_pipeline_task (background subprocess), polled by _poll_jobs, tracked in _pipeline_tasks. Verified at main.py:1668-1716 |
| T-019 | DONE | Existing code: /api/pipeline/quantize with full valid_quants list (IQ/Q/K/F variants). Validated and passed to llama-quantize. Verified at main.py:2090 |
| T-020 | DONE | Existing code: validates file exists + .gguf extension + valid quant type. Output named {stem}-{quant}.gguf. Progress via pipeline task. Verified at main.py:2090-2145 |
| T-021 | DONE | Existing code: pipeline task create/track/query at /api/pipeline/tasks, log streaming at /api/pipeline/tasks/{id}/logs?stream=true. Verified at main.py:2577-2624 |
| T-022 | DONE | Pipeline tasks queued (QUEUED status) while training RUNNING. _try_start_queued_pipeline_tasks() called when training completes. Auto-starts all queued tasks. GPU_PIPELINE_TYPES set defines which types are blocked. |
| T-048 | DONE | Existing code: POST /api/pipeline/bake triggers merge→convert→quantize via bake_model.py. Single API call. Verified at main.py:2544 |
| T-049 | DONE | Existing code: skip-quantize via quant_type=None, step progress via bake_model.py logging, failure handling via pipeline task status. Intermediate artifacts in work_dir. |
