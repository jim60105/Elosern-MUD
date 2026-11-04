# Spec Delta

## ADDED Requirements

### Requirement: Deficits recover only through delayed game-time episodes
A first committed below-lower population SHALL schedule delayed recovery once, and due waves SHALL cancel when local density is restored or otherwise replenish complete legal compositions and retry remaining deficits at positive authored intervals.

#### Scenario: Loss and delay
- **WHEN** a loss first creates deficit at T and further losses occur before T+delay
- **THEN** no loss, kill callback, visit, view or hunt acceptance spawns immediately or restarts the existing due time

#### Scenario: Obsolete episode
- **WHEN** explicit placement or returning living members restore local population to L before due
- **THEN** settlement clears the episode without a birth, random draw or generation-sequence increment

#### Scenario: Wave and blockage
- **WHEN** a due zone remains below L with fitting outcomes or no lawful space/home headroom
- **THEN** it births at most the wave budget with all ceilings, or births nothing; remaining deficit schedules the next interval

#### Scenario: Clock partition
- **WHEN** equal elapsed time is advanced once or partitioned with identical external events
- **THEN** chronological wave plans, sequence, due time and settlement progress agree and reload preserves them

### Requirement: Loss timing and encounter protection survive deferred combat settlement
Population settlement SHALL use actual committed loss occurrence times with recorded combat round offsets and historical encounter protection, never treating future losses as earlier birth headroom.

#### Scenario: Late-round defeat
- **WHEN** combat begins at100, a monster dies in round3 at118, and recovery delay is10
- **THEN** earliest due is128; a pending wave at110 cannot use that later loss as free local or home headroom

#### Scenario: No reinforcements
- **WHEN** clock catch-up passes ticks when the battlefield was active after its session has closed
- **THEN** no birth enters its historically protected cell or replaces/appends a participant

#### Scenario: Nondeath and replay
- **WHEN** a member flees, is absent, knocked out, or the same committed loss is replayed
- **THEN** no false defeat or repeated loss notification changes recovery state

#### Scenario: Outer failure
- **WHEN** a later clock stage raises after multiple real waves
- **THEN** the clock, pending-loss ledger, due state, all created IDs/registrations/attachments and caches roll back together and no success event survives

### Requirement: Population lifecycle replays loss and site boundaries chronologically
Population settlement SHALL merge pending presence transitions, site lifecycle boundaries and regional due waves chronologically, applying same-tick site births before ordinary births without exposing future changes to earlier waves.

#### Scenario: Later loss starts a new episode
- **WHEN** L is3, local population2 has due110, a wave restores3 at110, and a previously recorded later loss occurs118 with delay10
- **THEN** the118 boundary creates a new due128; recording that loss while an older episode was pending cannot consume its later deficit

#### Scenario: Cancellation before later loss
- **WHEN** explicit restoration ends an older episode before a pending future loss makes local density deficient again
- **THEN** that later occurrence starts a new delayed episode, with identical outcomes under equal interval partitioning

#### Scenario: Site recovery cannot affect earlier waves
- **WHEN** a zone has a wave due110 and an overlapping site's recovery is due140 during [100,160]
- **THEN** births and due state equal settlement through [100,125] then [125,160], and the140 site members do not occupy the110 headroom

### Requirement: Historical population evidence preserves removed ownership and cell protection
Population history SHALL retain complete identity, before/after presence, home/site ownership and actual-coordinate encounter intervals until chronological settlement no longer needs them, with atomic restart-safe serialization.

#### Scenario: Deleted away-home member
- **WHEN** a home-owned member dies outside its home zone at118 and is deleted before settlement evaluates110
- **THEN** its saved before facts still consume historical home headroom at110 and no object resurrection or public presence is fabricated

#### Scenario: Restart during protected combat
- **WHEN** a mapped session or terminal receipt reloads before accumulated combat time has settled
- **THEN** its exact wilderness cell and closed historical interval remain protected independently of pooled-room IDs until settlement passes the interval

#### Scenario: Explicit mutation routes join the owner
- **WHEN** existing GM or quest placement, HP transition, deletion or lawful relocation changes mapped living population
- **THEN** actual registration and the complete transition commit with that owner's operation; deficits use the occurrence tick and rollback restores both live and durable surfaces
