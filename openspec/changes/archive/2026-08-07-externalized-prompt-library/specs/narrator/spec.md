## MODIFIED Requirements

### Requirement: Narrator prompt construction is deterministic, bounded, and faithful
`world/ai/narrator.py` SHALL provide `build_narrator_prompt(event_logs)` returning a system/user
message pair. The system message SHALL be loaded from the prompt library's `narrator.system` key
via `render_prompt("narrator.system")`; the library is the sole source of the narrator's system
prompt text, and the module SHALL NOT embed it as a Python constant. The user message SHALL
serialize the event record (actor, skill key, targets, time cost, and every entry's
kind/actor/target/data and canonical `text_template`) with stable, sorted serialization so
identical input produces byte-identical prompts. The prompt SHALL be bounded: a fixed maximum
entry count, per-field string-length caps, and a bounded total size, so a large combat round
cannot produce an unbounded prompt. It SHALL contain only entity keys and plain JSON-compatible
data — never live entity references — and SHALL instruct the model to narrate exactly the recorded
events without inventing outcomes, numbers, or state.

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

#### Scenario: The system message is sourced from the prompt library
- **WHEN** the narrator system message is inspected
- **THEN** it equals `render_prompt("narrator.system")` and the prompt-library file is the only place its text is defined

#### Scenario: Input exceeding the prompt bounds degrades to the full deterministic template
- **WHEN** `narrate_event_logs()` is called with more EventLogs or entries than the prompt bounds allow, under a client that would otherwise return prose
- **THEN** the Deferred resolves to the injected template renderer's output for the full event set instead of narrating a truncated record
