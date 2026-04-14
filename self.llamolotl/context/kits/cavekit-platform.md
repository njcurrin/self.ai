---
created: "2026-04-10"
last_edited: "2026-04-10"
---

# Cavekit: Platform

## Scope
Cross-cutting infrastructure concerns for self.llamolotl: heretic removal, logging standardization, exception handling cleanup, health monitoring, test infrastructure, and main.py decomposition.

## Requirements

### R1: Heretic Removal
**Description:** Remove heretic_run.py and all references from the codebase. Clean removal — no stubs, no dead code, no orphaned dependencies.
**Acceptance Criteria:**
- [ ] heretic_run.py deleted
- [ ] All heretic-related endpoints removed from main.py
- [ ] All heretic-related Pydantic models removed
- [ ] optuna dependency removed if not used elsewhere
- [ ] No remaining references to "heretic" or "abliteration" in codebase
- [ ] Docker build still succeeds after removal
**Dependencies:** none

### R2: Logging Standardization
**Description:** Replace all bare print() calls with Python logging module. Consistent log levels, structured format across all modules.
**Acceptance Criteria:**
- [ ] main.py uses logging module instead of print() (all ~15 print sites)
- [ ] bake_model.py uses logging module instead of custom log() wrapper
- [ ] All modules use consistent logger naming (module-level logger = logging.getLogger(__name__))
- [ ] Log levels appropriate: INFO for lifecycle events, WARNING for degraded state, ERROR for failures, DEBUG for verbose detail
- [ ] Log format includes timestamp, level, module name
**Dependencies:** none

### R3: Exception Handling Cleanup
**Description:** Eliminate bare except Exception: pass blocks. Each site gets specific exception types, proper logging, and appropriate fallback behavior.
**Acceptance Criteria:**
- [ ] DeepSpeed config parse (train.py:252): catches JSONDecodeError/OSError, logs warning, defaults safely
- [ ] Metrics refresh (main.py:376): catches specific JSON errors, logs warning, preserves last-known metrics
- [ ] Output dir extraction (main.py:387): catches YAML errors, logs warning, returns explicit error not silent default
- [ ] All 13 bare except:pass sites in main.py addressed with specific exception types and logging
- [ ] No bare except Exception: pass remains in api/ directory
**Dependencies:** R2 (logging must be set up first)

### R4: Health and Readiness
**Description:** Composite health endpoint covering API, llama-server, GPU, and disk. Liveness vs readiness distinction.
**Acceptance Criteria:**
- [ ] GET /health returns composite status object
- [ ] Probes llama-server at localhost:8080/health for inference readiness
- [ ] Reports GPU availability via torch.cuda.is_available()
- [ ] Reports disk space on /models and /workspace volumes
- [ ] Liveness (API alive) vs readiness (inference ready) endpoints separated
- [ ] Health check failures on inference side report degraded state, don't crash API
**Dependencies:** none

### R5: Test Infrastructure
**Description:** Set up pytest with test structure. Priority coverage for critical business logic.
**Acceptance Criteria:**
- [ ] pytest configured with conftest.py and test directory structure
- [ ] Job state machine transitions tested (all valid and invalid transitions)
- [ ] Config parsing and field aliasing tested (axolotl compat)
- [ ] Dataset format detection tested (all 4 formats + unknown fallback)
- [ ] Pipeline task lifecycle tested
- [ ] Tests runnable inside Docker container
**Dependencies:** R6 (decomposed modules are easier to test)

### R6: main.py Decomposition
**Description:** Split 2800-line monolithic main.py into logical FastAPI router modules with shared state.
**Acceptance Criteria:**
- [ ] Job endpoints → routers/jobs.py
- [ ] Model endpoints → routers/models.py
- [ ] Pipeline endpoints → routers/pipeline.py
- [ ] System endpoints (restart, loras, health) → routers/system.py
- [ ] Shared state (jobs dict, pipeline tasks, config) → state.py or similar
- [ ] main.py reduced to app creation, router mounting, startup/shutdown hooks
- [ ] All existing endpoints maintain same paths and behavior
- [ ] No functionality change — pure structural refactor
**Dependencies:** R1 (remove heretic first, less code to move)

## Out of Scope
- CI/CD pipeline setup
- Dockerfile optimization
- supervisord replacement
- Documentation/README creation

## Cross-References
- See also: cavekit-training.md (logging/error fixes span training code)
- See also: cavekit-inference.md (health endpoint patterns)
- See also: cavekit-pipeline.md (logging/error fixes span pipeline code)

## Changelog
