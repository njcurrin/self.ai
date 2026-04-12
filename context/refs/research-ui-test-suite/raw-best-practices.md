## Agent: best-practices — Findings

### Q1: Testing exec()/Plugin Systems Safely

- **Test the enforcement boundary, not the code inside it.** Write fixture plugins that attempt escapes (os.system, subprocess, open('/etc/passwd'), __import__), assert the block.
- **RestrictedPython** — compile-time AST transform blocking dangerous builtins. Test: `compile_restricted(source)` → assert CompileError for dangerous code.
- **pytest-subprocess** — fake process registry, assert exact command lines match safe allowlist without running them.
- **Bandit/Semgrep as test gate** — SAST that fails test suite if plugin source contains exec/eval/import bypasses.
- **Don't test CPython itself** — interpreter escapes are CVEs, not your test responsibility.
- **Confidence: High**

### Q2: Admin-as-Root Trust Model Testing

- **Test vertical escalation** (non-admin → admin endpoints): MUST test
- **Test horizontal escalation** (user A → user B's data): MUST test
- **Don't test admin doing admin things** — that's the feature, not a bug

**Authorization matrix testing:**
```python
@pytest.mark.parametrize("role,endpoint,expected", [
    ("anonymous",  "GET /api/admin/users",    403),
    ("user",       "GET /api/admin/users",    403),
    ("admin",      "GET /api/admin/users",    200),
])
```

**Route coverage audit test:** Read router table, assert every route has auth dependency (except explicit allowlist).

**Role escalation path test:** Assert user can't upgrade own role via ANY endpoint (profile update, settings, webhooks).
- **Confidence: High**

### Q3: Test Tiers for 5 External Dependencies

| Tier | Dependencies | When | Speed |
|------|-------------|------|-------|
| T0 Unit | None (all mocked) | Every push | <30s |
| T1 Integration | DB only (testcontainers) | Every PR | <3 min |
| T2 Contract | Real services in Docker | Merge to main | <10 min |
| T3 E2E | Full stack | Nightly/release | <30 min |

- **respx** for HTTP dependency mocking (T0/T1)
- **testcontainers-python** for real Postgres (T1+)
- **schemathesis** for contract validation of external APIs (T2)
- GPU/training server: test API contract only, not computation
- **Confidence: High**

### Q4: JWT Authentication Testing

**Four required test categories (OWASP):**
1. **Token creation** — correct claims, algorithm, bounded exp
2. **Token validation** — tampered signature → 401, expired → 401, wrong secret → 401
3. **Algorithm confusion** — `alg: none` rejected, algorithm mismatch rejected
4. **Role claims** — injected `role: admin` with user signature rejected

**Default secret test (red test):**
```python
def test_jwt_forged_with_known_default_secret_rejected(client):
    forged = jwt.encode({"sub": "admin", "role": "admin"}, "t0p-s3cr3t", algorithm="HS256")
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401  # Will FAIL until fixed
```

**Token expiry:** Use `time-machine` (preferred over freezegun for asyncio compat).

**Role escalation paths:** Parametrize across all endpoints that accept user data with `role` field.
- **Confidence: High**

### Q5: File Upload Security Testing

**Four axes:**
1. **Size limits** — 413 at boundary (limit-1, limit, limit+1), multipart bombs
2. **MIME/content-type** — .php renamed to .jpg, correct extension wrong magic bytes, `python-magic`
3. **Path traversal** — `../../../etc/passwd`, URL-encoded `%2F`, null-byte `file.jpg\x00.php`
4. **Content scanning** — zip bombs, billion-laughs XML, corrupt PDFs → 400 not crash

**Red test for missing size limit:**
```python
async def test_oversized_upload_rejected(client, oversized_file):
    resp = await client.post("/api/files/upload", files={"file": ("big.bin", f, ...)}, ...)
    assert resp.status_code == 413  # FAILS until limit implemented
```
- **Confidence: High**

### Q6: SSE/Streaming Endpoint Testing

**httpx async streaming:**
```python
async with async_client.stream("POST", "/api/chat/stream", json={...}) as resp:
    async for line in resp.aiter_lines():
        if line.startswith("data: "): chunks.append(json.loads(line[6:]))
```

**Test upstream error mid-stream:** Mock Ollama to fail mid-response with respx, assert server sends error event cleanly (not crash).

**anyio backend fixture** — must specify explicitly to avoid event loop mismatch:
```python
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
```

**Conflict noted:** pytest-asyncio vs pytest-anyio can coexist but cause intermittent event loop teardown errors if mixed. Choose one project-wide.
- **Confidence: High**

### Cross-cutting
- **schemathesis** for contract fuzz testing all external APIs
- **factory_boy 3.3** supports async SQLAlchemy sessions
- Choose pytest-anyio OR pytest-asyncio, not both
