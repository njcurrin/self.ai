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
