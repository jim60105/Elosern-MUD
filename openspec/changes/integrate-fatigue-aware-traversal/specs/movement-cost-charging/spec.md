# Spec Delta

## ADDED Requirements

### Requirement: Traversal integrates fatigue over remaining distance
Traversal SHALL consume the external fatigue owner’s prediction and settlement semantics, recomputing the slowest sustainable speed at each member threshold or terrain boundary. Only remaining distance SHALL use a changed speed; rounding and fractional mental state SHALL agree with accepted settlement.

#### Scenario: Threshold within an edge
- **WHEN** synthetic external physiology permits 1.25m/s for 40s then half speed on a 100m edge
- **THEN** first 50m costs 40s and remaining 50m costs 80s, totaling 120s, rather than 80s or 160s.

#### Scenario: Limiting member changes
- **WHEN** an initially faster member crosses a threshold before the initial slowest member
- **THEN** remaining distance uses the newly limiting member; processing is per authored leg/event boundary, never per meter or second.

#### Scenario: Fractional prediction agreement
- **WHEN** two short accepted traversals and a subsecond rounding boundary are predicted and committed
- **THEN** external fractional mental remainder is preserved and prediction uses the same final integer elapsed-time semantics as settlement.

### Requirement: Sparse edge admission refuses pre-destination depletion
Every exit lineage SHALL reject departure before writes if any intended present traveller is forced sleeping or predicted to exhaust mental reserve before the next named destination. Exactly zero at arrival SHALL be permitted, followed by the external forced-sleep consequence at that destination.

#### Scenario: Exhaustion before destination
- **WHEN** piecewise prediction exhausts any member at 90m of a 100m edge although initial-speed estimation appeared sufficient
- **THEN** departure refuses with a clear reason; clock, location, mental remainder, knowledge, owning effects and wilderness materialization remain unchanged; no unnamed partial room or automatic rest is created.

#### Scenario: Exact-zero destination
- **WHEN** reserve reaches zero exactly at the destination under shared rounded-time semantics
- **THEN** full accepted traversal commits and external forced sleep applies there; next departure refuses.

#### Scenario: Possession and every lineage
- **WHEN** a source-present follower or possessed commander body is forced sleeping
- **THEN** plain exit, costed grid exit, both gate directions and ordinary wilderness movement all refuse before relocation or flight-waiver early return; a remote sleeping member does not block travel.

