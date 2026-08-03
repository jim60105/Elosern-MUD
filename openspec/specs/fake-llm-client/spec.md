## Purpose

Defines the deterministic offline fake LLM client contract that lets generative-layer tests replay recorded responses and script failure modes without ever contacting a live endpoint.

## Requirements

### Requirement: FakeLLMClient replays fixed responses deterministically
`world/ai/fake_client.py` SHALL define `FakeLLMClient`, a drop-in replacement for `OpenAICompatClient` that never opens a network connection. It SHALL return a fixed, test-authored response for each request, keyed by a stable matcher on the request content, and SHALL resolve through the same Deferred-returning interface as the real client so guarded pipelines and consumers behave identically.

#### Scenario: A matched request returns its recorded text
- **WHEN** a request matches a configured fake mapping
- **THEN** the client returns the recorded response text through a Deferred without any socket activity

#### Scenario: An unmatched request fails deterministically
- **WHEN** a request does not match any configured mapping
- **THEN** the client errbacks with a named deterministic error identifying the missing fixture

### Requirement: Failure modes are scriptable for guardrail tests
`FakeLLMClient` SHALL support configuring transport-style failures — timeout, HTTP error status, connection error, and malformed non-JSON body — so guardrail tests can exercise the degrade path without a live service. Each failure mode SHALL be keyed by the same stable request matcher as a normal fixture. Because an unparseable non-JSON body is a transport failure per the guardrail contract, it SHALL drive degradation, not validation retries; validation retries are exercised with fixtures that parse as JSON but fail the declared output schema.

#### Scenario: A timeout fixture drives the degrade path
- **WHEN** a test configures a request to time out and invokes a guarded call
- **THEN** the guarded pipeline returns the layer's degrade fallback, matching the transport-failure contract

#### Scenario: A malformed non-JSON fixture degrades without retrying
- **WHEN** a test configures a request to return non-JSON text and invokes a guarded call
- **THEN** the pipeline treats it as a transport failure and returns the layer's degrade fallback without appending an error message or entering the validation retry loop

#### Scenario: A schema-invalid JSON fixture drives validation retries
- **WHEN** a test configures a request to return text that parses as JSON but fails the declared output schema and invokes a guarded call
- **THEN** the pipeline treats it as a validation failure and retries within the budget before degrading

### Requirement: Generative-layer tests never contact a live endpoint
Every test under the generative layer SHALL use `FakeLLMClient` or an equivalent recorded fixture, never a real LLM endpoint, live Ollama, or a public service. The test suite SHALL be deterministic and offline-safe, with no network dependency, no API key, and no ambient service.

#### Scenario: All generative tests are deterministic and offline
- **WHEN** the generative test suite runs with no LLM service available
- **THEN** every test passes using recorded fixtures, and none of them opens a network connection
