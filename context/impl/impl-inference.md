---
created: "2026-04-11"
last_edited: "2026-04-11"
---
# Implementation Tracking: Inference

Build site: context/plans/build-site.md

| Task | Status | Notes |
|------|--------|-------|
| T-050 | DONE | Removed hardcoded qwen3.jinja from llama-server-wrapper.sh. Now relies on GGUF-embedded tokenizer.chat_template. Optional override via /app/chat-template-override.jinja (written by UI upload endpoint). |
