---
created: "2026-04-10"
last_edited: "2026-04-10"
---

# Cavekit: Inference

## Scope
llama.cpp server management, model loading/listing/pulling, LoRA adapter hot-swap via native API, chat template handling, and health monitoring within self.llamolotl.

## Requirements

### R1: Server Lifecycle
**Description:** llama-server managed via supervisord. Start, stop, restart. Wrapper script reads dynamic args (model path, LoRA preloads, optional template override) on each start.
**Acceptance Criteria:**
- [ ] llama-server starts via supervisord on container boot
- [ ] Restart via POST /api/system/restart-llama-server triggers supervisord restart
- [ ] Wrapper script reads /app/llama-server.args for dynamic CLI flags
- [ ] Server startup failure is detected and reported via health endpoint
**Dependencies:** none

### R2: Model Management
**Description:** List local GGUF models, list available on HF Hub, pull from HF, register metadata, delete. No validation on pull (by design — future HF container will handle this).
**Acceptance Criteria:**
- [ ] GET /api/models lists local GGUF models with metadata
- [ ] GET /api/models/available lists models from HF Hub
- [ ] POST /api/models/pull downloads GGUF from HF Hub to /models
- [ ] Model metadata persisted in models_meta.json (quant type, source, trainable flag)
- [ ] DELETE removes model file and metadata entry
**Dependencies:** none

### R3: LoRA Hot-Swap
**Description:** Use llama-server's native LoRA API for runtime adapter control. Preload adapters at startup with --lora-init-without-apply. Scale control via POST /lora-adapters proxy. Per-request LoRA passthrough. Remove restart-based swap pattern.
**Acceptance Criteria:**
- [ ] Adapters preloaded at startup with --lora-init-without-apply (scale 0)
- [ ] POST /api/system/apply-loras proxies to llama-server POST /lora-adapters (no restart)
- [ ] GET /api/system/active-loras proxies to llama-server GET /lora-adapters
- [ ] Per-request LoRA supported: requests to /v1/chat/completions can include lora field
- [ ] New adapters added to preload list trigger server restart only when necessary (new adapter not yet loaded)
- [ ] Auto-detect unconverted safetensors adapters and delegate conversion to Pipeline domain (cavekit-llamolotl-pipeline.md R3)
**Dependencies:** none

### R4: Chat Template Handling
**Description:** Remove hardcoded qwen3.jinja. Rely on GGUF-embedded tokenizer.chat_template by default. Support optional UI-provided custom template file. Keep --chat-template/--chat-template-file as override for edge cases.
**Acceptance Criteria:**
- [ ] No hardcoded chat template in llama-server-wrapper.sh
- [ ] GGUF models with embedded tokenizer.chat_template auto-detected by llama-server
- [ ] UI can upload a custom .jinja template file via API endpoint
- [ ] Custom template stored on disk and passed via --chat-template-file on next server start
- [ ] Template override can be cleared to revert to GGUF auto-detection
- [ ] 52 built-in named templates available as fallback via --chat-template flag
**Dependencies:** R1 (server restart needed for template changes)

### R5: Health and Readiness
**Description:** Composite health endpoint that checks API health AND llama-server status. Report loaded model, active LoRAs, GPU memory. Distinguish liveness (API process alive) from readiness (inference server accepting requests).
**Acceptance Criteria:**
- [ ] GET /health returns composite status: api_healthy + inference_healthy
- [ ] Inference health checked by probing llama-server at localhost:8080/health
- [ ] Response includes: loaded model name, active LoRA list, GPU memory usage
- [ ] Liveness probe (is API process alive) vs readiness probe (can it serve inference) distinguished
- [ ] Health check failure on inference side does not crash API — reports degraded state
**Dependencies:** R3 (active LoRAs reported in health)

## Out of Scope
- Model validation on pull (future dedicated HF container)
- sglang migration investigation (future)
- Training job execution (see cavekit-llamolotl-training.md)
- Model conversion/quantization (see cavekit-llamolotl-pipeline.md)

## Cross-References
- See also: cavekit-llamolotl-pipeline.md (produces GGUF models and LoRA adapters that inference loads)
- See also: cavekit-llamolotl-training.md (produces LoRA adapters that need conversion)
- See also: cavekit-llamolotl-platform.md (health endpoint patterns, logging standards)

## Changelog
