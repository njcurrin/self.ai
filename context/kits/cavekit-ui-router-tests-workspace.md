---
created: "2026-04-12"
last_edited: "2026-04-12"
---

# Cavekit: UI Router Tests — Workspace

## Scope

Functional correctness and access-control tests for user-facing workspace configuration routers: prompts, tools, functions, and models. These routers manage user-created configurations that other features consume (chat, pipelines, evaluations). This kit validates CRUD semantics, access control (public vs private, permission flags), and admin-only operations where they apply. Pairs with `cavekit-ui-security-tests.md`, which covered auth enforcement at the route level.

Source analysis: `context/refs/research-brief-ui-test-suite.md` Sections 1 (coverage gaps), 2 (plugin exec boundaries noted but out of scope here).

## Requirements

### R1: Prompts

**Description:** The prompts router must implement CRUD for user-defined prompts keyed by command, with access control separating public and private prompts.

**Acceptance Criteria:**
- [ ] Listing prompts returns prompts the caller can access (own prompts plus any marked public or shared with the caller)
- [ ] Listing prompts does not return private prompts owned by other users
- [ ] Creating a prompt with a unique command persists it and returns the created record
- [ ] Creating a prompt with a command that already exists for the caller returns an error status
- [ ] Reading a prompt by command as the owner returns the prompt contents
- [ ] Reading a public prompt by command as a non-owner succeeds
- [ ] Reading a private prompt by command as a non-owner returns a not-found or forbidden status
- [ ] Updating a prompt's title, content, or access scope persists the change and is reflected on subsequent reads
- [ ] Deleting an owned prompt removes it from subsequent list and read results
- [ ] Deleting a prompt owned by a different user does not remove the record

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures)

### R2: Tools

**Description:** The tools router must implement CRUD for user-created tools including valve (configuration) management and access control. Tool code execution safety is explicitly out of scope (deferred to a plugin-sandbox kit).

**Acceptance Criteria:**
- [ ] Listing tools returns tools the caller can access per the router's access rules
- [ ] Creating a tool with a valid content payload persists the tool and returns the created record
- [ ] Reading a tool by identifier as an accessor returns its metadata and content
- [ ] Reading a tool by a non-existent identifier returns a not-found status
- [ ] Updating a tool's metadata (name, description, access control) persists the change
- [ ] Updating a tool's content payload persists the new content and is reflected on subsequent reads
- [ ] Deleting an owned tool removes it from subsequent list and read results
- [ ] Writing values to a tool's valves (configuration variables) persists the values and is reflected on subsequent reads
- [ ] Reading a tool's valves returns the previously written values for the caller
- [ ] A tool's access control settings determine which non-owner callers can list or read the tool

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures)

### R3: Functions

**Description:** The functions router must implement admin-restricted create and delete, list, active toggle, and valve configuration, distinguishing global vs user-scoped functions.

**Acceptance Criteria:**
- [ ] Listing functions returns functions visible to the caller (global functions plus the caller's own)
- [ ] Creating a function as an admin persists the function and returns the created record
- [ ] Creating a function as a non-admin returns a forbidden status
- [ ] Reading a function by identifier returns its metadata and content when visible to the caller
- [ ] Updating a function's metadata persists the change when performed by a caller with permission
- [ ] Toggling a function's active flag persists the new state and is reflected on subsequent reads
- [ ] Writing values to a function's valves persists the values
- [ ] Reading a function's valves returns the previously written values for the caller
- [ ] Deleting a function as an admin removes it from subsequent list and read results
- [ ] Deleting a function as a non-admin returns a forbidden status and does not remove the record

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures)

### R4: Models

**Description:** The models router must implement CRUD for user-defined model configurations (custom models layered on upstream base models) including parameter overrides, system prompts, access control, and reset-to-default behavior.

**Acceptance Criteria:**
- [ ] Listing models returns models the caller can access per the router's access rules
- [ ] Creating a custom model configuration persists it and returns the created record
- [ ] Reading a model by identifier as an accessor returns its metadata and configuration
- [ ] Reading a model by a non-existent identifier returns a not-found status
- [ ] Updating model parameters (temperature, top-p, or equivalent) persists the change
- [ ] Updating a model's system prompt persists the change and is reflected on subsequent reads
- [ ] Updating a model's access control settings determines which non-owner callers can list or read it
- [ ] Resetting a custom model to its upstream default clears overridden parameters and system prompt
- [ ] Deleting an owned custom model removes it from subsequent list and read results
- [ ] Deleting a model owned by a different user does not remove the record (subject to admin override if applicable)

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures)

## Out of Scope

- Authentication enforcement (covered by `cavekit-ui-security-tests.md` R1)
- Authorization matrix across roles (covered by `cavekit-ui-security-tests.md` R2)
- Execution of tool or function code bodies — the `exec()`-based plugin sandbox is a separate major architectural concern, explicitly deferred
- Arbitrary pip install from tool frontmatter (same sandbox concern, deferred)
- End-to-end browser flows
- Performance or load testing
- Rendering of prompt/model metadata in UI components

## Cross-References

- See also: `cavekit-ui-test-infrastructure.md` — provides fixtures and factories
- See also: `cavekit-ui-security-tests.md` — covers auth and input-validation concerns
- See also: `cavekit-ui-router-tests-overview.md` — master index
- Source: `context/refs/research-brief-ui-test-suite.md` — Section 1 (coverage gaps), Section 2 (plugin exec scope boundary)

## Changelog
