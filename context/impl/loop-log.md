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
- **Next:** T-033 (exception handling, now unblocked)
