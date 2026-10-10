# Spec Delta

## MODIFIED Requirements

### Requirement: The approved first-batch profiles and grades are user-approved literals
All twelve currently shipped first-batch variants SHALL retain complete authored profiles and valid authored grades, with no None slots. Values SHALL be adjustable data, without a duplicate approval table. Completeness, identity/default membership, independent tier-axis/grade-range checks and explicit MP/SP pools SHALL remain. Six delivered ability kits remain delivered; undelivered hare/goat/lynx ability kits remain deferred independently of their already-shipped profiles.

#### Scenario: Benign authoring change
- **WHEN** a delivered or already-profiled first-batch variant's HP, physical axis or MP/SP changes within the established schema and tier constraints
- **THEN** content tests pass without editing expected numerical tables and a newly constructed individual uses the declaration without coefficients baked into storage

#### Scenario: Existing bounds remain authoritative
- **WHEN** a profile is partial, mistyped, negative, or outside an established tier axis or grade range
- **THEN** existing validation rejects it by variant and field, including nonzero magic under a zero magic band

#### Scenario: Live state is preserved
- **WHEN** the registry changes after an individual exists
- **THEN** reload preserves that individual's identity, owned kit and current stored traits/resources without migration or refill

#### Scenario: New instance
- **WHEN** a registered variant constructs a new monster
- **THEN** its current authored profile is authoritative without skill/gear multipliers baked into storage

#### Scenario: Every shipped batch variant carries its approved values
- **WHEN** all twelve first-batch profiles and grades are inspected
- **THEN** all seven fields and a valid grade are present with no None slots; authored values, not an approval mirror, govern

#### Scenario: Approval does not extend to unapproved content
- **WHEN** an undelivered ability kit or profile outside the required first-batch set is inspected
- **THEN** no inference from this batch grants that kit; any explicitly authored optional profile follows the same schema without a historical numerical approval fence

#### Scenario: The approved profile table is pinned verbatim
- **WHEN** authored first-batch profiles are checked
- **THEN** the historical numerical approval table is removed, not moved; completeness and current declared bounds remain independently checked for all twelve

#### Scenario: Zero pools and retained identities survive the batch
- **WHEN** current first-batch declarations are validated
- **THEN** zero remains a valid explicitly authored pool rather than inferred absence; magic remains zero under existing tier magic bands, and all species/variant identities and authored grade validity remain
- **AND** only the six delivered kits are present; tide_devouring_bite, grain_shaking_peck and lamp_carapace_claw retain their existing ownership and effect intent

#### Scenario: The approved literals retire attrition without changing character
- **WHEN** valid authored profiles are revised
- **THEN** the existing cat mobility, crocodile endurance and crab defensive content intent stays reflected in independent axes and ecology; no old-versus-new numerical table or new universal encounter band is imposed

#### Scenario: Crocodile resource values replace only their previous zero pools
- **WHEN** crocodile profiles are authored or consumed
- **THEN** explicit MP/SP pools and complete profile/grade are retained without a 140/30/40 or 210/50/60 approval mirror; kit/binding/effect mechanics remain unchanged

#### Scenario: Approved delivered resource rows are literal
- **WHEN** both delivered variants per crocodile, sparrow and crab species are constructed
- **THEN** their current complete authored profile/grade and defined owned kit are used; the other six required profiles remain complete while their ability kits remain deferred

### Requirement: Numeric combat profiles and danger grades are balance-gated slots, never invented values
`MonsterVariant.combat_profile` SHALL be either None or a frozen complete authored record of HP/MP/SP/atk_phys/agility/defense/magic_power. `danger_grade` SHALL be None or a valid authored guild grade. Authoring SHALL provide explicit values; narrative, display names and other variants SHALL NOT infer them. Tests SHALL validate schema and established independent tier/grade constraints without reproducing a literal approval table or forbidding an otherwise valid author edit.

#### Scenario: Incomplete or invalid profile
- **WHEN** a profile omits a field, supplies None in a populated record, a non-integer or negative value, or magic outside its declared tier band
- **THEN** registry validation raises the named error before publication

#### Scenario: None retains optional-source semantics outside the required profiled set
- **WHEN** a variant outside the twelve required first-batch profiles has no authored profile or grade
- **THEN** consumers treat None as absence; only individual construction may use and report its existing tier fallback, and no registry consumer substitutes inferred numbers

#### Scenario: Authored pools remain independent
- **WHEN** an author adjusts explicit MP/SP pools
- **THEN** no MP/SP tier band or narrative-derived pool is introduced, and physical/magic tier validation remains unchanged

#### Scenario: A partial numeric profile is rejected
- **WHEN** one of seven fields is absent or None inside a populated profile
- **THEN** named registry validation rejects before publication

#### Scenario: Flavour never becomes a number
- **WHEN** narrative mentions magical/elemental behavior
- **THEN** magic/MP/SP remain explicit declarations rather than inferred values, with existing zero magic bands enforced

#### Scenario: Balance approval populates the same slot
- **WHEN** an author supplies a valid complete profile and grade
- **THEN** the same record shape validates and becomes the single source consumers read

#### Scenario: An unapproved slot still means "no approved profile"
- **WHEN** an optional future variant outside the required twelve lacks a profile or grade
- **THEN** None means absence, never zero, without requiring a duplicate approval record

#### Scenario: An approved value is never re-derived at the registry
- **WHEN** a consumer reads an explicit authored profile
- **THEN** it never derives replacement values from names, other fields or tier ranges; otherwise valid author edits remain permitted

#### Scenario: MP and SP pools are gated by approval, not inference
- **WHEN** an author declares MP/SP pools
- **THEN** they are explicit valid integer data with no invented tier band or narrative inference; no historical approval table pins their magnitudes

#### Scenario: Only explicit user balance approval populates a slot
- **WHEN** a profile or grade is populated
- **THEN** an explicit author declaration is required, not inferred/interpolated consumer data; valid author retuning does not require changing a duplicate test approval

#### Scenario: Granted approval ships both profile and grade
- **WHEN** a required first-batch profile is published
- **THEN** both its complete authored record and valid guild danger grade are present

#### Scenario: A None slot means no approved profile exists
- **WHEN** an optional future variant has a None slot
- **THEN** no consumer treats absence as zero, invented flavor data or a populated tier-band profile

#### Scenario: The interim fallback is owned by individual construction
- **WHEN** such an absent profile needs numeric construction
- **THEN** only the existing named individual-construction tier fallback provides and records the source; the registry slot itself stays absent
