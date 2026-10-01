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

### Requirement: npc.persona.read returns a private editor snapshot
`npc.persona.read` SHALL accept a payload of exactly `npc_id`, a positive integer within the protocol safe-integer range and never a boolean. On success it SHALL return a result whose `data` holds exactly `npc_id`, `display_name`, `npc_title`, `persona_version`, and `persona`, where `persona` is the complete normalized card with `identity` holding `public` and `hidden`. It SHALL never initialize or repair a card: an NPC whose card or persona metadata is missing or invalid SHALL be rejected with `npc_persona.unavailable`. Reading SHALL change no game state, clock, currency, quest knowledge, relationship, or party state.

#### Scenario: A read returns the five-field snapshot
- **WHEN** the actor reads a co-located NPC whose card is at version 3
- **THEN** the success data has exactly the five fields, `persona_version` is 3, and `persona.identity.hidden` carries the stored hidden identity

#### Scenario: An uninitialized NPC is unavailable
- **WHEN** the actor reads a co-located NPC with no persona metadata
- **THEN** the result is rejected with `npc_persona.unavailable`, carries no data, and nothing is written

### Requirement: npc.persona.update replaces the whole card under a version check
`npc.persona.update` SHALL accept a payload of exactly `npc_id`, `expected_persona_version` (a positive safe integer, never a boolean), and `persona` (an object with exactly the seven card keys, `identity` with exactly `public` and `hidden`, every leaf a string). It SHALL submit the complete card as one atomic replacement through the deterministic NPC persona service and SHALL NOT assign entity attributes itself or call any player-persona editing API. A changed card SHALL return success with the five-field data at the advanced version; an identical card SHALL return success at the unchanged version; a version mismatch SHALL be rejected with `npc_persona.version_conflict` and a message naming the current version; a contract violation SHALL be rejected with a field-specific code `npc_persona.<reason>[.<leaf>]` and a message naming the field label; an unavailable or uninitialized NPC SHALL be rejected with `npc_persona.unavailable`. In-flight mutations SHALL stay single-flight per session and a retried request ID SHALL return the cached result.

#### Scenario: A save changes only the selected NPC
- **WHEN** two NPCs were initialized from the same profile and the actor saves a changed card for one of them
- **THEN** only that NPC's card and version change, and the world clock, wallet, quests, relationships, and party are byte-identical

#### Scenario: Two sessions cannot overwrite each other
- **WHEN** two sessions read the same card at version 4, the first saves a change, and the second saves its own change with expected version 4
- **THEN** the second is rejected with `npc_persona.version_conflict` naming version 5 and the first session's card remains stored

#### Scenario: A field violation names the leaf
- **WHEN** the actor saves a card whose `speech_style` is empty
- **THEN** the result is rejected with `npc_persona.required_empty.speech_style`, carries no data, and the stored card is unchanged

#### Scenario: A malformed payload never reaches the adapter
- **WHEN** a client submits an update whose persona lacks `habit`, carries an extra key, or whose expected version is `true`
- **THEN** the dispatcher rejects it as `malformed_payload` without invoking the adapter

### Requirement: Card data reaches only the requesting session
Only the success result of `npc.persona.read` or `npc.persona.update` SHALL carry card data, and only to the requesting session. Exploration, dialogue, and every other presentation panel SHALL carry at most the author-editor navigation affordance, never card text or hidden identity. No action message, narrative output, operational event, or analytics record SHALL include card text; error results SHALL carry no `data`. The result data SHALL use only fixed lowercase keys, SHALL use `persona_version` rather than any reserved state key, and SHALL fit the protocol's result-data field, string, and byte limits for every valid card, including maximal cards of CJK text, astral characters, and JSON-escaped characters.

#### Scenario: Snapshots never carry the card
- **WHEN** a full snapshot is published for an actor standing with an NPC whose hidden identity is set
- **THEN** no panel contains any card leaf text

#### Scenario: Logs never carry the card
- **WHEN** a read and an update succeed and a third request is rejected for a field violation
- **THEN** no captured operational event context or action message contains any card leaf text

#### Scenario: Maximal valid cards fit the protocol
- **WHEN** valid cards at the total budget built from CJK text, astral characters, and JSON-escape-heavy characters are returned as success data
- **THEN** both the server result validator and the browser protocol mirror accept the envelope

### Requirement: The browser mirrors the card contract exactly
The browser SHALL carry a DOM-independent mirror of the compact card contract — field set, normalization, code-point counting, per-leaf, identity-section, and total bounds, labels, and stable reason codes — and SHALL produce the same accept or reject decision and reason as the server contract for every case of the shared boundary fixture. The mirror SHALL NOT relax any global protocol limit.

#### Scenario: Shared boundary cases agree across languages
- **WHEN** the shared boundary fixture is evaluated by the server contract tests and by the browser mirror's Node tests
- **THEN** every case yields the same decision, reason code, and leaf in both
