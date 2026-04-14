---
created: "2026-04-10"
last_edited: "2026-04-13"
---

# Cavekit Overview

## Project
self.llamolotl — inference and training backbone of the self.ai platform. Dual-process Docker container running llama.cpp (inference) and FastAPI (training/pipeline API).

## Domain Index
| Domain | Cavekit File | Requirements | Status | Description |
|--------|-----------|-------------|--------|-------------|
| Training | cavekit-training.md | 7 | DONE | Job lifecycle, config, datasets, PEFT, DeepSpeed, checkpointing, progress |
| Inference | cavekit-inference.md | 5 | DONE | llama-server, models, LoRA hot-swap, chat templates, health |
| Pipeline | cavekit-pipeline.md | 6 | DONE | LoRA merge, HF→GGUF, quantization, bake, task lifecycle |
| Platform | cavekit-platform.md | 6 | DONE | Heretic removal, logging, exceptions, health, tests, decomposition |

## Cross-Reference Map
| Domain A | Interacts With | Interaction Type |
|----------|---------------|-----------------|
| Training | Pipeline | Training produces LoRA adapters → Pipeline transforms them |
| Training | Inference | Training produces adapters → Inference loads them (after pipeline conversion) |
| Pipeline | Inference | Pipeline produces GGUF models/adapters → Inference loads them |
| Platform | Training | Logging/error handling standards apply to training code |
| Platform | Inference | Health endpoint patterns, logging standards |
| Platform | Pipeline | Logging/error handling standards apply to pipeline code |

## Dependency Graph
1. **Platform (R1: Heretic removal)** — no dependencies, do first (reduces code surface)
2. **Platform (R2: Logging, R3: Exceptions)** — do early, improves all other work
3. **Training** and **Pipeline** — can proceed in parallel after platform foundations
4. **Inference** — can proceed in parallel, but LoRA hot-swap benefits from pipeline's LoRA→GGUF conversion
5. **Platform (R5: Tests, R6: Decomposition)** — do after functional work stabilizes

## Gaps / Open Questions
All domain requirements implemented and verified — see `context/impl/impl-{training,inference,pipeline,platform}.md` for task-level notes. Resolutions:
- Checkpoint resume wired (Training R6) — `train.py` resume_from_checkpoint with auto-detect/explicit path (T-044)
- LoRA hot-swap uses native `POST /lora-adapters` (Inference R3) — no restart when adapter already preloaded (T-029, T-030)
- Chat template no longer hardcoded (Inference R4) — GGUF-embedded templates + `/api/system/chat-template` override (T-050, T-051, T-052)
- 13 silent exception swallows replaced (Platform R3) — specific exception types + logging (T-033, T-034)
- pytest + 31 tests covering job state machine, configs, dataset detection, pipeline lifecycle (Platform R5) — T-059…T-062
- main.py decomposed to 42 lines across 4 routers + state.py (Platform R6) — T-055…T-058
