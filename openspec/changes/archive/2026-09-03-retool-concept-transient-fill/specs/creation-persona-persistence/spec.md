# creation-persona-persistence — Delta Spec

## ADDED Requirements

### Requirement: The retired concept stage leaves no draft or carry-over machinery
The creation-wizard draft service SHALL provide exactly the `preset_selected` and `custom_filled` stages; the `concept_filled` stage, the deterministic concept-apply service, the fingerprint compare-and-swap around concept application, and the custom-save persona carry-over (including its race-equality comparison) SHALL NOT exist. A draft carrying the retired stage or shape SHALL be treated as malformed through the existing degradation path. The draft-fingerprint helper SHALL remain solely for activation confirmation.

#### Scenario: No draft stage or apply service survives
- **WHEN** the draft service and wizard module surface are inspected
- **THEN** no `concept_filled` stage, apply service, concept CAS, or carry-over branch is present, and a stored legacy concept-shaped draft degrades to no draft

#### Scenario: A custom save never touches persona implicitly
- **WHEN** a custom save submits `persona: null` while any prior draft value existed
- **THEN** the stored draft's persona becomes null with no carry-over and no race comparison

## MODIFIED Requirements

### Requirement: Activation persists the persona block in the import-card shape
When the custom draft carries a non-null persona block, `activate_player_character()` SHALL write `entity.db.persona` as a dict with the import-card keys (identity/personality/life_story/habit/appearance/social_connection), the block filling the three prose fields and the remaining keys stored as empty containers, inside the same all-or-nothing activation transaction; a persona write failure SHALL roll back activation, and a draft with a null persona SHALL write nothing beyond the background rule below. The persona block SHALL be read from the custom draft — no concept-stage state exists to consult. When the draft carries a player-authored bounded background field, the same activation transaction SHALL additionally store that text under the persona record's `background` key (kept separate from the three prose fields), so a custom character's background survives activation; a draft without a background SHALL omit the key. `world/rules/character_creation.py` SHALL be the sole writer of creation-generated persona; `world/imports/loader.py` remains the import-time writer and is unchanged.

#### Scenario: A custom draft persists its persona at activation
- **WHEN** a pending character activates with a custom draft carrying a non-null persona block
- **THEN** `entity.db.persona` contains the six-key import-card dict with the block's three prose fields and empty containers for the rest, activation commits, and the character is an active persona owner

#### Scenario: A custom background is persisted inside the persona record
- **WHEN** a pending character activates with a custom draft carrying a non-empty bounded `background`
- **THEN** `entity.db.persona` contains the six import-card keys plus a `background` key holding the exact accepted text, activation commits, and the character is an active persona owner

#### Scenario: A persona write failure rolls back activation
- **WHEN** a write failure is injected into the persona-persistence step of the activation transaction
- **THEN** activation rolls back entirely, the character remains pending, and no canonical identity, trait, or persona state is written

#### Scenario: A draft without persona or background writes nothing
- **WHEN** a pending character activates with a draft whose persona is null and that has no background
- **THEN** `entity.db.persona` remains absent and activation behaves exactly as before

### Requirement: The background survives the draft, concept, custom-save, and activation journey
The `background` SHALL be a first-class custom-draft field: `save_custom_draft` validates and stores it, the draft normalizer accepts it with its bound and includes it in the draft fingerprint. Activation SHALL merge the background into the persona record together with any custom-draft persona block — the six import-card keys are written first, then `background` when the draft carries one — inside the same all-or-nothing transaction.

#### Scenario: A background persists through every entry order
- **WHEN** a background is entered, saved through the custom form, and activation commits
- **THEN** `entity.db.persona["background"]` equals the entered text at every step and after activation, and the custom persona block is also present when the draft carries one

### Requirement: The creation panel offers a concept field and adapter sharing the guarded pipeline
The WebClient creation panel SHALL provide a bounded concept text field, and the production action registry SHALL register `creation.concept` with a payload of exactly `concept` (a non-empty string of at most the declared bound). The adapter SHALL obtain the actor from the authenticated session, reject unknown fields, and run the same guarded `character_creation` generative layer as the Telnet command (injected client); on success it SHALL store the validated proposal in the session-scoped transient slot, return the stable applied outcome, and refresh the `creation` panel so the proposal reaches the browser through the panel's proposal slot; on degrade it SHALL return the stable outcome with no state change. The adapter SHALL NOT assign `.db`, traits, identity attributes, or `creation_pending` directly, SHALL write no persistent draft state, and SHALL NOT route through the text command parser.

#### Scenario: A concept submission delivers the proposal through the panel
- **WHEN** a pending character submits `creation.concept` with a bounded concept and the guarded layer returns a valid proposal
- **THEN** the adapter stores the proposal in the session slot, returns the applied outcome, and the completion `ui_update` for the refreshed `creation` panel carries the proposal (with its transient revision) for the browser to pre-fill

#### Scenario: Offline concept degrades without state change
- **WHEN** the `character_creation` layer is offline and a pending character submits `creation.concept`
- **THEN** the adapter returns the stable unavailable message, no draft, slot, or character state changes, and the preset/custom/activate adapters remain fully usable

#### Scenario: Unknown fields on the concept adapter are rejected
- **WHEN** a client submits `creation.concept` carrying actor, account, session, skills, or any field beyond `concept`
- **THEN** exact-schema validation rejects the request without invoking the adapter or the generative layer

## REMOVED Requirements

### Requirement: A server-owned concept draft stores the validated proposal and persona block
**Reason**: the concept becomes a transient form-filler with no server draft (design §2/§4.1); persona content now reaches the browser as proposal and custom-draft data, inverting the old never-online rule.
**Migration**: replaced by `concept-transient-fill::The retired concept stage leaves no draft or carry-over machinery` (draft surface) and `concept-transient-fill::Persona rides the custom draft, payload, and activation` (persona storage); the reconnect-persistence scenario survives in `webclient-character-creation-ui`'s draft requirement.

### Requirement: Concept-apply is deterministic and fingerprint-protected
**Reason**: with zero persistent writes there is nothing to protect — the CAS existed only because a late LLM response could clobber the concept draft; the user-facing risk of a clobbered form was explicitly accepted, and the panel proposal slot is last-write-wins per session.
**Migration**: the activation-fingerprint confirmation (`fix-creation-finalization-safety` D2) is untouched; concept behaviour is now specified by `concept-transient-fill::Concept applies transiently with zero persistent writes`.
