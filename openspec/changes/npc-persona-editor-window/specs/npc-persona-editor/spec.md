## REMOVED Requirements

### Requirement: npc.persona.read returns a private editor snapshot
**Reason**: superseded by the seven-key snapshot below — the five-field result cannot carry the offline-greeting field or its read-only authored default.
**Migration**: consumers (the editor surface) switch to the added requirement's `offline_greeting`/`default_greeting` keys; every previously accepted payload still succeeds.

### Requirement: npc.persona.update replaces the whole card under a version check
**Reason**: superseded by the card-and-greeting submission below — the optional `offline_greeting` component and its atomic single-version semantics extend the same version check.
**Migration**: every previously valid card-only payload remains valid and behaves identically; saves that also change the greeting use the added requirement.

## ADDED Requirements

### Requirement: npc.persona.read returns a private editor snapshot with the offline greeting
`npc.persona.read` SHALL accept a payload of exactly `npc_id`, a positive integer within the protocol safe-integer range and never a boolean. On success it SHALL return a result whose `data` holds exactly `npc_id`, `display_name`, `npc_title`, `persona_version`, `persona`, `offline_greeting`, and `default_greeting`, where `persona` is the complete seven-field card with `identity` holding `public` and `hidden`, `offline_greeting` is the NPC's stored offline-greeting field verbatim (`""` when unset, never initialized or repaired), and `default_greeting` is the read-only authored presentation default resolved at read time — the scripted dialogue-table greeting when the NPC has a table authoring one, `""` otherwise. `default_greeting` is presentation data and SHALL NOT be copied into the stored field, so an authored table or profile line stays live for every NPC whose field is empty. The seven-key result stays within the protocol's result-data field maximum of eight, and every valid payload including CJK and escape-heavy text stays within the protocol's per-string and envelope byte limits. Reading SHALL never initialize or repair a card: an NPC whose card or persona metadata is missing or invalid SHALL be rejected with `npc_persona.unavailable`. Reading SHALL change no game state, clock, currency, quest knowledge, relationship, or party state. Both greeting keys are editor data and follow the existing privacy rule: only the requesting session's result carries them, ordinary snapshots do not, and no card or greeting prose enters logs or narrative output.

#### Scenario: A read returns the seven-key snapshot
- **WHEN** the actor reads a co-located table-backed NPC whose card is at version 3, whose offline-greeting field holds an authored line, and whose dialogue table authors a greeting
- **THEN** the success data has exactly the seven fields with `persona_version` 3, `offline_greeting` the stored field text, and `default_greeting` the table greeting

#### Scenario: Both greetings are empty for an unseeded free-form NPC
- **WHEN** the actor reads a free-form NPC with no dialogue table and no offline-greeting field
- **THEN** the success data has `offline_greeting` and `default_greeting` both `""` and nothing is written

#### Scenario: An uninitialized NPC is unavailable
- **WHEN** the actor reads a co-located NPC with no persona metadata
- **THEN** the result is rejected with `npc_persona.unavailable`, carries no data, and nothing is written

### Requirement: npc.persona.update replaces the card and offline greeting under a version check
`npc.persona.update` SHALL accept a payload of exactly `npc_id`, `expected_persona_version` (a positive safe integer, never a boolean), `persona` (an object with exactly the seven card keys, `identity` with exactly `public` and `hidden`, every leaf a string), and the optional `offline_greeting` (a string of at most 300 code points after normalization containing no newline; an absent or empty value stores the field empty, clearing any override). It SHALL submit card and greeting as one atomic version-checked replacement through the deterministic NPC persona service and SHALL NOT assign entity attributes itself or call any player-persona editing API. A changed card, a changed greeting, or both SHALL return success with the seven-field read data at a version advanced exactly once; a payload identical in both card and greeting SHALL return success at the unchanged version; a version mismatch SHALL be rejected with `npc_persona.version_conflict` naming the current version; a card contract violation SHALL be rejected with its stable field code; an over-bound or multi-line `offline_greeting` SHALL be rejected with `npc_persona.greeting_invalid`; every rejection carries no data and writes nothing. A stored offline-greeting change SHALL advance the same `persona_version` as the card, so the stale-persona completion gate invalidates an in-flight dialogue exchange on a greeting-only edit. A stored offline-greeting change SHALL affect only the selected NPC and SHALL NOT write back to any preset, profile, or dialogue table.

#### Scenario: A save changes only the selected NPC
- **WHEN** two NPCs were initialized from the same profile and the actor saves a changed card or greeting for one of them
- **THEN** only that NPC's card, greeting field, and version change, and the world clock, wallet, quests, relationships, and party are byte-identical

#### Scenario: Two sessions cannot overwrite each other
- **WHEN** two sessions read the same card at version 4, the first saves a change, and the second saves its own change with expected version 4
- **THEN** the second is rejected with `npc_persona.version_conflict` naming version 5 and the first session's card remains stored

#### Scenario: A field violation names the leaf
- **WHEN** the actor saves a card whose `speech_style` is empty
- **THEN** the result is rejected with `npc_persona.required_empty.speech_style`, carries no data, and the stored card is unchanged

#### Scenario: A malformed payload never reaches the adapter
- **WHEN** a client submits an update whose persona lacks `habit`, carries an extra key, whose offline greeting is a number, or whose expected version is `true`
- **THEN** the dispatcher rejects it as `malformed_payload` without invoking the adapter

#### Scenario: A greeting-only save advances the version once
- **WHEN** the actor saves the identical card with one changed offline greeting at the expected version
- **THEN** the success data shows the new greeting and a version advanced by exactly one, and only that NPC changed

#### Scenario: Clearing the field restores the authored default
- **WHEN** the actor saves the identical card with an empty `offline_greeting` over a non-empty stored field
- **THEN** the success data shows `offline_greeting` `""`, the version advanced by one, and the NPC's authored table/profile default is untouched

#### Scenario: An invalid greeting is rejected without writing
- **WHEN** the actor submits an `offline_greeting` over 300 code points or containing a newline after normalization
- **THEN** the result is rejected with `npc_persona.greeting_invalid`, carries no data, and neither card nor field changed

#### Scenario: An in-flight exchange sees a greeting-only edit as stale
- **WHEN** an asynchronous dialogue exchange captured version N and the actor saves a greeting-only change before settlement
- **THEN** the stale-persona completion gate rejects the exchange's settlement through the existing stale-persona outcome
