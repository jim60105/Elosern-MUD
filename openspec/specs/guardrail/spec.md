## Purpose

Defines the guarded generative call pipeline that validates output, retries with appended errors, then degrades to a layer fallback, with pluggable semantic validators and strict separation between transport and validation failures.

## Requirements

### Requirement: Guarded generative calls validate, retry, then degrade
`world/ai/guardrail.py` SHALL provide a guarded-call pipeline with three ordered stages matching design §7.5: local jsonschema validation of the returned text against the call's declared output schema, semantic validation through pluggable validator hooks, and a bounded retry loop that appends the validation error message to the prompt and retries. When the retry budget is exhausted, the pipeline SHALL return the layer's registered degrade fallback rather than raising or returning invalid output. The retry budget SHALL be interpreted as `1 + max_retries` total calls: the initial attempt plus up to `max_retries` retries, and each retry SHALL append that round's complete validation error list while leaving the original messages unchanged.

#### Scenario: A schema-valid response is accepted on the first attempt
- **WHEN** the endpoint returns text that satisfies both the declared jsonschema and every semantic validator
- **THEN** the pipeline returns that text once and performs no retry

#### Scenario: Invalid output is retried with the errors appended
- **WHEN** the endpoint returns text that fails jsonschema or a semantic validator
- **THEN** the pipeline retries up to the `1 + max_retries` budget with that round's full validation error list appended to the prompt, and does not return the invalid text

#### Scenario: Exhausted retries degrade to the layer fallback
- **WHEN** every retry attempt returns output that still fails validation
- **THEN** the pipeline returns the layer's registered degrade fallback and the deterministic game continues unaffected

### Requirement: Semantic validators are pluggable and layer-scoped
Semantic validation SHALL be supplied as hook functions registered per layer, each receiving the parsed output and returning either an empty error list or a list of specific error messages. The pipeline SHALL run every registered semantic validator for the governing layer in a stable order and SHALL treat any non-empty error list as a validation failure. Later changes add their layer-specific rank, reward, archetype, and whitelist validators without modifying the pipeline.

#### Scenario: A registered semantic validator rejects an out-of-range value
- **WHEN** a layer registers a semantic validator and the endpoint returns output that violates it while passing jsonschema
- **THEN** the pipeline treats the output as invalid and enters the retry loop

#### Scenario: Semantic validation never mutates game state
- **WHEN** semantic validators run against output that passes or fails
- **THEN** they read registry data and the proposed output only, and the pipeline performs no persistent write, spawn, or trait/attribute mutation

### Requirement: Guardrail failures degrade without network coupling
A client-level failure (connection error, timeout, HTTP error, or an unparseable non-JSON body) SHALL route through the guardrail to the layer's degrade fallback without entering the validation retry loop. The guardrail SHALL NOT confuse a transport failure with a validation failure, and SHALL only append validation error messages on validation failures, never on transport failures.

#### Scenario: A transport failure degrades directly
- **WHEN** the endpoint is unreachable, returns a non-200 status, exceeds its timeout, or returns a body that cannot be parsed
- **THEN** the pipeline returns the layer's degrade fallback without retrying on the same broken transport and without appending an error message to any prompt

#### Scenario: Only schema-invalid text triggers validation retries
- **WHEN** the endpoint returns text that parses successfully but does not satisfy the declared output schema or a semantic validator
- **THEN** the pipeline treats it as a validation failure and retries within the budget rather than degrading immediately

#### Scenario: The whole layer can be declared offline
- **WHEN** a profile is disabled or the endpoint is unreachable
- **THEN** the pipeline's outcome is indistinguishable from degradation: the caller receives the fallback, no invalid output escapes, and no game state changes

### Requirement: Structured-output hints are passed per call
The guarded pipeline SHALL accept a layer-neutral per-call request descriptor containing the chat messages, an optional output jsonschema, and an optional schema identifier, and SHALL forward that descriptor to the client so the client can build a `response_format` hint exactly when the profile's `supports_response_format` flag is true. When the flag is false, the client SHALL omit `response_format` entirely and still complete as an ordinary chat completion. Layer-specific schemas remain owned by later changes; this capability defines only the transmission contract.

#### Scenario: A capable profile requests structured output
- **WHEN** a guarded call runs under a profile with `supports_response_format: true` and a per-call descriptor that declares an output schema
- **THEN** the request includes a `response_format` hint derived from that descriptor's schema and identifier

#### Scenario: An incapable profile never sends the hint
- **WHEN** a guarded call runs under a profile with `supports_response_format: false`
- **THEN** the request body contains no `response_format` field and still completes as an ordinary chat completion
