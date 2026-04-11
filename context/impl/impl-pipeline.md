---
created: "2026-04-11"
last_edited: "2026-04-11"
---
# Implementation Tracking: Pipeline

Build site: context/plans/build-site.md

| Task | Status | Notes |
|------|--------|-------|
| T-022 | DONE | Pipeline tasks queued (QUEUED status) while training RUNNING. _try_start_queued_pipeline_tasks() called when training completes. Auto-starts all queued tasks. GPU_PIPELINE_TYPES set defines which types are blocked. |
