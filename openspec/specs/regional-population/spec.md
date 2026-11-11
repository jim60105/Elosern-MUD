# regional-population Specification

## Purpose
Own deterministic persistent ordinary monster births, individual budgets and atomic initialization independently from transient wilderness rooms and foreign placement owners.

## Requirements

### Requirement: Automatic births satisfy local and home-owned individual ceilings
Automatic birth waves SHALL count living individuals independently against local-zone, home-owned, per-cell and per-wave ceilings, retaining ownership independently from current presence.

#### Scenario: Local and home measures
- **WHEN** a zone-owned living member leaves or detaches while a foreign visitor arrives
- **THEN** the member still consumes home headroom, the visitor consumes local headroom, each ID is counted once per measure and ownership is unchanged

#### Scenario: Manual excess
- **WHEN** manual, site or quest individuals exceed a local or cell ceiling
- **THEN** automatic births stop without deleting, relocating or modifying any existing individual

#### Scenario: Complete fitting groups
- **WHEN** a weighted composition has multiple count outcomes
- **THEN** only complete legal outcomes fitting every ceiling are selected; no row is truncated below its minima

### Requirement: Birth occurrences retain deterministic persistent individual state
Population initialization and successful waves SHALL persist selection seed and sequence with fresh individual identities and home ownership, reselecting position and composition per occurrence without replacing living survivors.

#### Scenario: Initialization once
- **WHEN** an initialized world reloads, rereads source, prepares or recycles a room, or receives a player
- **THEN** the same living IDs, consumed resources, initialization flag and selection state remain; no initial filling repeats

#### Scenario: Occurrence selection
- **WHEN** two lawful births use different saved occurrence inputs in a synthetic pool
- **THEN** selection can differ at the same coordinate and replay of either input reproduces its own complete plan

#### Scenario: No materialized room
- **WHEN** a birth occurs at an eligible inactive coordinate
- **THEN** the actual ID is registered without creating a room and later activation attaches that same ID

### Requirement: Population wave commit is atomic across durable and live surfaces
Each wave SHALL commit its complete constructed population, registrations, attachments and selection state atomically with surrounding owned settlement, restoring durable state and live caches on any later failure.

#### Scenario: Failure after real writes
- **WHEN** a fault follows an actual member construction and coordinate registration or a later scheduling/state write
- **THEN** DB reload and in-process state equal baseline, no half-group or success event remains and retry repeats the failed selection

#### Scenario: Protection and refusals
- **WHEN** birth space is protected by an active encounter, unavailable or temporarily full
- **THEN** no enemy is appended to a persisted session; invalid authoring and unavailable world state are distinct from temporary blocked birth space

#### Scenario: Commit observability
- **WHEN** a wave commits or an unchanged read runs
- **THEN** only the committed wave emits its bounded facade boundary event with available identifiers; reads emit no mutation event

### Requirement: Shared population seed and explicit registrations are owner supplied
Map population ownership SHALL persist an explicitly initialized world seed and register lawful explicit wilderness placements through the placing owner's atomic operation without applying ordinary birth exclusions or changing home ownership.

#### Scenario: No implicit seed default
- **WHEN** a fresh script is explicitly provisioned with a seed or an existing seed is reread
- **THEN** the saved seed is written once and reused, while missing or malformed seed reads refuse without selecting an implicit default

#### Scenario: Manual and quest actual registration
- **WHEN** an existing GM or quest placement creates an approved individual on a valid wilderness surface inside an automatic birth buffer
- **THEN** it is registered as that actual ID, counted locally and visible after room recycling, with unchanged placing ownership and complete post-registration rollback

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
Population settlement SHALL merge presence, site, recovery and activity boundaries chronologically, applying lawful arrivals and site-before-regional births before contacts and idle departures without exposing future state to earlier decisions.

#### Scenario: Later loss starts a new episode
- **WHEN** L is3, local population2 has due110, a wave restores3 at110, and a previously recorded later loss occurs118 with delay10
- **THEN** the118 boundary creates a new due128; recording that loss while an older episode was pending cannot consume its later deficit

#### Scenario: Cancellation before later loss
- **WHEN** explicit restoration ends an older episode before a pending future loss makes local density deficient again
- **THEN** that later occurrence starts a new delayed episode, with identical outcomes under equal interval partitioning

#### Scenario: Site recovery cannot affect earlier waves
- **WHEN** a zone has a wave due110 and an overlapping site's recovery is due140 during [100,160]
- **THEN** births and due state equal settlement through [100,125] then [125,160], and the140 site members do not occupy the110 headroom

#### Scenario: Actual movement preserves both budgets
- **WHEN** living home owners depart repeatedly or wait in transit while a foreign visitor enters their zone
- **THEN** each still consumes its own home ceiling once, the visitor consumes local headroom, and movement gives no defeat/site-clear credit or unlimited replacements

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

### Requirement: Boundary zone passes read shared population facts once per pass
A boundary zone pass over many ecology zones SHALL decode the per-zone state record once and scan presence facts once for the whole pass. Each zone SHALL receive the same counts and state fields that its single-zone read gives. Recovery settlement SHALL visit only the zones whose recovery is due at the boundary tick.

#### Scenario: Note pass over many zones
- **WHEN** one settled boundary notes six initialized zones from one presence mapping
- **THEN** the state record is decoded once, the presence mapping is iterated once, and every zone's recovery-due and settled-through fields equal the result of noting that zone alone

#### Scenario: Batch counts equal single-zone counts
- **WHEN** zone counts are measured for several zones from one presence mapping
- **THEN** the presence mapping is iterated once and each zone's local, home-owned and per-cell measures equal its single-zone measure

#### Scenario: Recovery visits due zones only
- **WHEN** a boundary tick finds two of six initialized zones with a recovery due at or before that tick
- **THEN** recovery settlement runs for exactly those two zones in zone-key order, and the other four zone records are unchanged

#### Scenario: Forecast zone note
- **WHEN** a forecast projection notes its zones at one projected tick
- **THEN** its presence facts are scanned once for all zones and each zone's projected recovery-due tick equals the single-zone rule
