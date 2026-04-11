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
