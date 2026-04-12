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
