## Agent: codebase-frontend-api — Findings

### 1. API Client Structure
- No shared HTTP client/interceptor. ~30 modules each do raw `fetch()` with inline auth headers
- Newer modules (queue, training, schedule) use per-module `apiFetch`/`queueFetch` wrappers — cleaner but still no global interceptor
- **Confidence: High**

### 2. Token Storage & Auth
- JWT stored as `localStorage.token` — plain string, no expiry monitoring
- Token passed as function arg: `getModels(localStorage.token)`
- Inconsistent header case: some `authorization:`, some `Authorization:`
- **No token refresh mechanism at all**
- **Confidence: High**

### 3. Error Handling
- Dominant pattern: `error = err.detail` then `if (error) throw error`
- **Bug:** When `err.detail` is `undefined` (network error), `error` = `undefined`, falsy check passes, returns `null` silently — masks failures
- Newer modules more robust: `throw err?.detail ?? 'Request failed'`
- No global error boundary
- **Confidence: High**

### 4. API Calls Without Auth
- Several functions default `token = ''` with conditional auth header — works without auth if no token passed
- `getBackendConfig()`, `getChangelog()`, `getVersionUpdates()` — no auth at all (appropriate)
- **`getFileContentById(id)` — no token parameter, cookie-only** — potential CSRF vector
- **Confidence: High**

### 5. 401/403 Handling
- **No 401/403-specific handling anywhere in frontend**
- All non-2xx treated uniformly: `throw await res.json()`
- Only redirect to `/auth` happens at startup if `getSessionUser()` fails
- **Mid-session token expiry = broken UI, no re-auth prompt**
- **Confidence: High**

### 6. Hardcoded URLs/Tokens
- None found. All URLs from `constants.ts`, GDrive keys fetched from backend config at runtime.
- `sk-1234` in i18n files is a placeholder label only
- **Confidence: High**

### 7. Data Sanitization
- Request: `JSON.stringify(body)` with no pre-sanitization
- Response: Chat messages sanitized at rendering layer (DOMPurify), not at API layer
- LLM JSON extraction uses try/catch, returns empty on failure
- **Confidence: High**

### 8. XSS Vectors — {@html} Usage

**MEDIUM-HIGH RISK:**
- `MarkdownTokens.svelte:207-208` — `{@html token.text}` when string includes iframe prefix — **bypasses DOMPurify**. Attacker/LLM could include the legitimate prefix substring + malicious HTML.
- Same pattern: `MarkdownInlineTokens.svelte:29-30`

**MEDIUM RISK:**
- `SVGPanZoom.svelte:42` — `{@html svg}` with **no DOMPurify** despite importing it. LLM-generated SVG with script tags could execute.

**LOW-MEDIUM RISK:**
- `Placeholder.svelte:159-161`, `ChatPlaceholder.svelte:97-99` — `{@html marked.parse(sanitizeResponseContent(...))}` — uses custom entity encoding instead of DOMPurify

**LOW RISK (properly sanitized):**
- `Banner.svelte:86`, `NotificationToast.svelte:50`, `RecursiveFolder.svelte:336` — all use DOMPurify

### 9. File Uploads
- Four upload points, all FormData, none validate MIME type client-side
- `SUPPORTED_FILE_TYPE` and `SUPPORTED_FILE_EXTENSIONS` constants in `constants.ts` are **dead code — never imported**
- File type enforcement entirely server-side
- **Confidence: High**

### 10. Sensitive Data Exposure
- `console.log(sessionUser)` at `auth/+page.svelte:33` — **logs JWT token to console on every login**
- `localStorage.token` — XSS-exfiltrable
- OpenAI API keys returned to admin UI (appropriate for admin, increases risk surface)
- Google OAuth token in memory only (acceptable)
- **Confidence: High**

### Risk Summary

| Finding | Risk Level |
|---|---|
| `{@html token.text}` iframe DOMPurify bypass | Medium-High (XSS) |
| `{@html svg}` unsanitized SVG | Medium (XSS) |
| `localStorage.token` + no refresh | Medium (token exfiltration via XSS) |
| `console.log(sessionUser)` with token | Medium (disclosure) |
| No 401/403 handling, no token refresh | Medium (broken auth UX) |
| `getFileContentById` cookie-only, no CSRF | Medium (CSRF) |
| `err.detail` undefined silent failure | Medium (masked errors) |
| Dead file type constants | Low-Medium (no client validation) |
| Inconsistent auth header case | Low |
