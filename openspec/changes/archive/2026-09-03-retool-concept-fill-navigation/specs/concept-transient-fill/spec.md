## MODIFIED Requirements

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
