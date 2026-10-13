## Purpose

Collect same-round resolved observations with bounded transaction-safe volatile memory and terminal cleanup. This capability defines observable behavior at the monster decision boundary.

## ADDED Requirements

### Requirement: Resolved observations are compact and bounded
Memory SHALL contain public resolved session/round/sequence, source identity/faction, skill/item identity, recipients and outcome magnitudes/status facts. It SHALL retain at most three actual rounds and 128 records per session, whichever expires first, with one compact bounded-recipient record per settled action/upkeep boundary.

#### Scenario: Capacity and privacy
- **WHEN** a session resolves large groups and more than the window capacity
- **THEN** records remain bounded, loss is traced, and pending requests, private prose, callbacks and entity graphs are absent

#### Scenario: Event coverage
- **WHEN** successful skills, health/support items and round upkeep execute
- **THEN** their public outcomes are observed at their execution boundary; rejected or rolled-back actions are not successful history

### Requirement: Same round observations remain transaction local
Earlier successful actions SHALL be visible before the next provider decision through a transaction-local overlay. Memory publication SHALL occur only after the outermost successful commit; rollback SHALL discard uncommitted observations while preserving prior committed memory.

#### Scenario: Earlier teammate action
- **WHEN** the first monster acts, then a later provider runs in the same round
- **THEN** the later snapshot includes the resolved outcome without reading unresolved choices

#### Scenario: Nested rollback
- **WHEN** an inner action/savepoint succeeds and the enclosing transaction later fails, or a savepoint itself fails
- **THEN** nothing from failed work publishes; prior committed memory remains and savepoint-local observations are removed

#### Scenario: Overwhelm and standalone
- **WHEN** overwhelm runs several real rounds or a direct non-session round executes
- **THEN** actual round/slot identities are preserved; direct rounds cannot modify shared session memory without a real transaction boundary

### Requirement: Terminal cleanup supersedes publication
Successful terminal victory/defeat, flee, forfeit, recovery and missing/deleted participant handling SHALL discard session memory and recorded tuning after commit. Terminal cleanup SHALL supersede every earlier publication callback in that transaction. Rollback SHALL preserve prior committed memory.

#### Scenario: Late publication
- **WHEN** publication is queued before terminal cleanup and callbacks run after success
- **THEN** no callback recreates terminated session state

#### Scenario: Generation order
- **WHEN** an older publication callback follows a newer committed overlay
- **THEN** sequence/generation checks prevent overwriting newer memory; hooks are installed once and removed after rounds or exceptions

#### Scenario: Failed cleanup
- **WHEN** a terminal path fails before outer commit
- **THEN** prior committed memory and configuration are retained

#### Scenario: Rolled back terminal savepoint with successful outer commit
- **WHEN** terminal work sets a cleanup token inside a savepoint, the savepoint rolls back, its exception is caught and a later action succeeds before outer commit
- **THEN** all failed-savepoint publication controls and pending tuning cleanup are restored; failed termination cannot delete history/configuration or suppress successful observation publication, while genuinely committed termination still prevents recreation

### Requirement: Observation access follows current session membership
Memory SHALL be isolated by session and stable actor identity. Battlefield reconstruction SHALL preserve committed history in process. Eligible projections SHALL use current live participation and faction. Restart SHALL clear history and use validated startup tuning without a durable sidecar.

#### Scenario: Reconstruction and isolation
- **WHEN** the same session rebuilds its battlefield while another session contains overlapping actors
- **THEN** the first session retains its history and neither can read the other session history

#### Scenario: Stale actors and restart
- **WHEN** an actor dies, flees, disappears or changes faction, then the server restarts
- **THEN** current projections exclude unauthorized or missing targets; reconstructed sessions begin with empty history

