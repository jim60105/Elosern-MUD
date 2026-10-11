## Purpose

Create immutable no-write snapshots and share complete deterministic legality with settlement. This capability defines observable behavior at the monster decision boundary.

## ADDED Requirements

### Requirement: Decision snapshots are read only and public
Snapshots SHALL contain stable identity, real execution scope, resolved context, true literal/effective traits, resources, capabilities, factions, owned skill metadata, active buff projections and settled public observations. Snapshot construction SHALL NOT create handlers or caches, regenerate gauges, update timestamps or write entity state.

#### Scenario: No create snapshot
- **WHEN** selection reads an entity with absent handlers, stale gauge timestamps and buffs
- **THEN** persistent attributes, handler attachment, gauge values and timestamps remain unchanged

#### Scenario: Public inputs only
- **WHEN** queued player requests, unresolved teammate choices or disguised stats change while settled state stays fixed
- **THEN** snapshot, scoring inputs, seed inputs and traces remain unchanged

### Requirement: Utility legality shares all deterministic settlement gates
Utility validation SHALL use the actual context, scale and submitted plan with shared ownership, active-kind, identity, lineage, proficiency, resource, capability, cast, interaction and target gates. Submission and initiative-time resolver revalidation SHALL remain authoritative.

#### Scenario: Complete cast rejection
- **WHEN** a skill passes the old preview subset but fails a real cast or interaction prerequisite
- **THEN** it is excluded before scoring with the same deterministic rejection as settlement

#### Scenario: Late state change
- **WHEN** an earlier action changes target presence, eligibility, resource or capability
- **THEN** resolver revalidation rejects the stale request without unauthorized effects or payment

### Requirement: Snapshot reads are reused within one decision
The system SHALL read registry, owned-skill metadata, costs, participant traits and buff projections once per decision and reuse these inputs across target plans. It SHALL refresh them for the next action.

#### Scenario: Query growth
- **WHEN** more target plans are enumerated on fixed actor and participant data
- **THEN** ORM queries do not grow per candidate; the next decision sees intervening HP, resource and status changes

