---
created: "2026-04-11"
last_edited: "2026-04-11"
---

# Cavekit: UI Security Hardening

## Scope

Tier 2 configuration hardening for self.UI. These are moderate-effort changes to default security posture: blocking known-insecure defaults, adding defense-in-depth headers, tightening CORS and cookie policy, and removing dead middleware. No requirement depends on another kit. All changes improve the security baseline independent of test coverage.

Source analysis: `context/refs/research-brief-ui-test-suite.md` Section 2 (Security Findings).

## Requirements

### R1: Block Default JWT Secret on Startup

**Description:** The application defaults to a well-known JWT secret (`t0p-s3cr3t`, publicly visible in the Open-WebUI source). The current guard only blocks empty strings. When authentication is enabled, the application must also block the well-known default and fail loudly.

**Acceptance Criteria:**
- [ ] Application startup fails with a clear error when the JWT secret matches the well-known default and authentication is enabled
- [ ] The error message identifies the problem (insecure default secret) and the remediation (set a unique secret)
- [ ] Application startup succeeds when a non-default, non-empty secret is configured
- [ ] Application startup succeeds with the default secret when authentication is explicitly disabled
- [ ] The behavior is testable: a test can verify the startup failure by configuring the known-default secret with auth enabled

**Dependencies:** None

### R2: Set Default Security Headers

**Description:** The security headers middleware only sets headers when environment variables are explicitly configured. Sensible defaults must be applied unconditionally, while still allowing environment variable overrides.

**Acceptance Criteria:**
- [ ] Responses include `X-Content-Type-Options: nosniff` by default (no configuration required)
- [ ] Responses include `X-Frame-Options: DENY` by default
- [ ] Responses include `Referrer-Policy: strict-origin-when-cross-origin` by default
- [ ] Each default header can be overridden via its corresponding environment variable
- [ ] Explicitly configured headers replace (not duplicate) the defaults
- [ ] Static file responses and API responses both include the default headers

**Dependencies:** None

### R3: Fix CORS Default

**Description:** The CORS configuration defaults to wildcard origin (`*`) with credentials allowed. This combination is insecure. The default must be tightened, and an explicit wildcard must produce a warning.

**Acceptance Criteria:**
- [ ] The default CORS origin is not wildcard (`*`) when credentials are allowed
- [ ] When wildcard origin is explicitly configured via environment variable, a warning is logged at startup
- [ ] The warning message identifies the security risk (wildcard + credentials)
- [ ] CORS behavior is correct for non-wildcard configured origins (preflight and actual requests succeed for allowed origins, fail for others)
- [ ] Existing deployments that explicitly set a non-wildcard origin are unaffected

**Dependencies:** None

### R4: Secure Session Cookie by Default

**Description:** The session cookie secure flag defaults to false. It must default to true in production (non-debug) mode so cookies are only sent over HTTPS. An explicit environment variable override must remain available for HTTP-only local development.

**Acceptance Criteria:**
- [ ] The session cookie secure flag defaults to `true` when the application is not in debug mode
- [ ] The session cookie secure flag defaults to `false` when the application is in debug mode
- [ ] An explicit environment variable can override the secure flag to `false` regardless of mode
- [ ] An explicit environment variable can override the secure flag to `true` regardless of mode
- [ ] The SameSite attribute on the session cookie is set to `Lax` or `Strict` (not `None` without `Secure`)

**Dependencies:** None

### R5: Add MIME Type Validation to File Uploads

**Description:** The upload endpoint accepts any file type without validation. A configurable allowlist of permitted MIME types must be enforced server-side, with a sensible default covering common document, image, audio, and data formats.

**Acceptance Criteria:**
- [ ] The upload endpoint rejects files with MIME types not in the allowlist, returning HTTP 415 status
- [ ] The default allowlist includes at minimum: text/plain, text/csv, application/json, application/pdf, image/png, image/jpeg, audio/mpeg, audio/wav
- [ ] The allowlist is configurable via environment variable or application configuration
- [ ] The MIME type check uses the file content (magic bytes), not solely the declared Content-Type header
- [ ] Files matching the allowlist continue to upload successfully
- [ ] The error response includes the rejected MIME type and a reference to the allowlist

**Dependencies:** None

### R6: Remove Dead Middleware

**Description:** The `commit_session_after_request` middleware commits a scoped session that no model code uses. It is dead code that adds confusion and potential for unintended side effects during debugging. It must be removed.

**Acceptance Criteria:**
- [ ] The `commit_session_after_request` middleware function no longer exists in the codebase
- [ ] The middleware is no longer registered in the application startup
- [ ] No remaining code references the removed middleware function
- [ ] Application request handling is otherwise unchanged (existing endpoints return the same responses)

**Dependencies:** None

## Out of Scope

- Rate limiting implementation (documented as a finding, deferred to a dedicated kit)
- CSRF token generation and validation (requires frontend coordination, deferred)
- Plugin sandboxing (major architectural rework, tracked separately)
- JWT token expiry or refresh mechanism changes
- Authentication middleware refactoring
- Surgical fixes already covered in `cavekit-ui-security-quick-fixes.md`

## Cross-References

- See also: `cavekit-ui-security-quick-fixes.md` -- Tier 1 surgical fixes that complement these hardening changes
- See also: `cavekit-ui-security-tests.md` -- R7 (Configuration Security) validates R1, R2, R3, R4 from this kit
- See also: `cavekit-ui-test-infrastructure.md` -- Test fixtures needed to validate these changes
- See also: `cavekit-ui-security-overview.md` -- master index
- Source: `context/refs/research-brief-ui-test-suite.md` -- Section 2 (Security Findings, items 1, 5, 6) and Section 3 (Architecture)

## Changelog
