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
