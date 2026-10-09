# npc-service-availability Specification

## Purpose
Define expose read-only planned service-capable npc presence intervals as observable deterministic behavior with explicit rejection and acceptance boundaries.

## Requirements

### Requirement: Planned service intervals use authoritative schedule occurrences without mutation
The reader SHALL consume selected persistent NPC, destination and current tick, reuse parsed schedules/occurrence arithmetic, and return the next planned service-capable [start_tick,end_tick) interval or a named unavailable result. Projection SHALL begin at actual location/state, honor effective-from and same-tick entry index ordering, and apply service blocking states. Search SHALL be bounded to remaining current cycle plus one complete future cycle.

#### Scenario: Busy arrival
- **WHEN** arrival at the guild is followed at the same tick by busy, then available
- **THEN** the interval starts at the available transition, not at arrival

#### Scenario: Read-only snapshot
- **WHEN** the reader handles a valid absent-host request
- **THEN** clock, NPC attributes/location, resources, affinity and exam records are unchanged

#### Scenario: Missed arrival
- **WHEN** an earlier planned arrival was skipped and the host remains absent
- **THEN** no remaining current interval is claimed as presence; future arrival or unavailable is returned

### Requirement: Indeterminate attendance never fabricates a timetable or reveals private routes
Missing/malformed schedules, clock or destination, unresolved movement, indeterminate hold and silenced schedule SHALL yield explicit named inability to confirm. Arrival due now SHALL remain planned until actual location confirms it. Only guild attendance SHALL be exposed; no schedule assignment, clock creation, movement or private route output SHALL occur.

#### Scenario: Missing clock
- **WHEN** no authoritative clock exists
- **THEN** a named unavailable result returns without clock creation

#### Scenario: Held or silenced host
- **WHEN** authoritative release cannot be determined or schedule is silenced
- **THEN** no fabricated interval returns

#### Scenario: Boundary
- **WHEN** tick equals a service interval end
- **THEN** that interval is no longer usable
