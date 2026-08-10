## Purpose

Defines the generative scene-flavor layer: a pure, guardrail-registered layer on the `scene_builder`
profile that turns a bounded scene context into a Traditional Chinese atmosphere paragraph, with
deterministic output gates (length and no-digit) and a degrade-to-None failure contract that keeps
the deterministic game fully playable with the LLM offline.

## Requirements

## ADDED Requirements

### Requirement: The scene-flavor layer is a pure guarded generative layer on the scene_builder profile
`world/ai/scene_flavor.py` SHALL provide a generative layer that consumes the `scene_builder`
LLM profile through the shared guardrail pipeline: a bounded deterministic prompt built from an
injected context, semantic validation, retry-with-appended-errors, and a degrade fallback
resolving to `None`. The module SHALL import no state writer, no typeclass, no live transport, and
no socket (the repository-wide transport-boundary contract SHALL stay green); the client SHALL be
a required injected argument and an explicit `None` SHALL be rejected with a named error before
any prompt construction or transport work. A disabled `scene_builder` profile SHALL short-circuit
directly to the degrade outcome with no network request.

#### Scenario: The layer resolves to a flavor paragraph with a live client
- **WHEN** `generate_scene_flavor(context, client)` is called with a valid bounded context and a
  `FakeLLMClient` replaying valid prose
- **THEN** it resolves to the prose, no state was written, and no entity or registry was touched

#### Scenario: An explicit None client is rejected before any work
- **WHEN** `generate_scene_flavor(context, None)` is called
- **THEN** it raises the named client-required error before any prompt construction or transport
  interaction

#### Scenario: A disabled profile degrades without a network request
- **WHEN** the `scene_builder` profile has `enabled: false` and `generate_scene_flavor` is invoked
- **THEN** the call resolves to `None` without any transport attempt and without any state change

#### Scenario: The layer keeps the transport-boundary contract
- **WHEN** the repository-wide `world/ai` boundary contract test inspects the scene-flavor module
- **THEN** it imports no state writer, no typeclass, no live transport, and no socket, and the
  existing contract test passes without modification

#### Scenario: Calling before registration surfaces a named not-registered error
- **WHEN** `generate_scene_flavor(context, client)` runs before the `scene_builder` layer hooks are
  registered in the guardrail's actual registry
- **THEN** the call errbacks with a named `SceneFlavorNotRegisteredError` identifying that the
  scene-flavor hooks are not installed, and no flavor is silently fabricated

### Requirement: The flavor output is plain text with deterministic gates
The layer SHALL validate every returned flavor: it SHALL be non-empty, SHALL be at least 50 and at
most 200 characters, SHALL contain at least one CJK Unified Ideograph (Traditional Chinese
surface), and SHALL contain no digit character (any ASCII or Unicode decimal digit).
A validation failure SHALL be appended to the prompt and retried under the profile's retry budget;
retry exhaustion SHALL resolve to `None`. The outcome `None` SHALL be the only pipeline-failure
shape — no exception escapes from the guarded pipeline except the named client-required error;
the named not-registered error is a registration-precondition error, not a pipeline failure.

#### Scenario: Valid flavor passes the gates
- **WHEN** a replay returns Traditional Chinese prose between 50 and 200 characters with no digits
- **THEN** the call resolves to that prose

#### Scenario: A flavor containing digits is rejected and retried
- **WHEN** a replay returns prose containing a decimal digit such as `3 隻狼` or `500 金幣`
- **THEN** the pipeline treats it as a validation failure, retries with the error appended, and on
  exhaustion resolves to `None`

#### Scenario: A non-Chinese flavor is rejected
- **WHEN** a replay returns 50–200 characters of non-Chinese text with no digits (for example
  English prose)
- **THEN** the pipeline treats it as a validation failure and never returns it

#### Scenario: Overlong or undersized flavor is rejected
- **WHEN** a replay returns prose shorter than 50 characters or longer than 200 characters
- **THEN** it is treated as a validation failure and never returned

#### Scenario: Retry exhaustion degrades to None
- **WHEN** every attempt under the retry budget fails validation or transport
- **THEN** the call resolves to `None` and the deterministic game continues unaffected

### Requirement: The flavor prompt is deterministic and data-driven
The layer SHALL render the `scene_builder.system` prompt-library key with exactly four values —
`scene_sentence`, `quest_context`, `room_name`, and `region` — each capped to a bounded length,
and SHALL build the user message from the bounded structured context with stable sorted JSON
serialization. Identical context SHALL produce byte-identical (system, user) message pairs. A
broken or unavailable `scene_builder.system` key SHALL resolve the call to `None` (prompt
unavailability never blocks startup and never raises from the layer).

#### Scenario: Identical context yields byte-identical prompts
- **WHEN** the same bounded context is passed to the prompt builder twice
- **THEN** both calls produce byte-identical system and user messages with all four values
  substituted

#### Scenario: Context fields are capped, never unbounded
- **WHEN** a context fragment exceeds its cap
- **THEN** the rendered prompt contains the capped value and remains within the module's bounds

#### Scenario: An unavailable prompt key degrades to None
- **WHEN** the `scene_builder.system` key is marked unavailable in the prompt library
- **THEN** the entry point resolves to `None` with a logged diagnostic and no state change
