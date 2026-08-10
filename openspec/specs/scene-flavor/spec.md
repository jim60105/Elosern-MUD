## Purpose

Defines the generative scene-flavor layer: a pure, guardrail-registered layer on the `scene_builder`
profile that turns a bounded scene context into a Traditional Chinese atmosphere paragraph, with
deterministic output gates (length and no-digit) and a degrade-to-None failure contract that keeps
the deterministic game fully playable with the LLM offline.

## Requirements

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

### Requirement: Instance quest scenes schedule one post-commit flavor generation
A freshly spawned `BOUND_INSTANCE` quest scene with a scene-sentence context SHALL schedule exactly
one scene-flavor generation, registered through `transaction.on_commit` so it fires only after the
spawn transaction actually commits (a nested outer transaction that rolls back SHALL never schedule
a generation). The scheduling SHALL be fire-and-forget: it never blocks arrival, never delays
materialization, never raises to the caller — synchronous failures (unregistered layer, malformed
context, client-construction failure) included, which SHALL be logged as bounded diagnostics and
resolved to nothing — and a failure resolves to "no flavor". An already-bound stage, a permanent
destination, or a scene without a scene-sentence context SHALL schedule nothing.

#### Scenario: A fresh instance scene schedules one generation
- **WHEN** a player materializes a fresh instance scene whose requirement or archetype carries a
  scene sentence, with the `scene_builder` profile enabled
- **THEN** exactly one flavor generation is scheduled on commit, and the materialization result
  and traversal are unaffected

#### Scenario: A rolled-back outer transaction schedules nothing
- **WHEN** the enter command runs inside an outer transaction that rolls back after materialization
- **THEN** no flavor generation is scheduled or fired

#### Scenario: A synchronous scheduling failure never reaches the command
- **WHEN** the layer is not registered, the context dict is malformed, or client construction
  raises before a Deferred exists
- **THEN** the scheduling call logs a bounded diagnostic, returns normally, and the 進入 command
  completes without error

#### Scenario: An already-bound stage schedules nothing
- **WHEN** the player re-enters a stage that is already bound (no fresh spawn)
- **THEN** no flavor generation is scheduled and the existing binding is returned

#### Scenario: A scene without scene-sentence context schedules nothing
- **WHEN** a stage's requirement has neither a scene sentence nor a resolvable archetype sentence
- **THEN** the materialization carries no flavor context and nothing is scheduled

#### Scenario: Offline profile resolves to no flavor without a network request
- **WHEN** the `scene_builder` profile is disabled and a fresh scene materializes
- **THEN** the scheduled generation resolves to no flavor, no network request occurs, and the room
  is unchanged

### Requirement: The flavor write is deterministic, idempotent, and sole-writer
`room.db.scene_flavor` SHALL be written only by the deterministic SceneBuilder apply helper. The
write SHALL verify the room's database row authoritatively (a cached typeclass is not proof of
existence after reclamation) before writing, SHALL be a no-op when the room no longer exists or
already carries a flavor (never overwrites, never regenerates), SHALL catch database and
object-deletion exceptions and resolve them to the same no-op outcome, SHALL never roll back or
block the materialization transaction, and SHALL leave the room description (`room.db.desc`)
untouched.

#### Scenario: A completed flavor is written once
- **WHEN** a flavor generation completes successfully for an existing flavor-less room
- **THEN** `room.db.scene_flavor` holds the flavor text and `room.db.desc` is unchanged

#### Scenario: A vanished room receives no write
- **WHEN** the flavor completes after the instance room was reclaimed and only a stale cached
  reference remains
- **THEN** the authoritative existence check fails, no write occurs, no error escapes, and the
  outcome is "no flavor"

#### Scenario: A room with an existing flavor never regenerates
- **WHEN** a completion tries to apply a flavor to a room that already carries one
- **THEN** the existing value is kept and no regeneration occurs

### Requirement: Completed flavor is pushed to present players and rendered in look
On a successful write, the flavor SHALL be pushed as plain text to every `PlayerCharacter` whose
location is the room (absent players are not chased). The shared appearance layer SHALL render
`room.db.scene_flavor` as a paragraph after the room description and before the exit line, on the
text look command, the character's `at_look` seam, and the webclient `explore.look` action
identically. A room without flavor SHALL render exactly as today.

#### Scenario: Present players receive the flavor on completion
- **WHEN** a flavor completes while players are inside the room
- **THEN** those players receive the flavor text, and players who left receive nothing

#### Scenario: Look renders the flavor paragraph on every entry path
- **WHEN** a player looks at a flavor-bearing scene room through the text 看 command, the `at_look`
  seam, and the webclient `explore.look` action
- **THEN** all three outputs show the room description followed by the flavor paragraph, followed
  by the 「出口」 line, with no English frame string

#### Scenario: Flavor-less rooms render as today
- **WHEN** a player looks at a room with no `scene_flavor`
- **THEN** the appearance contains no flavor paragraph and is otherwise identical to the same
  room rendered without the flavor attribute (the shared zh-tw room frame applies to every room
  typeclass, including `InstanceRoom`)
