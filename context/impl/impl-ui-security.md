---
created: "2026-04-11"
last_edited: "2026-04-11"
---
# Implementation Tracking: UI Security

Build site: context/plans/build-site-ui-security.md

| Task | Status | Notes |
|------|--------|-------|
| T-200 | DONE | Removed GET /api/v1/memories/ef debug endpoint from memories.py |
| T-201 | DONE | Removed console.log(sessionUser) from auth/+page.svelte |
| T-202 | DONE | Fixed DOMPurify bypass in MarkdownTokens.svelte and MarkdownInlineTokens.svelte — iframe content now sanitized through DOMPurify with ADD_TAGS/ADD_ATTR |
| T-203 | DONE | Applied DOMPurify.sanitize with SVG profile to SVGPanZoom.svelte |
| T-204 | DONE | Added server-side file size check to files.py upload_file — reads contents, checks against FILE_MAX_SIZE, returns 413 if exceeded |
| T-205 | DONE | Moved google_drive credentials inside `if user is not None` block in /api/config |
| T-206 | DONE | Removed dead SUPPORTED_FILE_TYPE and SUPPORTED_FILE_EXTENSIONS from constants.ts |
| T-207 | DONE | Block default JWT secret t0p-s3cr3t on startup when WEBUI_AUTH=True; also set new secret in .env |
| T-208 | DONE | Added default security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, X-Permitted-Cross-Domain-Policies) |
| T-209 | DONE | Changed CORS default from wildcard to empty (same-origin); enhanced warning message |
| T-210 | DONE | Session cookie Secure flag defaults to true in non-dev mode |
| T-211 | DONE | Added MIME type validation — blocked executable prefixes + configurable allowlist, 415 on reject |
| T-212 | DONE | Removed dead commit_session_after_request middleware from main.py |
| T-213 | DONE | Added [tool.pytest.ini_options] to pyproject.toml with markers, strict mode, timeout; added test deps to requirements.txt |
| T-214 | DONE | Created vitest.config.ts with jsdom, svelte plugin, $app/* mocks; added testing-library/svelte, jest-dom, jsdom, msw to package.json; smoke test for Spinner |
| T-215 | DONE | Created tests/mocks/external_services.py with respx-based ServiceMock fixtures for Ollama, OpenAI, Llamolotl, Curator, eval harness |
| T-216 | DONE | Root conftest.py with test_app, client, db_session fixtures; app.dependency_overrides for DI |
| T-217 | DONE | DB setup with create_all + truncation-based teardown (DELETE in FK-safe order); env overrides for test isolation |
| T-218 | DONE | authenticated_user and authenticated_admin fixtures with JWT token creation; test_user and test_admin helpers |
| T-219 | DONE | Startup task isolation via autouse fixture patching all 4 fire-and-forget tasks |
| T-220 | DONE | Uncommented pytest CI job with tier0+tier1 markers, JUnit XML; added vitest CI job |
| T-221 | DONE | Model factories in tests/factories.py (User, Auth, Chat, File, Knowledge, Tool, Function, Training/Eval/Curator jobs, JobWindow) |
| T-222 | DONE | Route auth coverage audit — all routes have auth except 7 allowlisted; found /api/v1/retrieval/ leak and 5 utils endpoints lacking auth |
| T-223 | DONE | Authorization matrix vertical escalation — 7 admin endpoints tested across anonymous/user/admin roles |
| T-224 | DONE | Horizontal isolation — user A cannot read/delete/list user B's chats |
| T-225 | DONE | JWT basic attacks — tampered sig, expired, alg:none, wrong secret, malformed, missing Bearer |
| T-226 | DONE | JWT secret/role forgery — t0p-s3cr3t rejected, forged admin role rejected |
| T-227 | DONE | Upload size — 413 on oversized, accepted at/below limit. Fixed files.py to preserve HTTPException status |
| T-228 | DONE | Upload traversal/MIME — path traversal sanitized, null-byte xfailed (real finding), executable MIME blocked, allowlist works |
| T-229+T-230 | DONE | Dict endpoint validation — 10 endpoints, empty/extra/wrong-type/deep-nesting tests. 20 xfailed documenting the gap |
| T-231 | DONE | Role escalation prevention — user cannot escalate via info/settings/profile updates, admin role endpoint rejects users |
| T-232 | DONE | Config security startup — default JWT secret blocked, empty secret blocked |
| T-233 | DONE | Config security runtime — headers present, CORS not wildcard, cookie Secure in non-dev |
| T-234 | DONE | Data exposure /api/config — no google_drive creds, no sensitive keys for unauthenticated |
| T-235 | DONE | Data exposure errors — no stack traces, no auth mechanism hints in 401/403 |
| T-236 | DONE | Test isolation validation — truncation teardown verified (2 sequential tests, 2nd sees no 1st data) |
| T-237 | DONE | Full suite dry-run — 122 tests collected and run, markers functional, no collection errors |
| T-238 | DONE | CI end-to-end — fixtures work, app state has required config, external service mocks importable |
