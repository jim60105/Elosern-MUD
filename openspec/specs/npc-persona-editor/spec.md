## Purpose

Let the authenticated player, as an author, read and replace the complete compact card of an NPC standing with their active character through two allowlisted, re-authorized, version-checked browser actions, without exposing card data anywhere else.

## Requirements

### Requirement: Author editing admits only a co-located NPC for the session's own active character
The `npc.persona.read` and `npc.persona.update` actions SHALL resolve the actor only from the authenticated session's current, activated, account-owned puppet and SHALL admit it only in exploration or dialogue mode: a creation-pending actor, an actor in an active combat session, and a possessed NPC acting as the puppet SHALL be rejected with `npc_persona.not_allowed`. The `npc_id` SHALL be re-resolved on every request from the actor's current location contents and SHALL be admitted only when it names an NPC-family instance; an unknown, forged, remote, departed, or deleted identity, a player character (including another account's), a `Monster`, and any other object SHALL be rejected with `npc_persona.no_target`. Author editing SHALL NOT require a conversation, affinity, or schedule slot.

#### Scenario: A co-located NPC is readable in exploration and dialogue
- **WHEN** an activated character standing with an NPC that carries a valid card submits `npc.persona.read` in exploration mode, and again while in a dialogue session with a different NPC
- **THEN** both reads succeed for that NPC without any conversation, affinity, or schedule requirement

#### Scenario: Forbidden targets are rejected without data
- **WHEN** the actor submits either action for a forged id, another account's player character, a monster, an NPC in another room, or an NPC deleted after it was read
- **THEN** the result is rejected with `npc_persona.no_target`, carries no data, and nothing is written

#### Scenario: Forbidden modes are rejected
- **WHEN** the actor is creation-pending, in an active combat session, or a possessed NPC
- **THEN** both actions are rejected with `npc_persona.not_allowed` and nothing is written

#### Scenario: A target that left after the read cannot be saved
- **WHEN** the actor reads an NPC's card, the NPC then moves to another room, and the actor submits an update
- **THEN** the update is rejected with `npc_persona.no_target` and the card is unchanged

### Requirement: npc.persona.read returns a private editor snapshot with the offline greeting
`npc.persona.read` SHALL accept a payload of exactly `npc_id`, a positive integer within the protocol safe-integer range and never a boolean. On success it SHALL return a result whose `data` holds exactly `npc_id`, `display_name`, `npc_title`, `persona_version`, `persona`, `offline_greeting`, and `default_greeting`, where `persona` is the complete normalized seven-field card with `identity` holding `public` and `hidden`, `offline_greeting` is the NPC's stored offline-greeting field verbatim (`""` when unset, never initialized or repaired), and `default_greeting` is the read-only authored presentation default resolved at read time through the same precedence the no-keyword greeting resolver applies below the instance field — the scripted dialogue-table greeting when the NPC has a table authoring one, else the authored profile greeting named by the NPC's profile provenance, else `""`. `default_greeting` is presentation data and SHALL NOT be copied into the stored field, so an authored table or profile line stays live for every NPC whose field is empty. The seven-key result stays within the protocol's result-data field maximum of eight, and every valid payload including CJK and escape-heavy text stays within the protocol's per-string and envelope byte limits. Reading SHALL never initialize or repair a card: an NPC whose card or persona metadata is missing or invalid SHALL be rejected with `npc_persona.unavailable`. Reading SHALL change no game state, clock, currency, quest knowledge, relationship, or party state. Both greeting keys are editor data and follow the existing privacy rule: only the requesting session's result carries them, ordinary snapshots do not, and no card or greeting prose enters logs or narrative output.

#### Scenario: A read returns the seven-key snapshot
- **WHEN** the actor reads a co-located table-backed NPC whose card is at version 3, whose offline-greeting field holds an authored line, and whose dialogue table authors a greeting
- **THEN** the success data has exactly the seven fields with `persona_version` 3, `persona.identity.hidden` the stored hidden identity, `offline_greeting` the stored field text, and `default_greeting` the table greeting

#### Scenario: A profile-backed NPC previews its profile greeting
- **WHEN** the actor reads an NPC with no dialogue table whose profile provenance names a profile authoring a greeting, and whose field is empty
- **THEN** `offline_greeting` is `""`, `default_greeting` is the profile greeting, and nothing is written

#### Scenario: Both greetings are empty for an unseeded free-form NPC
- **WHEN** the actor reads a free-form NPC with no dialogue table, no profile greeting, and no offline-greeting field
- **THEN** the success data has `offline_greeting` and `default_greeting` both `""` and nothing is written

#### Scenario: An uninitialized NPC is unavailable
- **WHEN** the actor reads a co-located NPC with no persona metadata
- **THEN** the result is rejected with `npc_persona.unavailable`, carries no data, and nothing is written

### Requirement: npc.persona.update replaces the card and offline greeting under a version check
`npc.persona.update` SHALL accept a payload of exactly `npc_id`, `expected_persona_version` (a positive safe integer, never a boolean), `persona` (an object with exactly the seven card keys, `identity` with exactly `public` and `hidden`, every leaf a string), and the optional `offline_greeting` (a string; after the card contract's text normalization it SHALL hold at most 300 code points and no newline; an absent or empty value stores the field empty, clearing any override). It SHALL submit card and greeting as one atomic version-checked replacement through the deterministic NPC persona service and SHALL NOT assign entity attributes itself or call any player-persona editing API. A changed card, a changed greeting, or both SHALL return success with the seven-field read data at a version advanced exactly once; a payload identical in both card and greeting SHALL return success at the unchanged version; a version mismatch SHALL be rejected with `npc_persona.version_conflict` and a message naming the current version; a card contract violation SHALL be rejected with a field-specific code `npc_persona.<reason>[.<leaf>]` and a message naming the field label; an over-bound or multi-line `offline_greeting` SHALL be rejected with `npc_persona.greeting_invalid` and a message naming the 離線問候語 field; an unavailable or uninitialized NPC SHALL be rejected with `npc_persona.unavailable`; every rejection carries no data and writes nothing. A stored offline-greeting change SHALL advance the same `persona_version` as the card, so the stale-persona completion gate invalidates an in-flight dialogue exchange on a greeting-only edit. A stored offline-greeting change SHALL affect only the selected NPC and SHALL NOT write back to any preset, profile, or dialogue table. In-flight mutations SHALL stay single-flight per session and a retried request ID SHALL return the cached result.

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
- **THEN** the success data shows `offline_greeting` `""`, the version advanced by one, the NPC's authored table/profile default is untouched, and the no-keyword greeting resolver answers that default again

#### Scenario: An invalid greeting is rejected without writing
- **WHEN** the actor submits an `offline_greeting` over 300 code points or containing a newline after normalization
- **THEN** the result is rejected with `npc_persona.greeting_invalid`, carries no data, and neither card nor field changed

#### Scenario: An in-flight exchange sees a greeting-only edit as stale
- **WHEN** an asynchronous dialogue exchange captured version N and the actor saves a greeting-only change before settlement
- **THEN** the stale-persona completion gate rejects the exchange's settlement through the existing stale-persona outcome

### Requirement: Card data reaches only the requesting session
Only the success result of `npc.persona.read` or `npc.persona.update` SHALL carry card or offline-greeting data, and only to the requesting session. Exploration, dialogue, and every other presentation panel SHALL carry at most the author-editor navigation affordance, never card text, hidden identity, or the editor's greeting keys. No action message, narrative output, operational event, or analytics record SHALL include card or greeting-field text; error results SHALL carry no `data`. The result data SHALL use only fixed lowercase keys, SHALL use `persona_version` rather than any reserved state key, and SHALL fit the protocol's result-data field, string, and byte limits for every valid payload, including maximal cards and maximal 300-code-point greetings of CJK text, astral characters, and JSON-escaped characters.

#### Scenario: Snapshots never carry the card
- **WHEN** a full snapshot is published for an actor standing with an NPC whose hidden identity is set
- **THEN** no panel contains any card leaf text

#### Scenario: Logs never carry the card
- **WHEN** a read and an update succeed and a third request is rejected for a field violation
- **THEN** no captured operational event context or action message contains any card leaf or greeting-field text

#### Scenario: Maximal valid cards fit the protocol
- **WHEN** valid cards at the total budget, together with a 300-code-point offline greeting and a default greeting, built from CJK text, astral characters, and JSON-escape-heavy characters are returned as success data
- **THEN** both the server result validator and the browser protocol mirror accept the envelope

### Requirement: The browser mirrors the card contract exactly
The browser SHALL carry a DOM-independent mirror of the compact card contract — field set, normalization, code-point counting, per-leaf, identity-section, and total bounds, the exact rendering labels and separators the server counts, and stable reason codes — and of the bounded offline-greeting rule (300 code points after normalization, no newline, empty allowed), and SHALL produce the same accept or reject decision and reason, and the same rendered card total, as the server contract for every case of the shared boundary fixtures. The mirror SHALL NOT relax any global protocol limit.

#### Scenario: Shared boundary cases agree across languages
- **WHEN** the shared card and offline-greeting boundary fixtures are evaluated by the server contract tests and by the browser mirror's Node tests
- **THEN** every case yields the same decision, reason code, leaf, and (for valid cards that declare one) rendered total in both

#### Scenario: The greeting bound is exact
- **WHEN** an offline greeting of exactly 300 code points, one of 301 code points, and one whose normalized text still contains a newline are evaluated by both contracts
- **THEN** the first is accepted and the other two are rejected as `greeting_invalid` in both
