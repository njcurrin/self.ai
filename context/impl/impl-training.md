---
created: "2026-04-11"
last_edited: "2026-04-11"
---
# Implementation Tracking: Training

Build site: context/plans/build-site.md

| Task | Status | Notes |
|------|--------|-------|
| T-009 | DONE | Existing code: Job state machine PENDING/RUNNING/COMPLETED/FAILED/CANCELLED. Approval via job.approved flag + _try_start_next_pending(). One-at-a-time FIFO. Atomic persistence via _save_jobs(). Error messages on FAILED. Verified at main.py:601-612, 773-790 |
| T-010 | DONE | Existing code: POST /api/configs (create), GET /api/configs (list), GET /api/configs/{name} (read), DELETE /api/configs/{name} (delete). Verified at main.py:811-875. Clone = create with different name (no dedicated endpoint needed). |
| T-011 | DONE | Existing code: job overrides merged at create time (config_data[k]=v for all overrides). Field aliasing via _FIELD_MAP in train.py:42. Verified at main.py:656-661, train.py:42-55 |
| T-012 | DONE | Existing code: YAML parse errors raise HTTPException 400 with detail. Config existence checks. Overrides applied after validation. Verified at main.py:634-661 |
| T-043 | DONE | Existing code: save_strategy="steps" at configurable intervals (saves_per_epoch), save_total_limit controls retention. Verified at train.py:399-432 |
| T-044 | DONE | Added resume_from_checkpoint to train.py. Supports auto-detect (True/"auto" scans output_dir for latest checkpoint-*), explicit path, or disabled. Passed to trainer.train(resume_from_checkpoint=). Config override compatible. |
| T-045 | DONE | Existing code: _refresh_metrics reads trainer_state.json log_history. GET /api/jobs/{id} returns job with metrics array. Verified at main.py:360-369, 700-710 |
| T-046 | DONE | Existing code: GET /api/jobs/{id}/logs?stream=true streams log file. Static fetch returns last N lines. Verified at main.py:712-740 |
| T-047 | DONE | Fixed in T-033: metrics refresh failure now catches JSONDecodeError/OSError and logs warning instead of silently swallowing. |
| T-035 | DONE | Existing code: chat_template (line 69), sharegpt (76-82), alpaca (87-100), completion (179-191) all implemented in train.py |
| T-036 | DONE | Existing code: concatenate_datasets at line 213, val_set_size train/test split at lines 205-210 |
| T-037 | DONE | Fixed: dataset load_dataset now wrapped in try/except with clear RuntimeError. Unknown format fallback already at lines 194-202 |
| T-038 | DONE | Existing code: LoraConfig with configurable r, alpha, dropout, target_modules at train.py:356-363 |
| T-039 | DONE | Existing code: QLoRA 4-bit (263-270), 8-bit (271-272), ZeRO-3 guard (258-261) |
| T-040 | DONE | Existing code: lora_target_linear at train.py:353-354, sets target_modules="all-linear" |
| T-041 | DONE | Existing code: ZeRO-2 normal loading, ZeRO-3 CPU offload + buffer migration at train.py:496-500 |
| T-042 | DONE | Fixed: _deepspeed_has_optimizer now logs warning on parse failure. adamw_torch forced when DS defines optimizer at train.py:415 |
