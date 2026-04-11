---
created: "2026-04-11"
last_edited: "2026-04-11"
---
# Implementation Tracking: Inference

Build site: context/plans/build-site.md

| Task | Status | Notes |
|------|--------|-------|
| T-050 | DONE | Removed hardcoded qwen3.jinja from llama-server-wrapper.sh. Now relies on GGUF-embedded tokenizer.chat_template. Optional override via /app/chat-template-override.jinja (written by UI upload endpoint). |
| T-029 | DONE | apply-loras now checks loaded adapters via native GET /lora-adapters. Preload list updated in args file for restart path. |
| T-030 | DONE | apply-loras proxies to POST /lora-adapters when adapters already loaded (hot-swap, no restart). active-loras queries llama-server native API first, falls back to args file. |
| T-023 | DONE | Existing code: _restart_llama_server() calls supervisorctl restart with error handling. Wrapper reads /app/llama-server.args. Verified at main.py:1659-1670 |
| T-024 | DONE | Health endpoint now probes llama-server at localhost:8080/health, reports inference_healthy=false on failure. Covered by T-006 health implementation. |
| T-025 | DONE | Existing code: GET /api/models/available lists GGUFs with metadata (hf_repo, quant, source_type, pulled_at, trainable, split shards). Verified at main.py:919 |
| T-026 | DONE | Existing code: POST /api/models/pull downloads GGUF/safetensors from HF, records metadata via _record_model_meta, streams progress. Verified at main.py:1109 |
| T-027 | DONE | Existing code: POST /api/models/delete removes file (handles split shards + symlinks), removes metadata. Verified at main.py:1556 |
| T-028 | DONE | Existing code: POST /api/models/inspect queries HF repo for files/sizes. GET /api/models/available lists local. Browse via inspect endpoint. Verified at main.py:1057 |
| T-032 | DONE | Existing code: auto-detect unconverted adapters in list_available_loras() scans OUTPUTS_DIR for adapter_model.safetensors, triggers background _auto_convert_lora. Verified at main.py:2230-2270 |
| T-031 | DONE | Per-request LoRA handled by llama-server natively (lora field in completion requests). Training API proxies, does not need its own endpoint. |
| T-051 | DONE | POST /api/system/chat-template uploads custom .jinja template, stores at /app/chat-template-override.jinja, restarts server |
| T-052 | DONE | DELETE /api/system/chat-template clears override. GET returns current status. GET /api/system/chat-templates/builtin lists 42+ named templates |
| T-053 | DONE | Covered by T-006: composite health includes loaded_model, active_loras, gpu_memory from llama-server probe |
| T-054 | DONE | Covered by T-008: /health/live and /health/ready with degraded state handling |
