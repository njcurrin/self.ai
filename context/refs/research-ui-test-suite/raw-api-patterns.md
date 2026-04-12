## Agent: codebase-api-patterns — Findings

### 1. Response Format Consistency
- **`{"detail": "..."}` error shape is consistent** across all routers via `HTTPException`
- **Semantic mismatch:** `tasks.py:201-205` returns 200 `{"detail": "Tags generation is disabled"}` — error-shaped body for a no-op feature flag response
- **Inconsistent delete response:** `windows.py:78` returns `{"message": "Window deleted"}` while other delete endpoints return `bool`

### 2. Orphaned/Dead Endpoints
- **`GET /api/v1/memories/ef`** — unauthenticated debug endpoint, never called by frontend. Exposes embedding function invocation to any caller.
- **Duplicate GET `/evaluations/feedbacks/all`** — registered at evaluations.py:122 AND :140. Second handler is silently dead (FastAPI matches first).
- **`GET /api/v1/retrieval/ef/{text}`** — dev-only, correctly gated by `ENV == "dev"`

### 3. Database Transaction Issues
- **`get_db()` has no rollback on exception** — db.py:106-114. Session close auto-rolls back uncommitted work, but partial commits from mid-block `commit()` would persist.
- **`commit_session_after_request` middleware commits the wrong session** — main.py:872-876. Commits `scoped_session` but all model code uses `SessionLocal()` (non-scoped). Effectively dead code.
- **GPU queue read-then-write race** — gpu_queue.py:344-392. Protected by RedisLock when Redis configured; no-op lock without Redis. Theoretical in single-process deployments.

### 4. Pagination Inconsistency
- Three styles coexist: page-based (chats), skip/limit (channels, chats alternate), body limit (retrieval)
- No consistent pagination envelope (no `total`, `next_cursor`, `has_more`)
- **Full table scans:** `get_all_courses()`, `get_all_jobs()` fetch ALL records then filter in Python — training.py:175, eval_jobs.py:141

### 5. WebSocket/SSE Issues
- Socket.IO events informally typed but consistent shape
- **SSE dry-run proxy lacks `data:` prefix framing** — evaluations.py:1293-1309 passes raw lines without SSE frame format. EventSource clients can't parse proxy stream. Local path (1311-1347) uses correct SSE format.

### 6. Middleware Stack
Global: RedirectMiddleware, SecurityHeadersMiddleware, commit_session (dead), check_url (timing), inspect_websocket, CORSMiddleware, SessionMiddleware (OAuth conditional)

- **No global auth middleware** — all auth is per-endpoint via `Depends()`
- **Custom service routers not under `/api/v1/`** — `/curator`, `/lm-eval`, `/bigcode-eval`, `/llamolotl` mounted at root level vs other routers at `/api/v1/...`

### 7. Import/Structure Issues
- No circular imports found
- Deferred imports in `gpu_queue.py:117,308` suggest past avoidance of circular import issues
- PEP 8 violation: import after variable assignment in training.py:26-27 (no runtime impact)

### 8. Background Tasks
- Four startup asyncio tasks (fire-and-forget, no supervision): usage pool cleanup, crawl resume, GPU queue, curator classifier health
- Task failures silently dropped (Python default for unresolved tasks)
- Web crawl correctly uses `BackgroundTasks.add_task()` for endpoint-spawned work
- Streaming responses correctly use `BackgroundTask` for cleanup

### 9. Migration Schema Gap — HIGH RISK
- **`curator_job.dataset_name` and `curator_job.created_knowledge_id`** only exist in Peewee migration (019), NOT in Alembic migration
- Fresh deploy running only Alembic → missing columns → `AttributeError` in `_finalize_curator_job()`
- Peewee runs first (db.py:74 `handle_peewee_migration()`) so existing deploys work, but the hybrid migration system is fragile

### Risk Summary

| Issue | Severity |
|---|---|
| Schema gap: curator_job columns in Peewee only | High |
| `GET /memories/ef` unauthenticated debug endpoint | High |
| Startup tasks fire-and-forget, no supervision | Medium |
| Full table scans in training/eval list queries | Medium |
| SSE proxy framing mismatch | Medium |
| Duplicate feedbacks/all route (dead handler) | Medium |
| commit_session middleware on wrong session (dead code) | Low |
| Pagination inconsistency | Low |
| Delete response shape inconsistency | Low |
