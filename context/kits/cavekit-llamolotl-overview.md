---
created: "2026-04-10"
last_edited: "2026-04-10"
---

# Cavekit Overview

## Project
self.llamolotl — inference and training backbone of the self.ai platform. Dual-process Docker container running llama.cpp (inference) and FastAPI (training/pipeline API).

## Domain Index
| Domain | Cavekit File | Requirements | Status | Description |
|--------|-----------|-------------|--------|-------------|
| Training | cavekit-llamolotl-training.md | 7 | DRAFT | Job lifecycle, config, datasets, PEFT, DeepSpeed, checkpointing, progress |
| Inference | cavekit-llamolotl-inference.md | 5 | DRAFT | llama-server, models, LoRA hot-swap, chat templates, health |
| Pipeline | cavekit-llamolotl-pipeline.md | 6 | DRAFT | LoRA merge, HF→GGUF, quantization, bake, task lifecycle |
| Platform | cavekit-llamolotl-platform.md | 6 | DRAFT | Heretic removal, logging, exceptions, health, tests, decomposition |

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
- Checkpoint resume not wired (Training R6) — high priority
- LoRA hot-swap using restart instead of native API (Inference R3) — high priority
- Chat template hardcoded to qwen3 (Inference R4) — medium priority
- 13 silent exception swallows (Platform R3) — high priority
- Zero test coverage (Platform R5) — high priority
- 2800-line monolith (Platform R6) — structural, do after functional fixes
