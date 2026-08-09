## ADDED Requirements

### Requirement: A server-owned concept draft stores the validated proposal and persona block
The creation-wizard draft service SHALL provide a `concept_filled` stage storing exactly the
validated proposal values (`race`, `subrace`, `allocations`) plus an optional persona block
(`personality`, `life_story`, `habit` bounded text fields), written only by the deterministic
concept-apply service from a proposal that passed the registry/band validation. The persona block
SHALL persist with the draft across logout, login, reload, and reconnect, SHALL be cleared with
the draft at activation and reset, and SHALL NOT be accepted from any client-submitted field. A
later `creation.custom` save SHALL preserve the persona block only when the submitted race equals
the concept draft's race; otherwise the block SHALL be cleared.

#### Scenario: A concept draft persists its persona across reconnect
- **WHEN** a concept-apply saves a validated concept draft with a persona block, then the session
  disconnects and reconnects
- **THEN** the draft's concept stage and persona block are intact and activation later persists
  the persona

#### Scenario: A custom save with a different race clears the persona
- **WHEN** a player edits the custom form's race to a different race after a concept draft was
  saved
- **THEN** the custom save clears the persona block and the panel no longer shows the
  background-generated indicator

#### Scenario: The persona block is cleared atomically with the draft
- **WHEN** activation commits or `creation.reset` succeeds for a concept draft
- **THEN** the draft and its persona block are cleared in the same transaction and no later
  snapshot or activation returns them

### Requirement: Concept-apply is deterministic and fingerprint-protected
The deterministic concept-apply service SHALL re-validate the proposal against the registries and
race bands and save the concept draft inside one transaction that compares the character's draft
fingerprint captured before the generative call; a mismatch SHALL return a stale outcome and
write nothing. Both the Telnet `character concept` command and the `creation.concept` adapter
SHALL call this same service.

#### Scenario: A late concept response cannot overwrite a newer draft
- **WHEN** the generative call is in flight and another session or entry saves or clears the
  draft, then the concept response arrives
- **THEN** the apply service detects the fingerprint mismatch, returns a stale outcome, and the
  newer draft is unchanged

#### Scenario: A matching fingerprint applies the concept draft
- **WHEN** the draft fingerprint at apply time equals the fingerprint captured before the call
- **THEN** the concept draft is saved atomically with the validated proposal and persona block

### Requirement: Activation persists the persona block in the import-card shape
When the draft carries a persona block, `activate_player_character()` SHALL write
`entity.db.persona` as a dict with exactly the import-card keys
(identity/personality/life_story/habit/appearance/social_connection), the block filling the three
prose fields and the remaining keys stored as empty containers, inside the same all-or-nothing
activation transaction; a persona write failure SHALL roll back activation, and a draft without a
persona block SHALL write nothing. `world/rules/character_creation.py` SHALL be the sole writer of
creation-generated persona; `world/imports/loader.py` remains the import-time writer and is
unchanged.

#### Scenario: A concept draft persists its persona at activation
- **WHEN** a pending character activates with a draft carrying a persona block
- **THEN** `entity.db.persona` contains the six-key import-card dict with the block's three prose
  fields and empty containers for the rest, activation commits, and the character is an active
  persona owner

#### Scenario: A persona write failure rolls back activation
- **WHEN** a write failure is injected into the persona-persistence step of the activation
  transaction
- **THEN** activation rolls back entirely, the character remains pending, and no canonical
  identity, trait, or persona state is written

#### Scenario: A draft without persona writes nothing
- **WHEN** a pending character activates with a draft that has no persona block
- **THEN** `entity.db.persona` remains absent and activation behaves exactly as before

### Requirement: The creation panel offers a concept field and adapter sharing the guarded pipeline
The WebClient creation panel SHALL provide a bounded concept text field, and the production action
registry SHALL register `creation.concept` with a payload of exactly `concept` (a non-empty string
of at most the declared bound). The adapter SHALL obtain the actor from the authenticated session,
reject unknown fields, capture the draft fingerprint, run the same guarded `character_creation`
generative layer as the Telnet command (injected client), and call the deterministic concept-apply
service; on success it SHALL refresh the `creation` panel, on degrade or stale fingerprint it
SHALL return the stable outcome with no state change. The panel SHALL render the concept field and
the draft's finite controls pre-filled from the concept stage plus a non-content indicator that a
background was generated; persona content SHALL NOT be part of any panel payload or browser state.
The adapter SHALL NOT assign `.db`, traits, identity attributes, or `creation_pending` directly and
SHALL NOT route through the text command parser.

#### Scenario: A concept submission fills the draft form
- **WHEN** a pending character submits `creation.concept` with a bounded concept and the guarded
  layer returns a valid proposal with a matching fingerprint
- **THEN** the adapter saves the concept draft (including the server-owned persona block),
  refreshes the `creation` panel with the pre-filled finite controls and the background indicator,
  and the player completes the form and activates through the ordinary flow

#### Scenario: Offline concept degrades without state change
- **WHEN** the `character_creation` layer is offline and a pending character submits
  `creation.concept`
- **THEN** the adapter returns the stable unavailable message, no draft or character state
  changes, and the preset/custom/activate adapters remain fully usable

#### Scenario: A stale draft fingerprint rejects the apply
- **WHEN** the draft changed between the fingerprint capture and the concept response
- **THEN** the adapter returns the stale outcome, writes nothing, and refreshes the panel

#### Scenario: Unknown fields on the concept adapter are rejected
- **WHEN** a client submits `creation.concept` carrying actor, account, session, persona, skill,
  or any field beyond `concept`
- **THEN** exact-schema validation rejects the request without invoking the adapter or the
  generative layer

#### Scenario: Persona content never reaches the browser
- **WHEN** a creation panel or snapshot is produced for a concept draft carrying a persona block
- **THEN** no payload contains persona text, keys, or length information — at most the
  background-generated indicator is present
