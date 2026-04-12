---
created: "2026-04-12"
last_edited: "2026-04-12"
---

# Cavekit: UI Router Tests — Core Data

## Scope

Functional correctness tests for user-owned data routers: chats, channels, folders, files, knowledge bases, and memories. Focuses on list/create/read/update/delete semantics, pagination, empty-state handling, not-found handling, and ownership isolation on the happy path. Complements `cavekit-ui-security-tests.md`, which already covered auth enforcement and the horizontal isolation fundamentals. This kit extends coverage into the functional contract each router promises to its caller.

Source analysis: `context/refs/research-brief-ui-test-suite.md` Sections 1 (coverage gaps on 32 routers), 3 (dual-session architecture, truncation teardown).

## Requirements

### R1: Chat CRUD

**Description:** The chat router must implement complete CRUD for user-owned chat records including import/export and clone, with correct list semantics, correct not-found handling, and correct ownership scoping.

**Acceptance Criteria:**
- [ ] Listing chats for a user with no chats returns an empty collection and a success status
- [ ] Listing chats for a user with multiple chats returns all of that user's chats and none belonging to other users
- [ ] List results can be paginated (skip/limit or equivalent) and pagination returns the expected slice without duplicates or omissions
- [ ] Creating a chat with a valid payload returns the created chat with a server-assigned identifier
- [ ] Reading a chat by its identifier as the owner returns the chat contents
- [ ] Reading a chat by a non-existent identifier returns a not-found status
- [ ] Reading a chat owned by a different user returns a not-found or forbidden status (never the other user's data)
- [ ] Updating chat metadata (title, tags, archive flag, pin flag, share flag) persists the change and is reflected on subsequent reads
- [ ] Deleting a chat as the owner removes it from subsequent list and read results
- [ ] Deleting a chat owned by a different user does not remove the record
- [ ] Importing a chat payload produces a new chat owned by the importing user
- [ ] Exporting a chat produces a payload that, when re-imported, reconstructs an equivalent chat
- [ ] Cloning a chat produces a new chat with a new identifier owned by the caller

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R3 (Chat factory)

### R2: Channel CRUD

**Description:** The channels router must implement messaging channel membership, message listing with pagination, message send/edit/delete, reactions, and thread replies, scoped correctly by channel membership.

**Acceptance Criteria:**
- [ ] Listing channels returns only channels the caller is a member of
- [ ] Creating a channel returns the created channel and includes the creator as a member
- [ ] Listing messages in a channel the caller is a member of returns messages in chronological order
- [ ] Listing messages supports pagination and returns the expected slice without duplicates or omissions
- [ ] Listing messages in a channel the caller is not a member of returns an error status (not the messages)
- [ ] Sending a message to a channel the caller is a member of persists the message and attributes it to the caller
- [ ] Editing a message the caller authored updates its contents and is reflected on subsequent reads
- [ ] Editing a message the caller did not author returns an error status and does not modify the message
- [ ] Deleting a message the caller authored removes it from subsequent list results
- [ ] Deleting a message the caller did not author returns an error status
- [ ] Adding a reaction to a message records the reaction and associates it with the caller
- [ ] Removing a reaction previously added by the caller removes only that reaction
- [ ] Replying to a message in a thread persists the reply and associates it with the parent message

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R3 (User factory)

### R3: Folder CRUD

**Description:** The folders router must implement folder CRUD with reparenting, recursive child handling on delete, and chat assignment.

**Acceptance Criteria:**
- [ ] Listing folders for a user with no folders returns an empty collection
- [ ] Listing folders returns only folders owned by the caller
- [ ] Creating a folder returns the created folder with a server-assigned identifier
- [ ] Renaming a folder persists the new name and is reflected on subsequent reads
- [ ] Moving a folder to a new parent updates its parent reference and is reflected on subsequent reads
- [ ] Moving a folder to create a cycle (folder becomes its own ancestor) returns an error status
- [ ] Deleting a folder with no children removes the folder
- [ ] Deleting a folder with children either removes the children recursively or returns an error — the behavior is deterministic and documented by the test
- [ ] Assigning a chat to a folder is reflected when listing chats in that folder
- [ ] Unassigning a chat from a folder removes it from that folder's chat list

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures)

### R4: File CRUD

**Description:** The files router must implement file listing, creation (upload happy path), read, update, content retrieval, and deletion with correct metadata and ownership scoping. Security-sensitive concerns (size limits, MIME validation, path traversal) are covered by `cavekit-ui-security-tests.md` R4; this kit covers functional correctness.

**Acceptance Criteria:**
- [ ] Listing files for a user with no files returns an empty collection
- [ ] Listing files returns only files owned by the caller
- [ ] Uploading a valid file round-trips: the response includes a server-assigned identifier, the declared filename, content type, and size
- [ ] Reading a file by identifier as the owner returns the file metadata
- [ ] Reading a file by a non-existent identifier returns a not-found status
- [ ] Reading a file owned by a different user returns a not-found or forbidden status
- [ ] Retrieving file content for an owned file returns the bytes matching what was uploaded
- [ ] Updating file data (content or metadata) persists the change and is reflected on subsequent reads
- [ ] Deleting a file as the owner removes it from subsequent list and read results
- [ ] Deleting a file owned by a different user does not remove the record

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R3 (File factory)

### R5: Knowledge Base CRUD

**Description:** The knowledge router must implement knowledge base CRUD, file membership management, reset, and query scoped to the owning user.

**Acceptance Criteria:**
- [ ] Listing knowledge bases for a user with none returns an empty collection
- [ ] Listing knowledge bases returns only bases owned by the caller
- [ ] Creating a knowledge base returns the created base with a server-assigned identifier
- [ ] Reading a knowledge base by identifier as the owner returns its metadata and file list
- [ ] Reading a knowledge base owned by a different user returns a not-found or forbidden status
- [ ] Updating the name and description of a knowledge base persists the change
- [ ] Adding an owned file to a knowledge base is reflected in the base's file list on subsequent reads
- [ ] Removing a file from a knowledge base is reflected by its absence in subsequent reads
- [ ] Resetting a knowledge base removes all files from it and leaves the base itself in place
- [ ] Deleting a knowledge base removes it from subsequent list and read results
- [ ] Querying a knowledge base returns results scoped to that base's indexed contents (with the retrieval backend mocked)

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R3 (Knowledge factory, File factory), R4 (retrieval mock)

### R6: Memory CRUD

**Description:** The memories router must implement memory CRUD, bulk delete for a user, and embedding-based query scoped to the owning user.

**Acceptance Criteria:**
- [ ] Listing memories for a user with none returns an empty collection
- [ ] Listing memories returns only memories owned by the caller
- [ ] Adding a memory returns the created record with a server-assigned identifier
- [ ] Updating a memory persists the change and is reflected on subsequent reads
- [ ] Deleting a single memory removes it from subsequent list results
- [ ] Deleting a memory owned by a different user does not remove the record
- [ ] Deleting all memories for the caller leaves no memories owned by the caller and does not affect memories owned by other users
- [ ] Querying memories by content or embedding returns only memories owned by the caller (with the embedding backend mocked)

**Dependencies:** `cavekit-ui-test-infrastructure.md` R2 (fixtures), R4 (embedding mock)

## Out of Scope

- Authentication enforcement (covered by `cavekit-ui-security-tests.md` R1)
- Authorization matrix across roles (covered by `cavekit-ui-security-tests.md` R2)
- File upload security — size limits, MIME, path traversal (covered by `cavekit-ui-security-tests.md` R4)
- Input validation on raw-dict endpoints (covered by `cavekit-ui-security-tests.md` R5)
- End-to-end browser flows
- Performance, load, or stress testing
- Actual embedding model quality or retrieval ranking correctness
- Real external service behavior (vector DB, embedding service — mocked here)

## Cross-References

- See also: `cavekit-ui-test-infrastructure.md` — provides fixtures, factories, and mocks this kit depends on
- See also: `cavekit-ui-security-tests.md` — covers the auth and input-validation concerns excluded above
- See also: `cavekit-ui-router-tests-overview.md` — master index for the router-test domain
- Source: `context/refs/research-brief-ui-test-suite.md` — Section 1 (coverage gaps), Section 3 (architecture)

## Changelog
