---
created: "2026-04-12"
last_edited: "2026-04-12"
---

# Cavekit: UI Router Tests — Admin

## Scope

Functional correctness tests for admin-only routers: groups, configs, benchmarks, job windows, and queue. Validates configuration persistence, group membership semantics, window/slot state transitions, and queue ordering/promotion operations. GPU job dispatch itself is tested in `cavekit-ui-router-tests-jobs.md`; this kit covers the admin control surface that feeds the queue.

Source analysis: `context/refs/research-brief-ui-test-suite.md` Sections 1 (coverage gaps on 32 routers), 3 (no global auth middleware — admin gate is per-route).

## Requirements

### R1: Groups

**Description:** The groups router must implement group CRUD, permission configuration, member management, and user-membership queries.

**Acceptance Criteria:**
- [ ] Listing groups returns all groups (admin scope)
- [ ] Creating a group with a valid payload persists it and returns the created record with a server-assigned identifier
- [ ] Reading a group by identifier returns its name, description, permissions, and members
- [ ] Reading a group by a non-existent identifier returns a not-found status
- [ ] Updating a group's name and description persists the change
- [ ] Updating a group's permissions persists the change and is reflected on subsequent reads
- [ ] Adding a user to a group makes the user appear in the group's member list
- [ ] Removing a user from a group makes the user no longer appear in the group's member list
- [ ] Querying the groups a specific user belongs to returns exactly the groups that include that user as a member
- [ ] Deleting a group removes it from subsequent list and read results

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R3 (User factory)

### R2: Configs

**Description:** The configs router must implement get/set of application configuration including banners, default models, prompt suggestions, and user permissions, plus import/export of the full configuration JSON.

**Acceptance Criteria:**
- [ ] Reading banners returns the current configured banner list (or an empty list when none configured)
- [ ] Updating banners persists the new list and is reflected on subsequent reads
- [ ] Reading the default models configuration returns the current setting
- [ ] Updating the default models configuration persists the change
- [ ] Reading prompt suggestions returns the current configured suggestions
- [ ] Updating prompt suggestions persists the change
- [ ] Reading user permissions returns the current permission configuration
- [ ] Updating user permissions persists the change
- [ ] Exporting the configuration returns a payload covering all settable keys
- [ ] Importing a previously exported configuration restores every setting to the exported value

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures)

### R3: Benchmarks

**Description:** The benchmarks router must implement listing of benchmark configurations, update of max_duration and notes, and preservation of seed data on startup.

**Acceptance Criteria:**
- [ ] Listing benchmark configurations returns all configured benchmarks
- [ ] The seeded default benchmarks are present on a fresh database
- [ ] Updating a benchmark's max_duration persists the change and is reflected on subsequent reads
- [ ] Updating a benchmark's notes persists the change
- [ ] Updating max_duration with a non-numeric or negative value returns an error status and does not modify the record
- [ ] Reading a benchmark by a non-existent identifier returns a not-found status

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures)

### R4: Job Windows

**Description:** The job windows router must implement CRUD for recurring GPU windows, slot creation/replacement inside windows, active-window lookup by time, and status transitions between upcoming, active, completed, and disabled.

**Acceptance Criteria:**
- [ ] Listing windows returns all configured windows
- [ ] Creating a window with a valid recurrence specification persists it and returns the created record
- [ ] Creating a window with an invalid recurrence or time range returns an error status
- [ ] Reading a window by identifier returns its schedule, slots, and status
- [ ] Updating a window's recurrence, duration, or metadata persists the change
- [ ] Replacing the slots of a window atomically swaps the slot set without leaving a partial state
- [ ] Looking up the active window for a given timestamp returns a window whose schedule covers that timestamp, or null when none does
- [ ] Disabling a window transitions its status to disabled and removes it from active-window lookups
- [ ] Enabling a previously disabled window transitions it back to upcoming or active per its schedule
- [ ] Deleting a window removes it from subsequent list and read results

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R3 (JobWindow factory)

### R5: Queue

**Description:** The queue router must implement listing of queued jobs across all job types, priority tier promotion (including run-now), and correct queue ordering by priority tier and scheduled time.

**Acceptance Criteria:**
- [ ] Listing the queue returns jobs in pending, queued, and running states across all job types (training, eval, curator)
- [ ] Queue results are ordered primarily by priority tier (run_now, high, normal, low) and secondarily by scheduled time within the same tier
- [ ] Promoting a job to run_now moves it ahead of all other non-run_now jobs in the queue
- [ ] Promoting a job to high priority moves it ahead of normal and low priority jobs
- [ ] Demoting or re-prioritizing a job is reflected in queue ordering on the next read
- [ ] Listing the queue for a user returns only the caller's jobs when called with a user-scoped filter, and all jobs when called with an admin-scoped filter
- [ ] Each queue entry includes the job type, identifier, priority tier, state, and scheduled time

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R3 (TrainingJob, EvalJob, CuratorJob factories)

## Out of Scope

- Authentication and admin-role enforcement (covered by `cavekit-ui-security-tests.md` R1, R2)
- Actual dispatch of GPU jobs to Llamolotl or eval harnesses (covered by `cavekit-ui-router-tests-jobs.md` and integration-level tests)
- Real GPU execution or model outcomes
- End-to-end browser flows
- UI rendering of windows, queues, or benchmark dashboards

## Cross-References

- See also: `cavekit-ui-test-infrastructure.md` — provides fixtures and factories
- See also: `cavekit-ui-security-tests.md` — covers admin-role enforcement
- See also: `cavekit-ui-router-tests-jobs.md` — covers job lifecycle that consumes windows and queue
- See also: `cavekit-ui-router-tests-overview.md` — master index
- Source: `context/refs/research-brief-ui-test-suite.md` — Section 1 (coverage gaps), Section 3 (architecture)

## Changelog
