# Spec Delta

## MODIFIED Requirements

### Requirement: The approved first-batch profiles and grades are user-approved literals
The delivered first-batch variants SHALL carry complete authored profiles and valid authored grades. These values SHALL be author-adjustable game data in the variant registry, with no duplicated approval-value table in specs or tests. Profile completeness, species/default membership, independent tier-axis membership and grade-range checks SHALL remain mandatory. MP/SP SHALL remain explicit pools without an invented tier band. Undelivered ability kits SHALL remain deferred.

#### Scenario: Benign authoring change
- **WHEN** a delivered or already-profiled first-batch variant's HP, physical axis or MP/SP changes within the established schema and tier constraints
- **THEN** content tests pass without editing expected numerical tables and a newly constructed individual uses the declaration without coefficients baked into storage

#### Scenario: Existing bounds remain authoritative
- **WHEN** a profile is partial, mistyped, negative, or outside an established tier axis or grade range
- **THEN** existing validation rejects it by variant and field, including nonzero magic under a zero magic band

#### Scenario: Live state is preserved
- **WHEN** the registry changes after an individual exists
- **THEN** reload preserves that individual's identity, owned kit and current stored traits/resources without migration or refill

### Requirement: Numeric combat profiles and danger grades are balance-gated slots, never invented values
`MonsterVariant.combat_profile` SHALL be either None or a frozen complete authored record of HP/MP/SP/atk_phys/agility/defense/magic_power. `danger_grade` SHALL be None or a valid authored guild grade. Authoring SHALL provide explicit values; narrative, display names and other variants SHALL NOT infer them. Tests SHALL validate schema and established independent tier/grade constraints without reproducing a literal approval table or forbidding an otherwise valid author edit.

#### Scenario: Incomplete or invalid profile
- **WHEN** a profile omits a field, supplies None in a populated record, a non-integer or negative value, or magic outside its declared tier band
- **THEN** registry validation raises the named error before publication

#### Scenario: None retains optional-source semantics
- **WHEN** a variant has no authored profile or grade
- **THEN** consumers treat None as absence; only individual construction may use and report its existing tier fallback, and no registry consumer substitutes inferred numbers

#### Scenario: Authored pools remain independent
- **WHEN** an author adjusts explicit MP/SP pools
- **THEN** no MP/SP tier band or narrative-derived pool is introduced, and physical/magic tier validation remains unchanged
