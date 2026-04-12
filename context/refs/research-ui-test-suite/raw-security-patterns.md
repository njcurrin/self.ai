## Agent: codebase-security-patterns — Findings

### 1. Authentication/Authorization Patterns

- **Consistent DI-based auth** across all 32 routers (363 `Depends(get_verified_user/get_admin_user)` occurrences). Solid baseline.
- **JWT HS256** with three auth paths: Bearer JWT, API key (`sk-`), JIT eval token (`eval-`)
- **JIT eval tokens have no expiry** — valid until explicit revocation. Leaked token stays valid.

### 2. Unauthenticated Endpoints

| Endpoint | What it leaks |
|---|---|
| `/api/v1/retrieval/` GET | embedding engine, model names, chunk sizes, RAG template |
| `/api/config` GET | App name, version, OAuth providers, **Google Drive API key + client_id** |
| `/health`, `/health/db` | Health status (appropriate) |
| `/api/version`, `/api/changelog` | Version info (appropriate) |

### 3. Role-Based Access Control

- Two roles: admin, user. Per-object ownership checks exist.
- Fine-grained permissions via `has_permission()` for workspace features.
- **`BYPASS_MODEL_ACCESS_CONTROL` env var** silently disables all model-level ACL when True.

### 4. Input Validation

**Raw `dict` (no Pydantic):**
- `POST /api/chat/completions` — `form_data: dict`
- `POST /api/completions` — `form_data: dict`
- `POST /api/chat/completed` — `form_data: dict`
- `POST /api/chat/actions/{action_id}` — `form_data: dict`
- `POST /llamolotl/chat/completions` — `form_data: dict`
- `POST /openai/.../chat/completions` — `form_data: dict`
- Multiple tasks endpoints — `form_data: dict`
- `POST /api/v1/users/user/info/update` — **merges arbitrary keys into user.info**

**Pydantic used correctly on:** admin/config endpoints, training forms, job windows, eval forms.

### 5. File Uploads — Critical Gaps

- **No server-side file size limit enforcement** — `FILE_MAX_SIZE` is client-side advisory only
- **No MIME type allowlist** — any file type accepted and stored
- Path traversal mitigated (`os.path.basename` + UUID prefix)
- Audio has 25MB hardcoded limit; general uploads have none

### 6. CORS, CSRF, Rate Limiting

- **CORS: Wildcard `*` default** with `allow_credentials=True` — permissive misconfiguration
- **No CSRF protection** — no tokens, no middleware. SameSite=lax provides partial mitigation.
- **No rate limiting** — zero brute-force protection on login/API key endpoints
- **Security headers entirely opt-in** — none set by default unless env vars configured
- **Session cookie `secure=false` by default** — transmits over HTTP

### 7. Critical Security Issues

**CRITICAL:**
- **Default JWT secret `"t0p-s3cr3t"`** — env.py:358-363. Well-known (public in Open-WebUI repo). Deployments not overriding this use a predictable key → forged JWTs with admin role.
- **`WEBUI_AUTH=False` creates hardcoded `admin@localhost`/`admin`** — auths.py:330-343. Intended for local/air-gap but critical if exposed.
- **`exec()` on user-supplied Python code** — plugin.py:101,145. By-design RCE for tool/function creators. Any user with workspace permission can execute arbitrary Python on server.
- **Arbitrary pip install from tool frontmatter** — plugin.py:173. No package validation.

### 8. SQL Injection / Command Injection / Path Traversal / SSRF

- **No SQL injection risk** — SQLAlchemy ORM throughout, no raw user input in queries
- **SSRF:** Admin verify_connection endpoints make unvalidated HTTP requests. DNS rebinding acknowledged but not fully mitigated in retrieval URL validation.
- **Path traversal mitigated** on upload

### 9. Secrets Management

- Default JWT secret not blocked if unchanged (only blocks empty string)
- Google Drive API key returned unauthenticated in `/api/config`
- Admin endpoints return API keys (Brave, Kagi, Serper, etc.) in cleartext
- S3 credentials from env, no presence validation

### Risk Summary

| Issue | Severity |
|---|---|
| Default JWT secret `t0p-s3cr3t` | Critical |
| `exec()` on user-supplied code (by design) | Critical (design) |
| Arbitrary pip install from frontmatter | Critical (design) |
| `WEBUI_AUTH=False` hardcoded admin | Critical (if exposed) |
| No rate limiting on auth endpoints | High |
| Wildcard CORS with credentials | High |
| `BYPASS_MODEL_ACCESS_CONTROL` env flag | High (if set) |
| No file size limit enforcement | Medium |
| No MIME type allowlist | Medium |
| No CSRF protection | Medium |
| Google Drive API key leaked unauthenticated | Medium-High |
| Security headers opt-in only | Medium |
| Cookie secure=false default | Medium |
| JIT eval tokens no TTL | Medium |
| Retrieval config leaked unauthenticated | Low |
