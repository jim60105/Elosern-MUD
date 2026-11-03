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

