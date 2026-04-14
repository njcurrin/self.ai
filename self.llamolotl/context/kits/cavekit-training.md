---
created: "2026-04-10"
last_edited: "2026-04-10"
---

# Cavekit: Training

## Scope
Training job lifecycle, configuration management, dataset handling, PEFT/QLoRA setup, DeepSpeed integration, checkpointing, and progress/metrics reporting within self.llamolotl.

## Requirements

### R1: Job Lifecycle
**Description:** Training jobs follow an explicit state machine: PENDING → APPROVED → RUNNING → COMPLETED/FAILED. The UI controls approval via scheduled job windows. Only approved jobs are eligible to start. One job runs at a time (FIFO within approved jobs).
**Acceptance Criteria:**
- [ ] Job created via POST /api/jobs enters PENDING state
- [ ] Job does not start until approved=True
- [ ] Only one job runs at a time; next approved job starts when current completes/fails
- [ ] Job state transitions are atomic and persisted to jobs.json
- [ ] FAILED jobs include error_message with actionable detail (not just exit code)
**Dependencies:** none

### R2: Config Management
**Description:** Axolotl-compatible YAML training configs. CRUD operations with job-level overrides that merge cleanly into base config.
**Acceptance Criteria:**
- [ ] Configs created, read, updated, deleted, cloned via /api/configs endpoints
- [ ] Job-level overrides merge into base config without mutating the original
- [ ] Field aliasing works (micro_batch_size → per_device_train_batch_size, etc.)
- [ ] Invalid config fields produce clear validation errors, not silent defaults
**Dependencies:** none

### R3: Dataset Handling
**Description:** Load datasets from HuggingFace Hub. Support chat_template, sharegpt, alpaca, and completion formats. Multi-dataset concatenation and train/eval split.
**Acceptance Criteria:**
- [ ] Each format (chat_template, sharegpt, alpaca, completion) produces correctly formatted text
- [ ] Multiple datasets concatenate without data loss
- [ ] val_set_size creates reproducible train/eval split
- [ ] Unknown format falls back to completion with logged warning
- [ ] Dataset loading errors produce clear error messages with dataset name/path
**Dependencies:** R2 (config specifies datasets)

### R4: PEFT/QLoRA Setup
**Description:** LoRA and QLoRA via PEFT library. Configurable rank, alpha, dropout, target modules. QLoRA blocked under ZeRO-3.
**Acceptance Criteria:**
- [ ] LoRA adapter applied with configurable r, alpha, dropout, target_modules
- [ ] QLoRA (4-bit) works with BitsAndBytesConfig under ZeRO-2
- [ ] QLoRA + ZeRO-3 combination is blocked with clear warning
- [ ] lora_target_linear=true applies LoRA to all linear layers
- [ ] 8-bit quantization works as alternative to 4-bit
**Dependencies:** R2 (config specifies PEFT params)

### R5: DeepSpeed Integration
**Description:** ZeRO-2 and ZeRO-3 with CPU offload. Buffer migration for ZeRO-3. Optimizer conflict resolution when DeepSpeed defines its own optimizer.
**Acceptance Criteria:**
- [ ] ZeRO-2 config loads and trains successfully
- [ ] ZeRO-3 config loads with CPU offload, buffers migrate to GPU before training
- [ ] DeepSpeed optimizer conflict resolved (adamw_torch forced when DS defines optimizer)
- [ ] DeepSpeed config parse failure produces clear error (not silent fallthrough)
**Dependencies:** R2 (config specifies deepspeed path)

### R6: Checkpointing and Resume
**Description:** Save checkpoints at configurable intervals. Limit retained checkpoints. Support resuming training from latest checkpoint.
**Acceptance Criteria:**
- [ ] Checkpoints saved at configurable intervals (saves_per_epoch)
- [ ] save_total_limit controls maximum retained checkpoints
- [ ] Resume from checkpoint: detect latest checkpoint in output_dir, pass to trainer.train(resume_from_checkpoint=path)
- [ ] Resume config option in job submission (auto-detect or explicit path)
- [ ] Resumed training continues from correct step/epoch, not from scratch
**Dependencies:** R1 (job lifecycle manages output_dir)

### R7: Progress Reporting
**Description:** Training metrics extracted from trainer_state.json. Loss, learning rate, epoch, step. Live log streaming via SSE.
**Acceptance Criteria:**
- [ ] Metrics refreshed from latest checkpoint's trainer_state.json
- [ ] GET /api/jobs/{job_id} returns current metrics array
- [ ] GET /api/jobs/{job_id}/logs?stream=true streams live logs via SSE
- [ ] Static log fetch returns last N lines (configurable)
- [ ] Metrics refresh failure is logged, not silently swallowed
**Dependencies:** R1 (job provides output_dir and log path)

## Out of Scope
- Model conversion, quantization, LoRA merging (see cavekit-pipeline.md)
- Inference server management (see cavekit-inference.md)
- Node-based training pipeline UI (future investigation)
- W&B integration (optional, leave existing env var passthrough)

## Cross-References
- See also: cavekit-pipeline.md (pipeline consumes training outputs)
- See also: cavekit-inference.md (inference loads trained adapters)
- See also: cavekit-platform.md (logging/error handling spans training code)

## Changelog
