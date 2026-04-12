---
created: "2026-04-11"
last_edited: "2026-04-11"
---

# Cavekit: UI Security Overview

## Purpose

Master index for the self.UI security and testing kits. These kits specify surgical security fixes, configuration hardening, test infrastructure, and a security test suite for the SvelteKit 2 + FastAPI application. All findings originate from the research brief at `context/refs/research-brief-ui-test-suite.md`.

## Domain Index

| Kit | Domain | File | Requirements | Acceptance Criteria |
|-----|--------|------|:------------:|:-------------------:|
| Security Quick Fixes | Tier 1 surgical vulnerability removal | `cavekit-ui-security-quick-fixes.md` | R1-R7 | 25 |
| Security Hardening | Tier 2 configuration and default security posture | `cavekit-ui-security-hardening.md` | R1-R6 | 31 |
| Test Infrastructure | pytest config, fixtures, factories, mocks, CI pipeline | `cavekit-ui-test-infrastructure.md` | R1-R7 | 48 |
| Security Tests | Auth audit, authorization matrix, JWT, uploads, input validation | `cavekit-ui-security-tests.md` | R1-R8 | 48 |

**Totals:** 4 domains, 28 requirements, 152 acceptance criteria

## Dependency Graph

```
cavekit-ui-security-quick-fixes          (no deps -- implement immediately)
    |
    |   cavekit-ui-security-hardening    (no deps -- implement in parallel)
    |       |
    |       |   cavekit-ui-test-infrastructure   (no deps -- implement in parallel)
    |       |       |
    +-------+-------+
            |
            v
    cavekit-ui-security-tests
        (depends on: test-infrastructure for fixtures/markers/CI)
        (validates: quick-fixes and hardening changes)
```

**Build order:**

1. **Parallel tier:** Security Quick Fixes, Security Hardening, and Test Infrastructure have no dependencies on each other. All three can be implemented simultaneously.
2. **Sequential tier:** Security Tests depends on Test Infrastructure for fixtures and markers. Tests should be written to pass green after Quick Fixes and Hardening are applied.

There are no circular dependencies between kits.

## Cross-Reference Map

### Test Infrastructure provides to Security Tests:

| Infra Requirement | Consumed By |
|-------------------|-------------|
| R1 (Pytest Configuration) | Security Tests: all requirements (markers, test discovery) |
| R2 (Backend Test Fixtures) | Security Tests: R1-R8 (test_app, authenticated_user, authenticated_admin) |
| R3 (Model Factories) | Security Tests: R2 (user factories for role testing), R6 (escalation tests) |
| R4 (External Service Mocking) | Security Tests: R2 (endpoints that call external services) |
| R7 (Startup Task Isolation) | Security Tests: all requirements (prevents background task interference) |

### Security Fixes validated by Security Tests:

| Fix Kit / Requirement | Validated By |
|-----------------------|-------------|
| Quick Fixes R1 (debug endpoint removed) | Security Tests R1 (route audit -- endpoint should not appear) |
| Quick Fixes R5 (file size limit) | Security Tests R4 (upload size boundary test) |
| Quick Fixes R6 (Google Drive behind auth) | Security Tests R8 (sensitive data exposure) |
| Hardening R1 (JWT secret blocking) | Security Tests R3 (default secret rejection), R7 (config security) |
| Hardening R2 (security headers) | Security Tests R7 (header presence validation) |
| Hardening R3 (CORS default) | Security Tests R7 (CORS policy validation) |
| Hardening R4 (cookie secure flag) | Security Tests R7 (cookie flag validation) |
| Hardening R5 (MIME validation) | Security Tests R4 (MIME mismatch rejection) |

## Known Security Findings Not Addressed

The following findings from the research brief are explicitly deferred and not covered by any kit in this set:

| # | Finding | Severity | Reason Deferred |
|---|---------|----------|-----------------|
| 1 | `exec()` on user-supplied plugin code | CRITICAL | Major architectural rework; tracked as plugin sandbox project |
| 2 | Arbitrary `pip install` from tool frontmatter | CRITICAL | Same scope as plugin sandbox |
| 3 | `WEBUI_AUTH=False` creates hardcoded admin | CRITICAL | By-design behavior for local-only dev; warning sufficient |
| 4 | No rate limiting on any endpoint | HIGH | Requires rate limiting infrastructure; separate kit |
| 5 | `BYPASS_MODEL_ACCESS_CONTROL` env flag | HIGH | Opt-in admin flag; document risk, do not remove |
| 6 | No CSRF protection | MEDIUM | Requires frontend+backend coordination; separate effort |
| 7 | JIT eval tokens have no TTL | MEDIUM | Token lifecycle redesign; separate effort |
| 8 | 19+ endpoints accept raw dict | MEDIUM | Pydantic migration is a large refactor; tests detect issues first |

## Implementation Notes

- **Parallel workstreams:** Quick Fixes and Hardening are pure code changes. Test Infrastructure is pure test scaffolding. All three can proceed simultaneously with different implementers.
- **Validation order:** After all three parallel kits are implemented, the Security Tests kit should be implemented last. Tests are written to pass green, not as red tests that drive the fixes.
- **Frontend vs backend:** Quick Fixes R2-R4 touch Svelte files (tab indentation -- use Python-based edits per CLAUDE.md). All other requirements are backend-only.
- **Existing tests:** 52 passing model tests and 16 retrieval tests exist but are not in CI. Test Infrastructure R6 activates them. Security Tests are additive, not replacing existing tests.
- **Container context:** Backend tests run in the host Python environment (FastAPI app). Frontend tests run via Docker (Node.js not installed on host). CI must account for both execution contexts.
