## ADDED Requirements

### Requirement: Narrator maps EventLogs to Traditional Chinese prose through the guarded pipeline
`world/ai/narrator.py` SHALL provide `narrate_event_logs(event_logs, client) -> Deferred[str]`, a pure mapping from one or more deterministic `EventLog` objects to Traditional Chinese prose. The client SHALL be a required injected argument (never constructed or imported by the module), and `narrate_event_logs()` SHALL reject an explicit `None` client with a named `NarratorClientRequiredError` before any prompt construction or transport interaction. The function SHALL build a prompt from the event record, submit a layer-neutral request descriptor (messages only, no output schema) through the `narrator` layer's guarded call, and resolve with the returned prose text. The narrator SHALL have no access to any state-mutating API, SHALL return plain text that is never parsed back into game state, and SHALL accept the client through an injected protocol rather than importing a live transport.

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

### Requirement: Narrator prompt construction is deterministic, bounded, and faithful
`world/ai/narrator.py` SHALL provide `build_narrator_prompt(event_logs)` returning a system/user message pair. The prompt SHALL serialize the event record (actor, skill key, targets, time cost, and every entry's kind/actor/target/data and canonical `text_template`) with stable, sorted serialization so identical input produces byte-identical prompts. The prompt SHALL be bounded: a fixed maximum entry count, per-field string-length caps, and a bounded total size, so a large combat round cannot produce an unbounded prompt. It SHALL contain only entity keys and plain JSON-compatible data — never live entity references — and SHALL instruct the model to narrate exactly the recorded events without inventing outcomes, numbers, or state.

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

### Requirement: Narrator degrades to deterministic template rendering when the pipeline fails
The `narrator` layer SHALL register a guardrail degrade fallback so that when the layer profile is disabled, a transport failure occurs, or validation retries are exhausted, `narrate_event_logs()` resolves to the deterministic template rendering of the same EventLogs via the injected template renderer, and SHALL NOT raise into the caller or leave the game blocked. The template renderer SHALL be injected through `register_narrator(template_renderer)` from a site that may import `world.rules`; `world/ai/narrator.py` itself SHALL NOT import any `world.rules` module.

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

### Requirement: Narrator semantic validation keeps prose within safe bounds
The `narrator` layer SHALL register semantic validators under stable names so the shared pipeline retries on shape violations and degrades on exhaustion. Validators SHALL reject empty or whitespace-only prose, prose exceeding a fixed length cap, prose containing no CJK Unified Ideograph (so obviously non-Chinese output is not accepted as Traditional Chinese prose), and prose containing template-placeholder syntax (a `{`-`}` brace pair wrapping a known field name such as `{actor}`, `{target}`, or `{data[...]}`) that indicates the model echoed the deterministic `text_template` formatting syntax. Each rejected attempt SHALL append a concrete validation message to the prompt before retrying.

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

### Requirement: Narrator preserves the single-writer and transport boundaries
`world/ai/narrator.py` SHALL import no state writer, no live transport, and no socket, and SHALL consume the client and the template renderer through injected protocols. Every test of the narrator SHALL use `FakeLLMClient` or an equivalent recorded fixture and never contact a live endpoint, per design §10. `register_narrator()` SHALL install its hooks atomically and SHALL be idempotent (a second call keeps the first renderer). Calling `narrate_event_logs()` before the narrator hooks are registered in the guardrail's actual registry SHALL surface a named `NarratorNotRegisteredError` rather than silently degrading or reaching the guardrail's unregistered-fallback path.

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
