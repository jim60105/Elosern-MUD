# Spec Delta

## MODIFIED Requirements

### Requirement: The browser form pre-fills from the proposal without submitting
The browser creation form SHALL apply only a fresh proposal revision to local unsent fields, preserving omitted values subject to the incoming race’s affinity bound. It SHALL NOT auto-submit. Fresh completion from concept mode SHALL navigate to the identity step; unchanged rebuilds and remounts SHALL NOT navigate.

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
- **THEN** the form switches to the custom tab’s identity step showing the filled values, one toast confirms the
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

#### Scenario: An absent transient-fill field keeps the local value but the race write enforces the affinity bound
- **WHEN** a proposal is applied and an optional transient-fill field is absent
- **THEN** the field SHALL leave the local value untouched, except that the race write itself always enforces the new race's affinity bound: a proposal that changes the race SHALL trim an existing over-bound local affinity selection to that bound even when the proposal carries no affinity elements, because the player-picked set must stay within the race's legal capacity (the same trim the player's own race change performs)

#### Scenario: A fresh apply from the concept tab switches tabs with exactly one toast
- **WHEN** a fresh apply completes while the player is on the concept tab
- **THEN** the form SHALL switch to the custom tab’s identity step automatically, and the client SHALL surface exactly one toast naming the applied proposal — the success confirmation, written by the form's own apply path through the action-feedback queue API, never duplicated by the result slice (which stays silent on success)

#### Scenario: A rebuild or remount fills without navigating
- **WHEN** a panel rebuild or a remount re-renders an already-unconsumed proposal
- **THEN** the form SHALL fill without any automatic tab switch

#### Scenario: The persona textareas stay visible and editable
- **WHEN** the browser creation form is in custom mode
- **THEN** the form SHALL keep the three persona textareas visible and editable on the story step, preserving their values while other steps are displayed

#### Scenario: An all-empty persona triple submits null
- **WHEN** persona local validation — all-empty-or-all-filled — meets an all-empty triple
- **THEN** the form submits null; a partially-filled triple blocks submission with a localized reason

#### Scenario: A race-changing proposal with local persona text shows a review prompt
- **WHEN** the proposal's race differs from the player's current selection while local persona text exists
- **THEN** the form SHALL show a non-blocking review prompt naming the incoming race, and no server-side overwrite or rejection SHALL accompany a race change
