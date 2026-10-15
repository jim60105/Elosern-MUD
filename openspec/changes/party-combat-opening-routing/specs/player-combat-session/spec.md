# Spec Delta

## REMOVED Requirements

### Requirement: Overwhelm waits for one player choice before compressed resolver-backed outcome
**Reason**: The approved party-combat design replaces this conflicting behavior.
**Migration**: Interactive opening selections seed the party draft; use opening-order metadata and ordinary complete-draft resolution. Independent noninteractive overwhelm mechanics are unchanged. No compatibility route or data migration.


### Requirement: Overwhelm compression is player-direction only
**Reason**: The approved party-combat design replaces this conflicting behavior.
**Migration**: Interactive opening selections seed the party draft; use opening-order metadata and ordinary complete-draft resolution. Independent noninteractive overwhelm mechanics are unchanged. No compatibility route or data migration.


### Requirement: submit_opening_action is the sole compression dispatcher and always grants the player first strike
**Reason**: The approved party-combat design replaces this conflicting behavior.
**Migration**: Interactive opening selections seed the party draft; use opening-order metadata and ordinary complete-draft resolution. Independent noninteractive overwhelm mechanics are unchanged. No compatibility route or data migration.


## MODIFIED Requirements

### Requirement: Player combat submission accepts one explicit target value
The commander/actor draft submission boundary SHALL accept only a concrete list of live participant objects or one of `all-enemies`, `all-allies`, and `all`. It SHALL reject any other scalar, a duplicate explicit participant, or a participant outside the current reconstructed session before initiative. Player-facing NONE and SELF SHALL require an empty list; the facade SHALL bind that empty SELF input to the actor and leave NONE empty.

#### Scenario: Explicit AREA participants drive one round
- **WHEN** a player submits an AREA skill with two distinct current enemy objects
- **THEN** the facade builds one ActionRequest containing both canonical participants and saves the selected actor entry, resolving one ordinary round only when the complete draft is valid

#### Scenario: Approved shorthand reaches ordinary targeting
- **WHEN** a player submits an AREA skill with `all-enemies`
- **THEN** the facade preserves the shorthand for ActionResolver expansion and every resulting candidate passes ordinary target validation

#### Scenario: Old single-object input is not retained
- **WHEN** a production caller passes one participant object instead of a list
- **THEN** the facade rejects the malformed call before initiative rather than wrapping it through a compatibility branch

#### Scenario: SINGLE and AREA keep their target shapes
- **WHEN** a SINGLE or AREA skill is submitted
- **THEN** SINGLE receives exactly one explicit participant, and AREA receives a nonempty explicit list or one approved shorthand

#### Scenario: The facade retains its orchestration ownership
- **WHEN** a submission is processed
- **THEN** the facade retains battlefield reconstruction, shared preview, `ActionResolver.preflight()`, initiative, session persistence, terminal settlement, and recovery ownership

#### Scenario: The facade never owns compression
- **WHEN** compression dispatch is needed
- **THEN** interactive dispatch never compresses and independent noninteractive overwhelm consumers retain their own boundary

#### Scenario: No single-object compatibility overload exists
- **WHEN** a caller attempts the old single-object call shape
- **THEN** no single-object compatibility overload exists to accept it

## ADDED Requirements

### Requirement: Interactive encounter openings seed a draft and never replace party choices with compression
An encounter-starting selection SHALL seed the initiating actor entry and wait for remaining required actors. Interactive rounds, including overwhelming and solo encounters, SHALL preserve selected commands and SHALL NOT dispatch autonomous compressed basic attacks. Existing encounter-specific opening order SHALL remain explicit and ordinary entry order SHALL NOT change initiative.

#### Scenario: Overwhelming party opening
- **WHEN** an exploration attack opens an encounter with companions under an overwhelming verdict
- **THEN** the initiating choice is saved, no action runs until remaining commands confirm and no compressed automatic attacks replace them

#### Scenario: Opening first actor
- **WHEN** an encounter explicitly grants the initiator first action and that actor has low ordinary initiative
- **THEN** the override applies only to its first complete round; later rounds use normal initiative regardless of command order


