---
created: "2026-04-12"
last_edited: "2026-04-12"
---

# Cavekit: UI Router Tests — Proxies

## Scope

Proxy and passthrough correctness tests for routers that forward requests to external services: Ollama, OpenAI, Llamolotl, Curator, audio (STT/TTS), images, retrieval (RAG and web crawl), lm-eval, and bigcode-eval. Validates request forwarding (body, headers, query), response passthrough (status codes, headers, body), streaming chunk shape, and error preservation. External services are mocked at the HTTP transport level — no real network traffic leaves the test process.

Source analysis: `context/refs/research-brief-ui-test-suite.md` Sections 3 (URL namespace split, proxy routers), 4 (respx at transport level), 5 (mock LLM backends at HTTP level, test SSE structure not token content).

## Requirements

### R1: Ollama Proxy

**Description:** The Ollama router must forward model listing, generation, chat completions (including streaming), and model management operations (pull/push/copy/delete) to the configured Ollama backend and pass responses back faithfully.

**Acceptance Criteria:**
- [ ] A request to list models forwards to the Ollama backend and returns the backend's model list unchanged in shape
- [ ] A non-streaming chat or generate request forwards the request body to the Ollama backend and returns the backend's response body
- [ ] A streaming chat or generate request produces a chunked response whose chunks match the shape emitted by the Ollama mock
- [ ] Model management operations (pull, push, copy, delete) forward their parameters to the backend and return the backend's response
- [ ] An upstream 4xx response from the Ollama mock produces the same 4xx status to the caller
- [ ] An upstream 5xx response from the Ollama mock produces a 5xx status to the caller without leaking stack traces
- [ ] The test makes zero real network requests (verified by the mock asserting no unmatched requests)

**Dependencies:** `cavekit-ui-test-infrastructure.md` R4 (Ollama mock)

### R2: OpenAI Proxy

**Description:** The OpenAI router must forward chat completions (including streaming) and model listing to the configured OpenAI-compatible backend and pass responses back faithfully.

**Acceptance Criteria:**
- [ ] A non-streaming chat completions request forwards the request body and returns the backend's response body
- [ ] A streaming chat completions request produces a server-sent-events response whose event chunks match the shape emitted by the OpenAI mock
- [ ] A model listing request forwards to the backend and returns the backend's model list
- [ ] An upstream 4xx response produces the same 4xx status to the caller
- [ ] An upstream 5xx response produces a 5xx status to the caller without leaking stack traces
- [ ] The test makes zero real network requests

**Dependencies:** `cavekit-ui-test-infrastructure.md` R4 (OpenAI mock)

### R3: Llamolotl Proxy

**Description:** The Llamolotl router must forward model load/unload operations, training job status sync, and chat completions to the configured Llamolotl backend.

**Acceptance Criteria:**
- [ ] A model load request forwards to the backend and returns the backend's confirmation
- [ ] A model unload request forwards to the backend and returns the backend's confirmation
- [ ] A training job sync request forwards the job identifier and returns the backend's status payload
- [ ] A chat completions request forwards the request body and returns the backend's response
- [ ] An upstream error response (4xx or 5xx) preserves the status code to the caller
- [ ] The test makes zero real network requests

**Dependencies:** `cavekit-ui-test-infrastructure.md` R4 (Llamolotl mock)

### R4: Curator Proxy

**Description:** The Curator router must forward pipeline configuration, job submission, and stage registry queries to the configured Curator backend.

**Acceptance Criteria:**
- [ ] A pipeline configuration write forwards the configuration and returns the backend's acknowledgement
- [ ] A pipeline configuration read forwards to the backend and returns the current configuration
- [ ] A job submission forwards the job payload and returns the backend's job identifier
- [ ] A stage registry query forwards to the backend and returns the registered stage list
- [ ] An upstream error response preserves the status code to the caller
- [ ] The test makes zero real network requests

**Dependencies:** `cavekit-ui-test-infrastructure.md` R4 (Curator mock)

### R5: Audio

**Description:** The audio router must forward speech-to-text (transcribe) and text-to-speech (synthesize) requests to the configured audio backend and expose configuration get/set.

**Acceptance Criteria:**
- [ ] A transcribe request forwards the audio payload to the backend and returns the backend's transcript response
- [ ] A synthesize request forwards the text payload to the backend and returns the backend's audio bytes or URL
- [ ] Reading the audio configuration returns the current configured values
- [ ] Updating the audio configuration persists the change and is reflected on subsequent reads
- [ ] An upstream error from the audio backend preserves the status code to the caller
- [ ] The test makes zero real network requests

**Dependencies:** `cavekit-ui-test-infrastructure.md` R4 (audio backend mock)

### R6: Images

**Description:** The images router must forward image generation requests to the configured image backend and expose image-generation configuration get/set.

**Acceptance Criteria:**
- [ ] Reading the image generation configuration returns the current configured values
- [ ] Updating the image generation configuration persists the change
- [ ] An image generation request forwards the prompt and parameters to the backend and returns the backend's image response
- [ ] An upstream error from the image backend preserves the status code to the caller
- [ ] The test makes zero real network requests

**Dependencies:** `cavekit-ui-test-infrastructure.md` R4 (image backend mock)

### R7: Retrieval

**Description:** The retrieval router must forward RAG queries, web crawl configuration, and file processing requests to the configured retrieval/vector backend.

**Acceptance Criteria:**
- [ ] A RAG query forwards the query and target scope to the backend and returns the backend's retrieval results
- [ ] Reading the web crawl configuration returns the current configured values
- [ ] Updating the web crawl configuration persists the change
- [ ] A file processing request forwards the file reference to the backend and returns the backend's processing status
- [ ] An upstream error from the retrieval backend preserves the status code to the caller
- [ ] The test makes zero real network requests

**Dependencies:** `cavekit-ui-test-infrastructure.md` R4 (retrieval/vector backend mock)

### R8: Eval Proxies

**Description:** The lm-eval and bigcode-eval routers must expose configuration get/set and a connection verification endpoint that forwards a probe to the respective eval harness.

**Acceptance Criteria:**
- [ ] Reading the lm-eval configuration returns the current configured values
- [ ] Updating the lm-eval configuration persists the change
- [ ] The lm-eval connection verification endpoint probes the harness and returns a success status when the mock responds successfully
- [ ] The lm-eval connection verification endpoint returns a failure status when the mock responds with an error
- [ ] Reading the bigcode-eval configuration returns the current configured values
- [ ] Updating the bigcode-eval configuration persists the change
- [ ] The bigcode-eval connection verification endpoint behaves symmetrically to the lm-eval verification endpoint
- [ ] The test makes zero real network requests

**Dependencies:** `cavekit-ui-test-infrastructure.md` R4 (eval harness mocks)

## Out of Scope

- Authentication enforcement (covered by `cavekit-ui-security-tests.md` R1, R2)
- The behavior of the external services themselves (not under our control)
- Real network calls to any external service
- Content correctness of model generations, transcripts, images, or retrieval rankings
- Performance characteristics of proxy forwarding (latency, throughput)
- End-to-end browser flows

## Cross-References

- See also: `cavekit-ui-test-infrastructure.md` — provides the respx-based transport mocks that are the basis of every test in this kit
- See also: `cavekit-ui-security-tests.md` — covers auth and input validation
- See also: `cavekit-ui-router-tests-jobs.md` — covers job lifecycle that uses the Llamolotl and eval harness proxies
- See also: `cavekit-ui-router-tests-overview.md` — master index
- Source: `context/refs/research-brief-ui-test-suite.md` — Section 3 (URL namespace), Section 4 (respx), Section 5 (mock at HTTP level)

## Cross-Cutting Requirement

### R9: Transport mock enforcement

**Description:** Every test file in this kit must configure its respx mock with `assert_all_called=True` and `assert_all_mocked=True`. An unmatched request must abort the test — a proxy test that silently succeeds against a real upstream (or against nothing) is worse than no test.

**Acceptance Criteria:**
- [ ] Every proxy test file uses a respx fixture (from `cavekit-ui-test-infrastructure.md` R4) configured with strict assertion mode
- [ ] A test that hits an unmocked URL fails the test, does not make a real network call
- [ ] A test that registers a mock but never triggers it fails rather than silently passing
- [ ] No test in this kit asserts `status_code in (200, 5xx)` — a 5xx from an unreachable upstream is never a pass condition
- [ ] A documentation string in each test file confirms the zero-real-network contract is enforced

**Dependencies:** `cavekit-ui-test-infrastructure.md` R4
**Source:** Findings F-001, F-009, F-012, F-014 from `/ck:check` on 2026-04-12.

## Changelog
- 2026-04-12: Added R9 (Transport mock enforcement) — discovered during `/ck:check`. The original R1-R8 all include "zero real network requests" AC but no enforcement mechanism was specified; the resulting tests used status-tuple passes (`200, 500, 502, 503`) that hide unreachable-upstream failures.
