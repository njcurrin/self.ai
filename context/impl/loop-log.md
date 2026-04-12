### Iteration 1 (ui-security) — 2026-04-11
- **Tasks:** T-200 through T-206 — Tier 0 Quick Fixes (batched)
- **Tier:** 0
- **Status:** DONE (all 7)
- **Files:** memories.py, files.py, main.py, auth/+page.svelte, constants.ts, SVGPanZoom.svelte, MarkdownTokens.svelte, MarkdownInlineTokens.svelte
- **Validation:** Acceptance 25/25 (all AC covered)
- **Next:** T-207 through T-212 (Tier 0 hardening)

### Iteration 2 (ui-security) — 2026-04-11
- **Tasks:** T-207 through T-212 — Tier 0 Hardening (batched)
- **Tier:** 0
- **Status:** DONE (all 6)
- **Files:** env.py, security_headers.py, config.py, main.py, files.py, .env
- **Validation:** Acceptance 31/31 (all AC covered)
- **Notes:** Also set new WEBUI_SECRET_KEY in self.UI/.env per user request
- **Next:** T-213 through T-215 (Tier 0 test infrastructure foundation)

### Iteration 3 (ui-security) — 2026-04-11
- **Tasks:** T-213 through T-215 — Tier 0 Test Infrastructure Foundation (batched)
- **Tier:** 0
- **Status:** DONE (all 3)
- **Files:** pyproject.toml, requirements.txt, tests/mocks/external_services.py, vitest.config.ts, vitest-setup.ts, test-mocks/*.ts, package.json, Spinner.test.ts
- **Validation:** Acceptance 20/20 (config, mocks, frontend config all in place)
- **Notes:** Frontend deps need container rebuild to install. npm not in prod container.
- **Next:** T-216 through T-220 (Tier 1 — core test infra)

### Iteration 4 (ui-security) — 2026-04-11
- **Tasks:** T-216 through T-220 — Tier 1 Core Test Infrastructure (batched)
- **Tier:** 1
- **Status:** DONE (all 5)
- **Files:** tests/conftest.py (rewritten), integration-test.yml (pytest+vitest jobs)
- **Validation:** Acceptance criteria met for fixtures/CI. Cannot run tests in container until rebuild — code changes are host-only.
- **Notes:** Container has stale code (WEBUI_SECRET_KEY="" in container env). Rebuild needed.
- **Next:** T-221 (factories), then T-222+ (Tier 2 security tests)

### Iteration 5 (ui-security) — 2026-04-11
- **Tasks:** T-221 through T-235 — Tier 2 Factories + Security Tests
- **Tier:** 2
- **Status:** DONE (all 15)
- **Files:** tests/factories.py, tests/security/ (8 modules), conftest.py, files.py fix
- **Validation:** 115 passing, 21 xfailed (documented findings), 20 xpassed
- **Real findings surfaced:**
  - /api/v1/retrieval/ unauthenticated (known)
  - 4 utils endpoints unauthenticated (review needed)
  - 10 dict endpoints crash on empty body (KeyError, needs Pydantic)
  - null-byte filename %00 encoding leaks through upload
- **Next:** T-236–T-238 (Tier 3 validation)

### Iteration 6 (ui-security) — 2026-04-11
- **Tasks:** T-236 through T-238 — Tier 3 Validation (batched)
- **Tier:** 3
- **Status:** DONE (all 3)
- **Files:** tests/test_infrastructure_validation.py
- **Validation:** 122 passing total, 21 xfailed, 20 xpassed. Zero failures.
- **BUILD COMPLETE:** 39/39 tasks done.

---

### Iteration 1 — 2026-04-11
- **Task:** T-001 — Delete heretic_run.py and remove heretic endpoints
- **Tier:** 0
- **Status:** DONE
- **Files:** self.llamolotl/api/heretic_run.py (deleted), self.llamolotl/api/main.py
- **Validation:** Build N/A (Docker), Acceptance 2/2 (file deleted, endpoints removed)
- **Next:** T-002

### Iteration 2 — 2026-04-11
- **Task:** T-002 — Remove heretic Pydantic models, optuna dep, verify clean
- **Tier:** 0
- **Status:** DONE
- **Files:** self.llamolotl/api/main.py
- **Validation:** Acceptance 4/4 (model removed, optuna not in Dockerfile, no refs remain, Dockerfile clean)
- **Next:** T-003

### Iteration 3 — 2026-04-11
- **Task:** T-003 — Standardize logging in main.py
- **Tier:** 0
- **Status:** DONE
- **Files:** self.llamolotl/api/main.py
- **Validation:** Acceptance 1/1 (all print() replaced with log.warning/info/debug)
- **Next:** T-004

### Iteration 4 — 2026-04-11
- **Task:** T-004 — Standardize logging in bake_model.py
- **Tier:** 0
- **Status:** DONE
- **Files:** self.llamolotl/api/bake_model.py
- **Validation:** Acceptance 1/1 (custom log() wrapper replaced with logging module)
- **Next:** T-005

### Iteration 5 — 2026-04-11
- **Task:** T-005 — Configure log format and consistent logger naming
- **Tier:** 0
- **Status:** DONE
- **Files:** self.llamolotl/api/train.py, self.llamolotl/api/merge_lora.py, self.llamolotl/api/bake_model.py
- **Validation:** Acceptance 3/3 (all use __name__, format consistent, basicConfig added to bake)
- **Next:** T-050, T-044

### Iteration 6 — 2026-04-11
- **Task:** T-050 — Remove hardcoded chat template, rely on GGUF auto-detection
- **Tier:** 1
- **Status:** DONE
- **Files:** self.llamolotl/llama-server-wrapper.sh
- **Validation:** Acceptance 2/2 (no hardcoded qwen3.jinja, override file path supported)
- **Next:** T-044

### Iteration 7 — 2026-04-11
- **Task:** T-044 — Implement checkpoint resume
- **Tier:** 1
- **Status:** DONE
- **Files:** self.llamolotl/api/train.py
- **Validation:** Acceptance 3/3 (auto-detect latest checkpoint, explicit path, resume_from_checkpoint passed to trainer.train())
- **Next:** T-033

### Iteration 8 — 2026-04-11
- **Task:** T-033 — Fix exception handling: DeepSpeed config + metrics refresh
- **Tier:** 1
- **Status:** DONE
- **Files:** self.llamolotl/api/main.py, self.llamolotl/api/train.py
- **Validation:** Acceptance 2/2 (specific exceptions, logged warnings, preserves last-known metrics)
- **Next:** T-034

### Iteration 9 — 2026-04-11
- **Task:** T-034 — Fix remaining bare except:pass sites
- **Tier:** 1
- **Status:** DONE
- **Files:** self.llamolotl/api/main.py
- **Validation:** Acceptance 3/3 (all 13 sites addressed, specific types, no bare except:pass in critical paths)
- **Next:** Continue Tier 0 tasks

### Iteration 10 — 2026-04-11
- **Task:** T-006/T-007/T-008 — Composite health, GPU/disk, liveness/readiness
- **Tier:** 0
- **Status:** DONE
- **Files:** self.llamolotl/api/main.py
- **Validation:** Acceptance 6/6 (composite status, llama-server probe, GPU/disk, liveness/readiness, degraded handling)
- **Next:** T-029/T-030

### Iteration 11 — 2026-04-11
- **Task:** T-029/T-030 — LoRA hot-swap via native llama-server API
- **Tier:** 0
- **Status:** DONE
- **Files:** self.llamolotl/api/main.py
- **Validation:** Acceptance 4/4 (hot-swap via POST /lora-adapters, active-loras from native API, fallback to restart for new adapters)
- **Next:** T-022

### Iteration 12 — 2026-04-11
- **Task:** T-022 — Pipeline/training mutual exclusion + auto-start
- **Tier:** 0
- **Status:** DONE
- **Files:** self.llamolotl/api/main.py
- **Validation:** Acceptance 2/2 (QUEUED status while training runs, auto-start on training complete)
- **Next:** Verify remaining brownfield tasks

### Iteration 13 — 2026-04-11
- **Task:** T-037/T-042 — Fix dataset error handling + DeepSpeed optimizer parse logging
- **Tier:** 1
- **Status:** DONE
- **Files:** self.llamolotl/api/train.py
- **Validation:** Dataset load wrapped in try/except with clear error. _deepspeed_has_optimizer logs warning.
- **Next:** T-051/T-052

### Iteration 14 — 2026-04-11
- **Task:** T-051/T-052 — Custom template upload/clear + built-in template list
- **Tier:** 1
- **Status:** DONE
- **Files:** self.llamolotl/api/main.py
- **Validation:** POST/DELETE/GET /api/system/chat-template. Built-in template list endpoint.
- **Next:** Brownfield verification

### Iteration 15 — 2026-04-11
- **Task:** Bulk brownfield verification (T-009–T-049 remaining)
- **Status:** DONE
- **Notes:** Verified 35 brownfield tasks against acceptance criteria with code evidence. All criteria met in existing code. Two gaps fixed (T-037 dataset errors, T-042 DS optimizer logging).
- **Next:** Tier 2 (T-055–T-058 decomposition)

### Iteration 16 — 2026-04-11
- **Task:** T-055/T-056/T-057/T-058 — Decompose main.py into routers
- **Tier:** 2
- **Status:** DONE
- **Files:** self.llamolotl/api/main.py (42 lines), state.py (829), routers/jobs.py (328), routers/models.py (914), routers/pipeline.py (788), routers/system.py (276)
- **Validation:** 43 endpoints preserved, all syntax valid, pure structural refactor
- **Next:** Tier 3 (T-059–T-062 test infrastructure)

### Iteration 17 — 2026-04-11
- **Task:** T-059/T-060/T-061/T-062 — Test infrastructure + test suites
- **Tier:** 3
- **Status:** DONE
- **Files:** self.llamolotl/api/tests/conftest.py, test_jobs.py, test_config.py, test_pipeline.py, pytest.ini
- **Validation:** 30/30 tests passing in Docker container. Job state machine, config parsing, dataset formats, pipeline lifecycle all covered.
- **Next:** ALL TASKS COMPLETE
