---
created: "2026-04-12"
last_edited: "2026-04-12"
---


# Cavekit: UI Router Tests — Overview

## Scope

Master index for the five router-test domain kits that extend coverage of the self.UI FastAPI backend from auth/isolation fundamentals (already covered by `cavekit-ui-security-tests.md`) into functional correctness across all 32 routers. This overview maps domains, dependencies, and cross-references between the router-test kits and the existing test infrastructure and security kits.

Source analysis: `context/refs/research-brief-ui-test-suite.md` Sections 1 (coverage gaps — 0 of 32 routers have working HTTP-layer tests), 3 (architecture), 5 (best practices).

## Domain Index

| Kit | Scope | Requirements |
|---|---|---|
| `cavekit-ui-router-tests-core-data.md` | User-owned data CRUD: chats, channels, folders, files, knowledge, memories | R1–R6 |
| `cavekit-ui-router-tests-workspace.md` | User-created configuration CRUD: prompts, tools, functions, models | R1–R4 |
| `cavekit-ui-router-tests-admin.md` | Admin-only surface: groups, configs, benchmarks, windows, queue | R1–R5 |
| `cavekit-ui-router-tests-jobs.md` | Job lifecycle: training (courses + jobs), evaluations, tasks | R1–R4 |
| `cavekit-ui-job-state-machines.md` | Shared state machine for GPU-queued jobs: vocabulary, transitions, idempotency, upstream-sync conflict resolution, per-type lifecycles, queue promotion ordering | R1–R7 |
| `cavekit-ui-router-tests-proxies.md` | External service passthrough: Ollama, OpenAI, Llamolotl, Curator, audio, images, retrieval, lm-eval, bigcode-eval | R1–R8 |

## Dependency Graph

```
cavekit-ui-test-infrastructure.md
   |
   +---> cavekit-ui-router-tests-core-data.md
   +---> cavekit-ui-router-tests-workspace.md
   +---> cavekit-ui-router-tests-admin.md
   +---> cavekit-ui-router-tests-jobs.md
   +---> cavekit-ui-router-tests-proxies.md
   +---> cavekit-ui-job-state-machines.md
             |
             +--- relates to: cavekit-ui-router-tests-jobs.md (tightens state-machine portion of R2/R3/R4)
             +--- relates to: cavekit-ui-router-tests-admin.md (queue endpoint order from R7)
             +--- relates to: cavekit-ui-router-tests-proxies.md (Llamolotl + harness HTTP contracts)
             +--- relates to: cavekit-curator-pipeline-integration.md (pipeline downstream dataset write contract)
```

The five router-test kits depend exclusively on `cavekit-ui-test-infrastructure.md` (fixtures, factories, mocks) and do not depend on each other — they are fully parallelizable across multiple contributors or agent threads. `cavekit-ui-job-state-machines.md` additionally cross-references the jobs, admin, proxies, and curator-pipeline-integration kits to pin the shared state contract that spans them.

## Cross-Reference Map (to Existing Kits)

| Concern | Kit that owns it |
|---|---|
| Authentication enforcement (auth dependency present on every non-public route) | `cavekit-ui-security-tests.md` R1 |
| Authorization matrix (anonymous/user/admin against every endpoint) | `cavekit-ui-security-tests.md` R2 |
| Horizontal isolation fundamentals (user A cannot access user B data) | `cavekit-ui-security-tests.md` R2 |
| JWT forgery, tamper, expiry, alg-none | `cavekit-ui-security-tests.md` R3 |
| File upload size/MIME/path-traversal safety | `cavekit-ui-security-tests.md` R4 |
| Input validation on raw-dict endpoints | `cavekit-ui-security-tests.md` R5 |
| Role escalation prevention | `cavekit-ui-security-tests.md` R6 |
| Configuration security defaults | `cavekit-ui-security-tests.md` R7 |
| Sensitive data exposure | `cavekit-ui-security-tests.md` R8 |
| Pytest config, markers, tiers | `cavekit-ui-test-infrastructure.md` R1 |
| Truncation-based fixtures, dual-session safety | `cavekit-ui-test-infrastructure.md` R2 |
| Model factories | `cavekit-ui-test-infrastructure.md` R3 |
| External service HTTP-level mocks | `cavekit-ui-test-infrastructure.md` R4 |
| Startup task isolation | `cavekit-ui-test-infrastructure.md` R7 |

## Coverage Relationship to `cavekit-ui-security-tests.md`

The security kit establishes that every route is auth-gated, admin-only routes reject non-admins, and one user's data is not reachable by another. The router-test kits in this overview pick up from there and validate **what each endpoint does when called correctly by an authorized caller**: payloads round-trip, list semantics are correct, not-found is returned where expected, state machines transition as documented, proxies forward and preserve responses faithfully, and SSE streams are well-formed.

In short: the security kit tests the gate; these kits test the room behind the gate.

## Out of Scope (Overview Level)

- End-to-end browser flows (Cypress/Playwright)
- Performance, load, and stress testing
- Real external service behavior (Ollama, OpenAI, Llamolotl, Curator, eval harnesses — all mocked)
- Real GPU execution, model training outcomes, or eval scores
- Plugin exec() sandboxing (deferred architectural rework)
- Schemathesis / OpenAPI fuzz testing (separate kit)

## Cross-References

- `cavekit-ui-test-infrastructure.md` — structural enabler for every kit in this domain
- `cavekit-ui-security-tests.md` — prerequisite coverage that these kits extend
- `cavekit-ui-router-tests-core-data.md`
- `cavekit-ui-router-tests-workspace.md`
- `cavekit-ui-router-tests-admin.md`
- `cavekit-ui-router-tests-jobs.md`
- `cavekit-ui-job-state-machines.md`
- `cavekit-ui-router-tests-proxies.md`
- `cavekit-curator-pipeline-integration.md` — cross-referenced by `cavekit-ui-job-state-machines.md` R6 for the pipeline downstream dataset write contract
- Source: `context/refs/research-brief-ui-test-suite.md`

## Requirements (Cross-Cutting)

### R1: Done criteria for router-test tasks

**Description:** A router-test task may be marked DONE only when every acceptance criterion in the referenced cavekit requirement has at least one test with strict assertions that prove the contract. "File exists and imports" is not DONE.

**Acceptance Criteria:**
- [ ] The impl tracking file lists each AC per task and which test(s) cover it
- [ ] No test covering a stated AC asserts `status_code in (<success>, <failure>)` simultaneously (e.g. `(200, 401)` or `(200, 400)`)
- [ ] No test covering a "rejects" / "forbidden" / "not-found" AC accepts 200 as a pass
- [ ] Tests asserting contract-level not-found pin one status code (the one the router actually returns), not a union
- [ ] A task marked DONE with unimplemented AC is a build bug that fails `/ck:check`

**Dependencies:** None
**Source:** Finding F-002 from `/ck:check` on 2026-04-12.

## Changelog
- 2026-04-12: Added R1 (Done criteria for router-test tasks) — discovered during `/ck:check` (findings F-002, F-003, F-004, F-005, F-009, F-010).
- 2026-04-12: Added `cavekit-ui-job-state-machines.md` to the Domain Index; extended Dependency Graph and Cross-References to map its edges to jobs, admin (queue), proxies, and curator-pipeline-integration kits.
