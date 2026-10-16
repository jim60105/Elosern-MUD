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

### Requirement: A round and its settlement form one atomic persistence unit

The shared submission body SHALL persist the round's action effects, the updated session metadata (round count, fled/knockout sets, the consumed opening-order policy), and any terminal settlement (exam outcome, clock advance, session clearing) together with draft consumption, round-revision admission and its durable completion receipt as one durable transaction with snapshot/restore of all touched entities, so a process termination can never leave half-round durable state.

#### Scenario: Termination mid-round leaves no half-committed round

- **WHEN** a process terminates after some combatant effects committed but before the session record update
- **THEN** after restart either the full round (effects plus `rounds_elapsed`) is durable or none of it is

#### Scenario: Upkeep effects commit inside the same unit
- **WHEN** the upkeep settlement stages damaging-tick HP, defeat entries, or quest effects
- **THEN** those upkeep-settled effects commit inside the same unit: the body forwards the session's `simulated` and companion `nonlethal_keys` policy into its one ordinary resolution, and an upkeep settlement failure rolls back the whole round

#### Scenario: Defeat aftermath commits in the one transaction
- **WHEN** a hostile-defeat terminal outcome settles
- **THEN** the complete defeat aftermath (violator departure, weak buff grant, and the adult phases contributed by later changes) commits in that one transaction together with the `settled_tick` marker and the session-record clearing

#### Scenario: Departure deletions ride on_commit
- **WHEN** the defeat aftermath deletes the departing entities physically
- **THEN** the deletions ride `transaction.on_commit`, so an outer round transaction's rollback discards them too

#### Scenario: Accepted draft survives technical failure
- **WHEN** a technical failure follows a participant, item mirror, session metadata or terminal-settlement write
- **THEN** all durable and touched Evennia cache state returns to pre-round values and the accepted complete draft remains recoverable for retry

## ADDED Requirements

### Requirement: Interactive encounter openings seed a draft and never replace party choices with compression
An encounter-starting selection SHALL seed the initiating actor entry and wait for remaining required actors. Interactive rounds, including overwhelming and solo encounters, SHALL preserve selected commands and SHALL NOT dispatch autonomous compressed basic attacks. Existing encounter-specific opening order SHALL remain explicit and ordinary entry order SHALL NOT change initiative.

#### Scenario: Overwhelming party opening
- **WHEN** an exploration attack opens an encounter with companions under an overwhelming verdict
- **THEN** the initiating choice is saved, no action runs until remaining commands confirm and no compressed automatic attacks replace them

#### Scenario: Opening first actor
- **WHEN** an encounter explicitly grants the initiator first action and that actor has low ordinary initiative
- **THEN** the override applies only to its first complete round; later rounds use normal initiative regardless of command order

#### Scenario: The opening seed takes concrete participants only
- **WHEN** an approved AREA shorthand is handed to the opening seed path
- **THEN** it is rejected before initiative rather than resolved through a compatibility branch, because the initiation already expanded that line-up into the session's concrete enemy identities

#### Scenario: An off-roster participant is rejected before initiative
- **WHEN** the opening seed is handed a participant absent from the reconstructed session's roster
- **THEN** it rejects with the ordinary not-present reason before initiative, exactly as the draft boundary does for the same input, persisting no round

#### Scenario: An opening seed with absent companions runs nothing
- **WHEN** an exploration opening seeds its selection while a required companion has not confirmed
- **THEN** the session and the seed's draft entry are durable together, no action has run, no round time has passed, and later round failures preserve that committed draft

