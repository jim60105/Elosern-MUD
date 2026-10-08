## Purpose

Defines the narrator layer that maps deterministic `EventLog` records to Traditional Chinese prose through the guarded generative pipeline. The layer is deterministic-first: prompt construction is stable and bounded, every failure path degrades to the injected template renderer, and the module never crosses the single-writer or transport boundaries.

## Requirements

### Requirement: Narrator maps EventLogs to Traditional Chinese prose through the guarded pipeline
`world/ai/narrator.py` SHALL provide `narrate_event_logs(event_logs, client) -> Deferred[str]`, a pure mapping from one or more deterministic `EventLog` objects to Traditional Chinese prose. The client SHALL be a required injected argument, never constructed or imported by the module. The function SHALL build a prompt from the event record, submit a layer-neutral request descriptor (messages only, no output schema) through the `narrator` layer's guarded call, and resolve with the prose text.

#### Scenario: A valid EventLog resolves to narrated prose
- **WHEN** `narrate_event_logs()` is called with one `EventLog` and a client that returns accepted prose
- **THEN** the returned Deferred resolves with exactly that prose text and no game state changes

#### Scenario: Multiple EventLogs narrate as one coherent passage
- **WHEN** `narrate_event_logs()` is called with a tuple of several `EventLog` objects and a client that returns accepted prose
- **THEN** the returned Deferred resolves with one prose passage derived from all of the entries, and no game state changes

#### Scenario: Narrator output is never parsed back
- **WHEN** a consumer inspects the value returned by `narrate_event_logs()`
- **THEN** it is a plain string of prose and the narrator exposes no parser or write-back path that interprets it

#### Scenario: An explicit None client is rejected before any network work
- **WHEN** `narrate_event_logs()` is called with `client=None` under an enabled narrator profile
- **THEN** the call errbacks with a named `NarratorClientRequiredError` before any prompt build or transport interaction, rather than crashing inside the guarded pipeline

#### Scenario: The narrator holds no state-mutating access
- **WHEN** `narrate_event_logs()` runs
- **THEN** the narrator has access to no state-mutating API anywhere in the mapping path

#### Scenario: The client arrives through an injected protocol
- **WHEN** the narrator needs its client
- **THEN** it accepts the client through an injected protocol rather than importing a live transport

### Requirement: Narrator prompt construction is deterministic, bounded, and faithful
`world/ai/narrator.py` SHALL provide `build_narrator_prompt(event_logs)` returning a system/user
message pair. The system message SHALL be loaded from the prompt library's `narrator.system` key
via `render_prompt("narrator.system")`. The user message SHALL serialize the event record with
stable, sorted serialization so identical input produces byte-identical prompts.

#### Scenario: Identical EventLogs produce identical prompts
- **WHEN** `build_narrator_prompt()` is called twice with the same event data
- **THEN** both calls return byte-identical system and user messages

#### Scenario: A large combat round produces a bounded prompt
- **WHEN** `build_narrator_prompt()` is called with an EventLog containing more entries than the cap and fields longer than the string caps
- **THEN** the returned messages stay within the fixed bounds and remain valid, parseable prompt text

#### Scenario: The prompt carries entity keys, never live references
- **WHEN** the serialized user message for an event involving actor `elosia` and target `violet` is inspected
- **THEN** it contains the keys `elosia` and `violet` and contains no live entity object anywhere in the serialization

#### Scenario: The prompt instructs fidelity to the record
- **WHEN** the system message is inspected
- **THEN** it directs narration in Traditional Chinese and forbids inventing events, outcomes, or numbers beyond the record

#### Scenario: A compressed overwhelm summary narrates with team keys intact
- **WHEN** `build_narrator_prompt()` is called with an `EventLog` containing an `overwhelm_resolution` summary entry whose actor and target are `Battlefield.teams` keys and whose `data` carries `rounds`, `hits`, and `total_damage`
- **THEN** the serialized user message preserves the team keys and the summary data within the prompt bounds, with no live references

#### Scenario: Input exceeding the prompt bounds degrades to the full deterministic template
- **WHEN** `narrate_event_logs()` is called with more EventLogs or entries than the prompt bounds allow, under a client that would otherwise return prose
- **THEN** the Deferred resolves to the injected template renderer's output for the full event set instead of narrating a truncated record

#### Scenario: The system message is sourced from the prompt library
- **WHEN** the narrator system message is inspected
- **THEN** it equals `render_prompt("narrator.system")` and the prompt-library file is the only place its text is defined

#### Scenario: The library is the sole source, never a Python constant
- **WHEN** the narrator module's source is inspected
- **THEN** the system prompt text is embedded nowhere as a Python constant

#### Scenario: The user message serializes the full event record
- **WHEN** a user message is built for an event
- **THEN** it serializes the actor, skill key, targets, time cost, and every entry's kind/actor/target/data and canonical `text_template`

#### Scenario: The prompt carries bounded size parameters
- **WHEN** any prompt is constructed
- **THEN** it is bounded by a fixed maximum entry count, per-field string-length caps, and a bounded total size, so a large combat round cannot produce an unbounded prompt

#### Scenario: The prompt instructs exact fidelity to the record
- **WHEN** the system message instructs the model
- **THEN** it directs narration of exactly the recorded events without inventing outcomes, numbers, or state

### Requirement: Narrator degrades to deterministic template rendering when the pipeline fails
The `narrator` layer SHALL register a guardrail degrade fallback so that when the layer profile is disabled, a transport failure occurs, or validation retries are exhausted, `narrate_event_logs()` resolves to the deterministic template rendering of the same EventLogs via the injected template renderer, and SHALL NOT raise into the caller or leave the game blocked.

#### Scenario: A disabled narrator profile returns template prose
- **WHEN** the `narrator` profile is disabled and `narrate_event_logs()` is called
- **THEN** the Deferred resolves to the injected template renderer's output for the same EventLogs, with zero client calls made

#### Scenario: A transport failure degrades to template prose
- **WHEN** the client errbacks with a transport failure and `narrate_event_logs()` is called
- **THEN** the Deferred resolves to the injected template renderer's output for the same EventLogs, with no exception escaping to the caller

#### Scenario: Exhausted validation retries degrade to template prose
- **WHEN** every retry within the `1 + max_retries` budget returns prose that fails semantic validation
- **THEN** the Deferred resolves to the injected template renderer's output for the same EventLogs

#### Scenario: Degraded output equals the deterministic template rendering
- **WHEN** the injected renderer is a join of `world.rules.event_log.render_plain_text` over the same EventLogs
- **THEN** the degraded result is byte-identical to rendering each EventLog with `render_plain_text` and joining the lines

#### Scenario: The renderer is injected from a world.rules-importing site
- **WHEN** the template renderer is registered through `register_narrator(template_renderer)`
- **THEN** registration happens from a site that may import `world.rules`

#### Scenario: The narrator module never imports world.rules
- **WHEN** the imports of `world/ai/narrator.py` are scanned
- **THEN** the module imports no `world.rules` module

### Requirement: Narrator semantic validation keeps prose within safe bounds
The `narrator` layer SHALL register semantic validators under stable names so the shared pipeline retries on shape violations and degrades on exhaustion. Validators SHALL reject prose that is empty or whitespace-only, exceeds a fixed length cap, contains no CJK Unified Ideograph, or contains template-placeholder syntax. Each rejected attempt SHALL append a concrete validation message to the prompt before retrying.

#### Scenario: Empty prose is rejected and retried
- **WHEN** a client returns whitespace-only text for a narrator call
- **THEN** the pipeline treats it as a validation failure, appends the error, and retries rather than returning the empty text

#### Scenario: Non-Chinese prose is rejected and retried
- **WHEN** a client returns non-empty text with no CJK Unified Ideograph
- **THEN** the pipeline rejects it as a validation failure and does not return it as Traditional Chinese prose

#### Scenario: Template-placeholder leakage is rejected
- **WHEN** a client returns text containing a known template placeholder such as `{actor}` or `{data[raw_roll]}`
- **THEN** the pipeline rejects it as a validation failure and does not return it as prose

#### Scenario: Bounded-length prose with ordinary punctuation passes validation
- **WHEN** a client returns non-empty Traditional Chinese prose within the length cap containing no template-placeholder syntax
- **THEN** the pipeline returns it as the narrated passage with no retry

#### Scenario: Over-length prose is rejected and retried
- **WHEN** a client returns prose exceeding the fixed length cap
- **THEN** the pipeline rejects it as a validation failure rather than returning oversized prose

#### Scenario: Placeholder syntax is defined by the brace-pair pattern
- **WHEN** validators decide whether prose contains template-placeholder syntax
- **THEN** they detect a `{`-`}` brace pair wrapping a known field name such as `{actor}`, `{target}`, or `{data[...]}`, indicating the model echoed the deterministic `text_template` formatting syntax

#### Scenario: The CJK check guards the language contract
- **WHEN** validators reject prose containing no CJK Unified Ideograph
- **THEN** obviously non-Chinese output is not accepted as Traditional Chinese prose

### Requirement: Narrator preserves the single-writer and transport boundaries
`world/ai/narrator.py` SHALL import no state writer, no live transport, and no socket, and SHALL consume the client and the template renderer through injected protocols. `register_narrator()` SHALL install its hooks atomically and SHALL be idempotent. Calling `narrate_event_logs()` before the narrator hooks are registered in the guardrail's actual registry SHALL surface a named `NarratorNotRegisteredError` rather than silently degrading or reaching the unregistered-fallback path.

#### Scenario: The narrator module stays inside the transport boundary
- **WHEN** the repository-wide transport-boundary contract scans `world/ai/narrator.py`
- **THEN** it finds no import of a state writer, no live transport symbol, and no socket import, and the module is not `client.py`

#### Scenario: All narrator tests run offline
- **WHEN** the narrator test suite runs with no LLM service available
- **THEN** every test passes using recorded fixtures and none opens a network connection

#### Scenario: Missing registration fails loudly with a named error
- **WHEN** `narrate_event_logs()` is called before any `register_narrator()` call, including after a test has reset the shared guardrail registries
- **THEN** the call errbacks with a named `NarratorNotRegisteredError` identifying that the narrator hooks are not installed, and no prose is silently fabricated

#### Scenario: Duplicate registration keeps the first renderer
- **WHEN** `register_narrator()` is called twice with two different template renderers
- **THEN** the second call is a no-op, the first renderer remains installed, and narrate behavior is unchanged

#### Scenario: Narrator tests never contact a live endpoint
- **WHEN** any test of the narrator runs
- **THEN** it uses `FakeLLMClient` or an equivalent recorded fixture and never contacts a live endpoint, per design §10
