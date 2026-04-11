---
created: "2026-04-11"
last_edited: "2026-04-11"
---
# Implementation Tracking: Platform

Build site: context/plans/build-site.md

| Task | Status | Notes |
|------|--------|-------|
| T-001 | DONE | Deleted heretic_run.py, removed 3 heretic endpoints (/api/heretic/run, /status, /config), removed HERETIC enum value from PipelineTaskType, removed HERETIC_SCRIPT/HERETIC_DIR/HERETIC_DEFAULT_CONFIG constants |
| T-002 | DONE | Removed HereticJobCreate Pydantic model, verified no optuna dep in Dockerfile (was only imported in deleted file), no remaining heretic/abliteration references in api/ |
| T-003 | DONE | Replaced 6 print() calls in main.py with log.warning/info/debug. Added logging import and module-level logger |
| T-004 | DONE | Replaced custom log() wrapper in bake_model.py with logging.getLogger(__name__). All log() calls now log.info() |
| T-005 | DONE | All modules use getLogger(__name__). Format consistent: %(asctime)s %(levelname)s %(name)s. Added basicConfig to bake_model.py |
| T-033 | DONE | Fixed DeepSpeed config parse (train.py), metrics refresh (main.py), output dir extraction. Catches specific exceptions (JSONDecodeError, OSError, YAMLError), logs warnings, preserves last-known metrics |
| T-034 | DONE | Fixed all remaining bare except:pass — adapter_config reads (3 sites), log tail read, HF cache scan, size calculations, symlink cleanup. All now use specific exception types + logging. Remaining OSError:pass in download monitoring are correct (transient file stat) |
| T-006 | DONE | Composite health endpoint probes llama-server at localhost:8080/health, reports api_healthy + inference_healthy, status "ok"/"degraded" |
| T-007 | DONE | Health includes gpu_available, gpu_memory_used/total_gb (torch.cuda), disk_models_free_gb, disk_workspace_free_gb (os.statvfs) |
| T-008 | DONE | Added /health/live (liveness) and /health/ready (readiness). Readiness checks inference server. Degraded state on inference failure |
| T-055 | DONE | Extracted jobs router: routers/jobs.py (328 lines, 11 endpoints — jobs CRUD, configs CRUD, outputs) |
| T-056 | DONE | Extracted models router: routers/models.py (914 lines, 11 endpoints — GGUF, HF cache, FastText) and pipeline router: routers/pipeline.py (788 lines, 11 endpoints) |
| T-057 | DONE | Extracted system router: routers/system.py (276 lines, 10 endpoints — server mgmt, LoRAs, health, templates). Created state.py (829 lines — constants, models, shared state, helpers) |
| T-058 | DONE | main.py reduced to 42 lines: app creation + 4 router mounts + startup event. All 43 endpoints preserve exact paths. Pure structural refactor. |
