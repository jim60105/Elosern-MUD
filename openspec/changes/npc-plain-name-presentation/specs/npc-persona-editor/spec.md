# Spec Delta

## MODIFIED Requirements

### Requirement: npc.persona.read returns a private editor snapshot with the offline greeting
`npc.persona.read` SHALL accept a payload of exactly `npc_id`. On success it SHALL return a result whose `data` holds exactly `npc_id`, `display_name`, `persona_version`, `persona`, `offline_greeting`, and `default_greeting`, where `persona` is the complete normalized seven-field card with `identity` holding `public` and `hidden`. Reading SHALL never initialize or repair a card, and SHALL change no game state, clock, currency, quest knowledge, relationship, or party state.

#### Scenario: A read returns the title-free snapshot
- **WHEN** the actor reads a co-located table-backed NPC whose card is at version 3, whose offline-greeting field holds an authored line, and whose dialogue table authors a greeting
- **THEN** the success data has exactly the six fields with `persona_version` 3, `persona.identity.hidden` the stored hidden identity, `offline_greeting` the stored field text, and `default_greeting` the table greeting

#### Scenario: A profile-backed NPC previews its profile greeting
- **WHEN** the actor reads an NPC with no dialogue table whose profile provenance names a profile authoring a greeting, and whose field is empty
- **THEN** `offline_greeting` is `""`, `default_greeting` is the profile greeting, and nothing is written

#### Scenario: Both greetings are empty for an unseeded free-form NPC
- **WHEN** the actor reads a free-form NPC with no dialogue table, no profile greeting, and no offline-greeting field
- **THEN** the success data has `offline_greeting` and `default_greeting` both `""` and nothing is written

#### Scenario: An uninitialized NPC is unavailable
- **WHEN** the actor reads a co-located NPC with no persona metadata
- **THEN** the result is rejected with `npc_persona.unavailable`, carries no data, and nothing is written

#### Scenario: The payload id is a positive safe integer
- **WHEN** a `npc.persona.read` payload is validated
- **THEN** `npc_id` must be a positive integer within the protocol safe-integer range and never a boolean

#### Scenario: offline_greeting echoes the stored field verbatim
- **WHEN** a read succeeds
- **THEN** `offline_greeting` is the NPC's stored offline-greeting field verbatim (`""` when unset, never initialized or repaired)

#### Scenario: default_greeting follows the resolver's authored precedence
- **WHEN** a read resolves `default_greeting`
- **THEN** it is the read-only authored presentation default resolved at read time through the same precedence the no-keyword greeting resolver applies below the instance field — the scripted dialogue-table greeting when the NPC has a table authoring one, else the authored profile greeting named by the NPC's profile provenance, else `""`

#### Scenario: The default preview is presentation-only
- **WHEN** a read returns `default_greeting`
- **THEN** it is presentation data and is not copied into the stored field, so an authored table or profile line stays live for every NPC whose field is empty

#### Scenario: The result stays inside protocol limits
- **WHEN** a read result is serialized
- **THEN** the six-key result stays within the protocol's result-data field maximum of eight, and every valid payload including CJK and escape-heavy text stays within the protocol's per-string and envelope byte limits

#### Scenario: An invalid card is unavailable, never repaired
- **WHEN** the actor reads an NPC whose card or persona metadata is missing or invalid
- **THEN** the read is rejected with `npc_persona.unavailable` and the card is never initialized or repaired

#### Scenario: Greeting keys follow the editor privacy rule
- **WHEN** a read returns either greeting key
- **THEN** both greeting keys are editor data under the existing privacy rule: only the requesting session's result carries them, ordinary snapshots do not, and no card or greeting prose enters logs or narrative output

#### Scenario: A read returns the six-key snapshot
- **WHEN** a co-located NPC has persona version 3 and stored/table greetings
- **THEN** the title-free result has exactly six fields: npc_id, display_name, persona_version, persona, offline_greeting and default_greeting; version/private identity/greetings retain their actual canonical values
