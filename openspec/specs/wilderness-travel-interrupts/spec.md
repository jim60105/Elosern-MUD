# wilderness-travel-interrupts Specification

## Purpose
Attach stateless commit-qualified interrupt flags to wilderness moves. This capability owns its observable mechanism and rejection boundaries.

## Requirements

### Requirement: Wilderness steps report stateless committed interrupts
Successful wilderness moves SHALL return unique interrupt flags derived from committed before/after state and optional validated walk context without storing walking state.

#### Scenario: Transition/context table
- **WHEN** synthetic snapshots independently add each landmark, lit district, source, hostile, threshold, night entry or sleeping member
- **THEN** each documented flag raises only for its positive transition/context and combined flags use stable order

#### Scenario: Identity and absent context
- **WHEN** a prospective hostile materializes while a pooled-room step has no walk context
- **THEN** stable identity avoids false hostile flags, natural flags remain and pace/night flags do not raise

### Requirement: Interrupt results respect movement failure boundaries
Interrupts SHALL accompany only committed successful steps; comparison failures log and leave successful movement intact while existing refusal results remain unchanged.

#### Scenario: Refusal and rollback
- **WHEN** an exit refuses, traversal fails or a failure occurs after observation writes inside the movement-owned transaction
- **THEN** no interrupt/success result survives and the movement owner restores durable and cached observation state

#### Scenario: Comparison failure
- **WHEN** visibility comparison throws while the actual move commits
- **THEN** travel_interrupts_failed logs, success carries empty interrupts and location/charge/committed revision remain correct

#### Scenario: Existing pace state stops consistently
- **WHEN** a legal move starts with a traveller already at or beyond the cautious or standard threshold
- **THEN** pace_threshold raises after that first step just as the paired travel plan stops there, while forced pace does not raise it

#### Scenario: External rollback cannot publish deferred success
- **WHEN** a caller-owned transaction rolls back before the adapter's commit-qualified completion
- **THEN** no interrupt success result publishes; that external owner remains responsible for its existing cached-state compensation and failure completion
