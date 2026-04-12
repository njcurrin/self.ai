---
created: "2026-04-11"
last_edited: "2026-04-11"
---

# Cavekit: UI Security Tests

## Scope

Security test suite for self.UI. Covers authentication enforcement, authorization matrix, JWT validation, file upload safety, input validation, role escalation prevention, configuration security, and sensitive data exposure. All tests in this kit depend on the test infrastructure provided by `cavekit-ui-test-infrastructure.md`. Tests should pass green after the fixes in `cavekit-ui-security-quick-fixes.md` and `cavekit-ui-security-hardening.md` are applied.

Source analysis: `context/refs/research-brief-ui-test-suite.md` Sections 2 (Security Findings) and 3 (Architecture).

## Requirements

### R1: Route Auth Coverage Audit

**Description:** An automated test that reads the application's router table and asserts every route has an authentication dependency, except for an explicit allowlist of public endpoints. Any new endpoint added without authentication automatically fails CI.

**Acceptance Criteria:**
- [ ] A test enumerates all registered routes from the application's router table
- [ ] The test asserts that every route not in the public allowlist has an auth dependency in its dependency chain
- [ ] The public allowlist includes exactly: `/health`, `/health/db`, `/api/version`, `/api/changelog`, `/api/config`, `/docs`, `/openapi.json`, and OAuth callback routes
- [ ] Adding a new route without an auth dependency causes the test to fail (verified by the test's design, not by actually adding a route)
- [ ] The test output identifies which specific routes are missing auth when it fails
- [ ] The test does not make HTTP requests -- it inspects the route definitions programmatically

**Dependencies:** `cavekit-ui-test-infrastructure.md` R1 (pytest config, `security` marker)

### R2: Authorization Matrix

**Description:** A parametrized test covering all routers with three caller roles (anonymous, user, admin). Validates both vertical escalation (user accessing admin endpoints) and horizontal isolation (user A accessing user B's data).

**Acceptance Criteria:**
- [ ] The test is parametrized across all routers (32+) and three roles: anonymous, user, admin
- [ ] Anonymous requests to authenticated endpoints receive 401 or 403
- [ ] User-role requests to admin-only endpoints receive 403
- [ ] Admin-role requests to admin endpoints receive 200 (or appropriate success status)
- [ ] User-role requests to user-accessible endpoints succeed (200 or appropriate success status)
- [ ] At least one horizontal isolation test exists: user A cannot read or modify user B's resources (chats, files, or memories)
- [ ] The test matrix is defined declaratively (data-driven), not as individual test functions per endpoint
- [ ] Test failures identify the specific (role, endpoint, expected_status, actual_status) tuple

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (authenticated_user, authenticated_admin fixtures)

### R3: JWT Security

**Description:** Tests validating that the JWT authentication layer correctly rejects forged, tampered, expired, and misconfigured tokens.

**Acceptance Criteria:**
- [ ] A request with a tampered JWT signature receives 401
- [ ] A request with an expired JWT receives 401
- [ ] A request with a JWT using `alg: none` receives 401
- [ ] A request with a JWT signed with a wrong/random secret receives 401
- [ ] A request with a JWT containing a forged admin role claim is rejected (role is read from the database, not the token)
- [ ] A request with a JWT signed using the well-known default secret (`t0p-s3cr3t`) is rejected when the application is configured with a different secret
- [ ] Each test case is independent and produces a clear failure message identifying the attack vector tested

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (test_app fixture), `cavekit-ui-security-hardening.md` R1 (default secret blocking)

### R4: File Upload Security

**Description:** Tests validating server-side enforcement of file upload constraints: size limits, path traversal prevention, MIME type validation, and filename injection.

**Acceptance Criteria:**
- [ ] Uploading a file exceeding the configured size limit returns HTTP 413
- [ ] Uploading a file at exactly the size limit succeeds (boundary test)
- [ ] A filename containing path traversal sequences (`../`, `..\\`) is rejected or sanitized (file is not written outside the upload directory)
- [ ] A filename containing null bytes is rejected or sanitized
- [ ] A file with mismatched MIME type (content does not match declared type) is rejected with HTTP 415
- [ ] Each test produces a clear failure message identifying the attack vector tested

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (authenticated_user fixture), `cavekit-ui-security-quick-fixes.md` R5 (size limit enforcement), `cavekit-ui-security-hardening.md` R5 (MIME validation)

### R5: Input Validation on Dict Endpoints

**Description:** Tests targeting the 19+ endpoints that accept raw `dict` input instead of typed request models. Validates graceful handling of missing fields, unexpected fields, type mismatches, and deeply nested payloads.

**Acceptance Criteria:**
- [ ] Sending a request with missing required fields returns an appropriate error (400 or 422), not a 500
- [ ] Sending a request with extra/unexpected fields does not cause a server error (returns success or ignores the extra fields)
- [ ] Sending a request with type coercion attacks (string where integer expected, array where string expected) returns an appropriate error, not a 500
- [ ] Sending a deeply nested object (100+ levels) does not cause a stack overflow or excessive processing time (returns 400 or is truncated)
- [ ] At least 10 of the 19+ dict-accepting endpoints are covered
- [ ] Each test case documents which endpoint it targets and what validation gap it exercises

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (authenticated_user fixture)

### R6: Role Escalation Prevention

**Description:** Tests verifying that a user cannot escalate their own role via any endpoint that accepts user data containing a `role` field.

**Acceptance Criteria:**
- [ ] A user-role caller submitting a profile update with `role: admin` does not become an admin
- [ ] A user-role caller submitting settings with `role: admin` does not become an admin
- [ ] The test is parametrized across all endpoints that accept a request body containing a `role` field
- [ ] After each escalation attempt, the test verifies the user's role in the database is unchanged
- [ ] The endpoint either ignores the role field or returns an error -- either outcome is acceptable as long as the role is not changed

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (authenticated_user fixture), R3 (User factory)

### R7: Configuration Security

**Description:** Tests verifying that security-relevant configuration defaults are correctly enforced: JWT secret blocking, CORS policy, security headers, and cookie flags.

**Acceptance Criteria:**
- [ ] A test verifies that application startup fails when the JWT secret is the well-known default and auth is enabled
- [ ] A test verifies that CORS does not allow wildcard origin when credentials are enabled (the default configuration)
- [ ] A test verifies that responses include `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` headers with the expected default values
- [ ] A test verifies that the session cookie has the `Secure` flag set when the application is not in debug mode
- [ ] Each test can run independently without relying on other configuration tests

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (test_app fixture), `cavekit-ui-security-hardening.md` R1-R4 (the configuration changes being validated)

### R8: Sensitive Data Exposure

**Description:** Tests verifying that unauthenticated responses and error responses do not leak secrets, internal paths, or configuration details.

**Acceptance Criteria:**
- [ ] Unauthenticated `GET /api/config` does not include API keys, JWT secrets, or database connection strings in the response body
- [ ] Unauthenticated `GET /api/config` does not include Google Drive client_id or api_key in the response body
- [ ] Error responses (triggering a 500 via malformed input) do not contain Python stack traces or internal file paths
- [ ] The response body of 401/403 errors does not include information about what auth mechanism is expected (no hints for attackers)
- [ ] Each test documents what sensitive data it checks for and where the exposure was identified

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (test_app fixture), `cavekit-ui-security-quick-fixes.md` R6 (Google Drive credentials moved behind auth)

## Out of Scope

- Rate limiting implementation or rate limiting tests (detection only -- identified as a finding, implementation deferred to a dedicated kit)
- Plugin sandbox tests (exec()-based RCE is a separate major architectural rework, tracked independently)
- Browser-level end-to-end security tests (Cypress/Playwright)
- Performance or load testing
- CSRF token validation tests (CSRF protection is not yet implemented)
- Frontend component security tests (XSS vectors in Svelte components are addressed by fixes in `cavekit-ui-security-quick-fixes.md`, not by component-level tests)
- JIT eval token TTL tests (token lifecycle is a separate concern)
- Schemathesis / OpenAPI fuzz testing (tier 2, separate kit)

## Cross-References

- See also: `cavekit-ui-test-infrastructure.md` -- provides all fixtures, factories, mocks, and configuration this kit depends on
- See also: `cavekit-ui-security-quick-fixes.md` -- Tier 1 fixes that R4, R8 tests validate
- See also: `cavekit-ui-security-hardening.md` -- Tier 2 hardening that R3, R4, R7, R8 tests validate
- See also: `cavekit-ui-security-overview.md` -- master index
- Source: `context/refs/research-brief-ui-test-suite.md` -- Section 2 (Security Findings), Section 5 (Best Practices items 4, 5)

## Changelog
