---
created: "2026-04-11"
last_edited: "2026-04-11"
---

# Cavekit: UI Security Quick Fixes

## Scope

Tier 1 surgical security fixes for self.UI. Each requirement is a small, targeted change that eliminates a known vulnerability or exposure identified in the research brief (`context/refs/research-brief-ui-test-suite.md`). No requirement depends on another kit or on any other requirement in this kit. All changes are independently deployable.

## Requirements

### R1: Remove Unauthenticated Debug Endpoint

**Description:** The `GET /api/v1/memories/ef` endpoint is unauthenticated, is not called by any frontend code, and invokes the embedding function without access control. It must be removed entirely.

**Acceptance Criteria:**
- [ ] The route handler for `GET /api/v1/memories/ef` no longer exists in the codebase
- [ ] Requests to `GET /api/v1/memories/ef` return 404 or 405
- [ ] All other `/api/v1/memories/` endpoints continue to function with their existing authentication

**Dependencies:** None

### R2: Remove JWT Leak from Console

**Description:** The login page logs the full session user object (including the JWT token) to the browser console on every successful authentication. The console.log call must be removed or the token must be stripped before logging.

**Acceptance Criteria:**
- [ ] The auth page does not call `console.log` with an object containing a JWT token after login
- [ ] Login functionality is not affected (user is still authenticated and redirected correctly after login)

**Dependencies:** None

### R3: Fix DOMPurify Bypass in Markdown Rendering

**Description:** The markdown rendering components have a code path where text containing an iframe prefix falls through to raw HTML rendering without DOMPurify sanitization. All HTML output in these components must pass through DOMPurify regardless of content.

**Acceptance Criteria:**
- [ ] Markdown token text containing `<iframe` is sanitized through DOMPurify before rendering
- [ ] Markdown inline token text containing `<iframe` is sanitized through DOMPurify before rendering
- [ ] Legitimate iframe embeds that DOMPurify allows (if any are configured) still render correctly
- [ ] Non-iframe markdown content continues to render as before

**Dependencies:** None

### R4: Sanitize SVG Rendering

**Description:** The SVG pan/zoom component renders SVG content as raw HTML despite importing DOMPurify. The SVG content must be sanitized before rendering.

**Acceptance Criteria:**
- [ ] SVG content is passed through DOMPurify sanitization before being rendered as HTML
- [ ] DOMPurify is configured to permit SVG elements and attributes (not strip valid SVG)
- [ ] Valid SVG content continues to render and remain interactive (pan/zoom functionality preserved)

**Dependencies:** None

### R5: Enforce Server-Side File Size Limit

**Description:** The file upload endpoint has no server-side size check. The configured maximum file size is only enforced by the frontend. The server must reject uploads exceeding the configured limit before writing to storage.

**Acceptance Criteria:**
- [ ] The upload endpoint rejects files exceeding the configured maximum size with HTTP 413 status
- [ ] The rejection occurs before the file is written to persistent storage
- [ ] The configured maximum size value is read from the same configuration source used by the frontend
- [ ] Files at or below the size limit are accepted as before
- [ ] The error response includes a message indicating the size limit was exceeded

**Dependencies:** None

### R6: Move Google Drive Credentials Behind Auth

**Description:** The `/api/config` endpoint returns Google Drive client_id and api_key to unauthenticated callers. These values must only be returned to authenticated users.

**Acceptance Criteria:**
- [ ] Unauthenticated requests to `/api/config` do not include `google_drive.client_id` in the response
- [ ] Unauthenticated requests to `/api/config` do not include `google_drive.api_key` in the response
- [ ] Authenticated requests to `/api/config` continue to receive both values
- [ ] Frontend Google Drive functionality continues to work for logged-in users

**Dependencies:** None

### R7: Remove Dead File Type Constants

**Description:** `SUPPORTED_FILE_TYPE` and `SUPPORTED_FILE_EXTENSIONS` constants are defined but never imported anywhere in the codebase. They must either be removed or wired into client-side upload validation.

**Acceptance Criteria:**
- [ ] `SUPPORTED_FILE_TYPE` is either removed from the codebase or imported by at least one module
- [ ] `SUPPORTED_FILE_EXTENSIONS` is either removed from the codebase or imported by at least one module
- [ ] If removed: no remaining references exist in the codebase
- [ ] If wired in: the client-side upload flow uses the constants to validate file type before upload

**Dependencies:** None

## Out of Scope

- Rate limiting on any endpoint
- CSRF protection
- Plugin sandboxing (exec()-based RCE -- separate major rework)
- Test infrastructure or test cases for these fixes (see `cavekit-ui-test-infrastructure.md` and `cavekit-ui-security-tests.md`)
- Changes to authentication middleware or dependency injection patterns
- Cookie security settings (see `cavekit-ui-security-hardening.md` R4)

## Cross-References

- See also: `cavekit-ui-security-hardening.md` -- Tier 2 configuration changes that complement these surgical fixes
- See also: `cavekit-ui-security-tests.md` -- Test cases that validate these fixes are in place (R4 file uploads, R7 configuration, R8 sensitive data)
- See also: `cavekit-ui-security-overview.md` -- master index
- Source: `context/refs/research-brief-ui-test-suite.md` -- Section 2 (Security Findings)

## Changelog
