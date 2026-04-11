---
created: "2026-04-10"
last_edited: "2026-04-10"
---

# Cavekit: Pipeline

## Scope
Model transformation pipeline — LoRA merge, HF→GGUF conversion, LoRA→GGUF conversion, quantization, and the multi-step "bake" pipeline. All orchestrated as background pipeline tasks within self.llamolotl.

## Requirements

### R1: LoRA Merge
**Description:** Merge PEFT LoRA adapter(s) into base model, producing a full HF-format model. Single adapter via merge_lora.py, multi-adapter with weights via bake_model.py.
**Acceptance Criteria:**
- [ ] Single LoRA adapter merges into base model producing valid HF safetensors output
- [ ] Multi-adapter merge with per-adapter weights produces correct weighted combination
- [ ] Adapter compatibility with base model validated before merge begins
- [ ] Merge failure produces clear error with adapter/model details
- [ ] Output directory created if not exists; existing output prompts overwrite confirmation
**Dependencies:** none

### R2: HF to GGUF Conversion
**Description:** Convert HuggingFace safetensors models to GGUF format via llama.cpp's convert_hf_to_gguf.py.
**Acceptance Criteria:**
- [ ] Conversion produces valid GGUF file from HF safetensors input
- [ ] Output type selectable: f32, f16, bf16, q8_0, auto
- [ ] Input path validated (exists, contains expected files) before conversion starts
- [ ] Conversion progress reported to task status
- [ ] Failed conversion cleans up partial output
**Dependencies:** none

### R3: LoRA to GGUF Conversion
**Description:** Convert PEFT LoRA adapters (safetensors) to GGUF format for llama-server dynamic loading.
**Acceptance Criteria:**
- [ ] Conversion produces valid GGUF LoRA file from PEFT safetensors adapter
- [ ] Auto-conversion triggers when unconverted adapters detected in lora directory
- [ ] Background conversion does not block API responses
- [ ] Conversion status trackable via pipeline task API
**Dependencies:** none

### R4: Quantization
**Description:** Quantize GGUF models via llama-quantize binary. Full GGUF quant type support.
**Acceptance Criteria:**
- [ ] All standard quant types supported (IQ, Q, K variants as enumerated in main.py)
- [ ] Input validated as existing GGUF file before quantization starts
- [ ] Quantization progress reported to task status
- [ ] Output file named with quant type suffix for identification
- [ ] Failed quantization cleans up partial output
**Dependencies:** none

### R5: Bake Pipeline
**Description:** Multi-step pipeline: merge weighted LoRA adapters → convert to GGUF → optional quantize. Single task submission with internal step orchestration.
**Acceptance Criteria:**
- [ ] Single API call triggers full bake pipeline
- [ ] Each step (merge, convert, quantize) reports individual progress
- [ ] Pipeline can be configured to skip quantization step
- [ ] Failure at any step stops pipeline with clear indication of which step failed
- [ ] Intermediate artifacts accessible for debugging
**Dependencies:** R1 (merge), R2 (convert), R4 (quantize)

### R6: Task Lifecycle
**Description:** Pipeline tasks tracked in pipeline_tasks.json. Status polling, log streaming, error reporting.
**Acceptance Criteria:**
- [ ] Tasks created with unique ID, tracked in pipeline_tasks.json
- [ ] Task status queryable via GET endpoint
- [ ] Task logs streamable via SSE (same pattern as training jobs)
- [ ] Completed tasks retain status and output path
- [ ] Failed tasks retain error message and partial output info
- [ ] Pipeline tasks blocked while any training job is RUNNING — conversion/quantization queued until GPU is free
- [ ] When training completes, queued pipeline tasks start automatically (one at a time, not all simultaneously)
- [ ] At most one GPU pipeline task runs at a time to prevent GPU memory contention
**Dependencies:** none

## Out of Scope
- Dataset curation (see self.curator)
- Training job execution (see cavekit-llamolotl-training.md)
- Inference model loading (see cavekit-llamolotl-inference.md — but pipeline produces what inference loads)
- Node-based pipeline UI (future investigation)

## Cross-References
- See also: cavekit-llamolotl-training.md (training produces LoRA adapters that pipeline transforms)
- See also: cavekit-llamolotl-inference.md (inference loads GGUF models and adapters that pipeline produces)
- See also: cavekit-llamolotl-platform.md (logging standards, error handling patterns)

## Changelog
