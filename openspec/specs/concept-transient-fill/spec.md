# concept-transient-fill Specification

## Purpose

Define the transient concept form-fill contract: the `creation.concept` adapter
and the Telnet concept command apply a validated generative proposal with zero
persistent writes through a session-scoped revision-numbered slot, the
`creation` panel renders that slot, the custom draft, payload, and activation
carry the player-owned persona block, and the browser pre-fills its editable
form from the proposal without ever auto-submitting it.

## Requirements

### Requirement: Concept applies transiently with zero persistent writes
The `creation.concept` adapter and the Telnet `character concept` command SHALL run the same guarded `character_creation` generative pipeline and, on a validated proposal, write no persistent state: the WebClient adapter SHALL store the validated proposal (race, subrace, allocations, and the persona block) in a session-scoped transient slot mirroring the existing session options-state pattern, return a plain success with the stable code `concept_applied`, and declare the `creation` panel affected so the panel refresh carries the proposal. Because the concept path writes no draft, no concept outcome SHALL read, write, or invalidate the activation-confirmation fingerprint state — a still-valid earlier save confirmation survives a concept apply untouched, and a concept completion can never authorize activation of a draft it did not save. The slot SHALL bind the actor it was written for (mirroring the options-state owner binding), SHALL NOT render for a different puppet, and SHALL be cleared when the session's puppet changes. The slot SHALL be overwritten by a later successful apply, cleared when a `creation.custom` save or `creation.reset` succeeds, and lost with the session. The `ui_action_result` envelope SHALL NOT gain a data field, and no draft, trait, identity, or `creation_pending` value SHALL change on any concept outcome.

#### Scenario: A successful apply fills only the session slot
- **WHEN** a pending character submits `creation.concept` and the guarded layer returns a valid proposal
- **THEN** the adapter writes nothing persistent, stores the proposal with a fresh revision in the session slot, returns `concept_applied`, and the completion `ui_update` for the refreshed `creation` panel (published before the matching result) carries the proposal

#### Scenario: A concept apply never authorizes an unconfirmed draft
- **WHEN** a session holds a save confirmation for draft X, the persisted draft later changes to Y, and that session completes a concept apply
- **THEN** the recorded confirmation still names X, and a subsequent `creation.activate` is refused as stale

#### Scenario: The slot never follows a puppet switch
- **WHEN** a session holds a proposal written for one puppet and then switches puppet (or an in-flight concept completion settles after the switch)
- **THEN** the slot does not render for the new puppet, and an in-flight completion whose admitted actor is no longer the puppet writes nothing

#### Scenario: Offline concept degrades with no state change
- **WHEN** the `character_creation` layer is offline and a pending character submits `creation.concept`
- **THEN** the adapter returns the stable unavailable outcome, no slot, draft, or character state changes, and the preset/custom/activate adapters remain fully usable

#### Scenario: A later custom save or reset clears the slot
- **WHEN** a proposal is pending in the session slot and then `creation.custom` saves successfully, or `creation.reset` succeeds
- **THEN** the slot is cleared and subsequent `creation` panels contain no proposal key

#### Scenario: Reconnect loses only the in-flight fill
- **WHEN** a session holding an unconsumed proposal slot disconnects and a new session logs in for the same pending character
- **THEN** the new session's creation panel shows the persisted draft unchanged and contains no proposal key

### Requirement: The creation panel renders the transient proposal
The `creation` panel available payload SHALL additionally accept the optional top-level key
`proposal`, present only when the authenticated session holds a transient proposal. The proposal
object SHALL contain exactly `revision` (a positive integer transient sequence number, strictly
increasing within the session across successive applies), `race` (a registry key), `subrace` (a
registry key or null), `allocations` (one integer per `ALLOCATABLE_AXES` axis — the full seven-axis
set including `magic_power`), and `persona` (an object with exactly `personality`, `life_story`,
and `habit`, each 1..600 non-empty code points), plus five optional transient-fill keys that are
present only when the validated generative proposal carried a value: `display_name` (1..64 code
points), `age` and `apparent_age` (integers in 18..10000), `background` (1..600 code points), and
`affinity_elements` (a list of at most 8 distinct registered element keys). An absent optional key
SHALL NOT be encoded as null, and every value SHALL be deep-copied from the session snapshot with
no live object reference. A worst-case proposal (three 600-code-point persona fields, a maximum
background, a maximum display name, both ages, and an eight-element affinity set) SHALL still fit
the canonical envelope bound.

#### Scenario: A panel renders the pending proposal
- **WHEN** a creation panel is built for a session whose slot holds a proposal
- **THEN** the payload contains the `proposal` key with the exact base shape and the snapshot's
  values

#### Scenario: A proposal carries the transient-fill fields it received
- **WHEN** a validated proposal carried a display name, both ages, a background, and an affinity set
- **THEN** the panel's `proposal` object names all five additional keys with those exact values

#### Scenario: A proposal omits absent transient-fill keys
- **WHEN** a validated proposal carried none of the five optional transient-fill fields
- **THEN** the panel's `proposal` object contains none of the five keys (never null-valued copies)

#### Scenario: A slotless panel omits the key
- **WHEN** a creation panel is built for a session with an empty slot
- **THEN** the payload contains no `proposal` key at all (not a null value)

#### Scenario: A worst-case proposal fits the envelope bound
- **WHEN** a proposal with three maximum-length persona fields, a maximum background, a maximum
  display name, and an eight-element affinity set renders through the panel
- **THEN** the canonical JSON stays within `MAX_CANONICAL_JSON_BYTES` and passes exact-schema
  validation

#### Scenario: Successive identical applies carry increasing revisions
- **WHEN** the same concept is applied twice and both responses are byte-identical in content
- **THEN** the second panel proposal carries a strictly greater `revision` than the first


### Requirement: Persona rides the custom draft, payload, and activation
The `custom_filled` draft SHALL carry a required, nullable `persona` key holding either null or exactly `{personality, life_story, habit}` with each value 1..600 non-empty code points validated through the existing persona-block validator, and a draft missing the key SHALL be treated as a malformed legacy shape and degraded through the existing draft-degradation path. The `creation.custom` payload SHALL accept exactly nine keys including a required `persona` key (null or the exact three-key object; the browser convention ships null when all three fields are empty), and the deterministic save SHALL store the submitted value verbatim without any carry-over or race comparison. Activation SHALL write the character's persona record from the custom draft's persona key (falling back to the existing background-only branch when it is null).

#### Scenario: A custom save stores a valid persona block verbatim
- **WHEN** `creation.custom` submits the nine-key payload with a valid three-field persona block
- **THEN** the saved draft's `persona` equals the submitted block exactly and the panel's draft renders it

#### Scenario: A malformed persona block is rejected without mutation
- **WHEN** `creation.custom` submits a persona value that is not null and misses, adds, or empties a prose key, or exceeds 600 code points
- **THEN** the request is rejected with a stable reason and no draft value changes

#### Scenario: An all-empty persona ships as null
- **WHEN** `creation.custom` submits `persona: null`
- **THEN** the draft stores a null persona and activation later writes no prose fields (background-only behaviour preserved)

#### Scenario: Activation sources persona from the custom draft
- **WHEN** a pending character activates with a custom draft carrying a non-null persona block
- **THEN** the activation transaction persists the import-card persona record from that block plus any background, and no concept-stage state is consulted

### Requirement: The browser form pre-fills from the proposal without submitting
Whenever the rendered proposal's `revision` exceeds the last revision the browser applied, the
browser creation form SHALL copy the proposal's race, subrace, allocations, and three persona
fields, plus every present transient-fill field — display name, actual age, apparent age,
background, and affinity elements (filtered to the incoming race's registered element keys and
trimmed to its input bound) — into the local
unsent form state and record that revision; an absent transient-fill field SHALL leave the local
value untouched, except that the race write itself always enforces the new race's affinity
bound: a proposal that changes the race SHALL trim an existing over-bound local affinity
selection to that bound even when the proposal carries no affinity elements, because the
player-picked set must stay within the race's legal capacity (the same trim the player's own
race change performs). When the fresh apply completes while the player is on the concept tab, the form
SHALL switch to the custom tab automatically, and the client SHALL surface exactly one toast
naming the applied proposal — the success confirmation, written by the form's own apply path
through the action-feedback queue API, never duplicated by the result slice (which stays silent
on success); a panel
rebuild or a remount that re-renders an already-unconsumed proposal
SHALL fill without any automatic tab switch. The form SHALL NOT auto-submit,
and SHALL keep the three persona textareas visible and editable in custom mode at all times.
Persona local validation SHALL be all-empty-or-all-filled: an all-empty triple submits null; a
partially-filled triple blocks submission with a localized reason. When the proposal's race
differs from the player's current selection while local persona text exists, the form SHALL show a
non-blocking review prompt naming the incoming race; no server-side overwrite or rejection SHALL
accompany a race change.

#### Scenario: A proposal fills an untouched form
- **WHEN** the panel delivers a proposal carrying the base fields and all five transient-fill
  fields and the player has entered no local edits
- **THEN** race, subrace, allocations, the three textareas, the name field, both age fields, the
  background field, and the affinity checkboxes show the proposal values and nothing is submitted

#### Scenario: An absent transient-fill field keeps the local value
- **WHEN** a new proposal omits the display name and both ages
- **THEN** the name field keeps its local (possibly empty) value, both age fields keep their
  current values, and the present fields are replaced

#### Scenario: A race-changing proposal without affinity elements enforces the new race bound
- **WHEN** a new proposal changes the race while carrying no affinity elements and the player's
  local selection exceeds the new race's input bound
- **THEN** the selection is trimmed to the new race's bound and the name, age, and background
  fields keep their local values

#### Scenario: Applying from the concept tab lands on the custom tab
- **WHEN** a fresh proposal revision is applied while the player is on the concept tab
- **THEN** the form switches to the custom tab showing the filled values, one toast confirms the
  apply, and no action is submitted

#### Scenario: A remount fills without navigating
- **WHEN** the overlay remounts against a panel that still carries an unconsumed proposal
- **THEN** the form fills from it but no automatic tab switch happens and no toast is surfaced

#### Scenario: Rebuilds and identical re-applies are distinguished by revision
- **WHEN** the panel re-renders the same `revision` after the player edited the form, and then a
  fresh apply of byte-identical content raises the revision
- **THEN** the rebuild leaves the player's edits untouched while the new revision replaces the
  generated fields

#### Scenario: A partial persona blocks submission locally
- **WHEN** exactly one of the three persona textareas is non-empty and the player submits the
  custom form
- **THEN** the browser blocks submission with the all-or-empty reason and sends no action

#### Scenario: A race-changing proposal surfaces a review prompt
- **WHEN** a new proposal arrives whose race differs from the selected race while persona text is
  present locally
- **THEN** a non-blocking review prompt names the proposal's race and the form remains submittable
  with the player's own text
