# Spec Delta

## ADDED Requirements

### Requirement: A lifecycle pass inside an advance stores each written record once
A lifecycle settlement pass run by a clock advance SHALL store the population timeline, the coordinate registration, the zone record, the site record and each body's reserve and posture at most once when the pass completes, plus once before each field contact block. Every read during the pass SHALL return the latest written value.

#### Scenario: Statements do not grow with boundary ticks
- **WHEN** one synthetic travelling group is advanced over an interval that contains two boundary ticks, and the same world over an interval that contains six
- **THEN** both advances issue the same number of update statements for the timeline row, for the coordinate row and for each member's reserve row

#### Scenario: Readers see pending values
- **WHEN** a departure inside the pass has written the coordinate registration and the timeline and nothing was stored yet
- **THEN** an ordinary attribute read of both records and a presence read at that tick return the post-departure values

#### Scenario: Contact sees stored state
- **WHEN** a field contact block starts inside a pass that has pending writes
- **THEN** every pending value is stored before the admission reads or writes anything, and writes inside the block are stored immediately

#### Scenario: Results are unchanged
- **WHEN** a synthetic world with a wandering group, a travelling group with members below full gauges, a zone below its lower density and a recoverable site is advanced over one interval and over a partition of it, once with deferred storage and once with immediate storage
- **THEN** all resulting state projections are equal, in memory and after every attribute cache was reset

### Requirement: A failed pass stores nothing it deferred
When a lifecycle settlement pass inside an advance fails, no deferred value SHALL be stored, and every deferred record SHALL read its pre-pass value in memory before the advance's own restore runs.

#### Scenario: Pending value lost before the store
- **WHEN** the cached attribute object of a pending record is replaced before the pass completes
- **THEN** the pass fails with the named lost-store error and the advance rolls back

#### Scenario: Fault after deferred writes
- **WHEN** a fault is injected at the third boundary tick of a pass that already deferred timeline, coordinate and reserve writes
- **THEN** the advance raises, no update statement for those rows was issued, and the state projection equals the pre-advance projection in memory and after every attribute cache was reset

### Requirement: Gauge regeneration stores a body's trait record once per settlement
Gauge regeneration of one body for one interval SHALL store that body's trait record at most once, with the same resulting gauge values and remainders as storing each gauge separately.

#### Scenario: Three regenerating gauges
- **WHEN** a body whose three gauges are all below maximum regenerates for one interval inside a pass
- **THEN** its trait record is written once and each gauge's current value and remainder equal the values the per-gauge writer gives for the same interval
