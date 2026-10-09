# Spec Delta

## Purpose

Defines shared identity qualification for character and monster skills so authors and runtime consumers apply the same deterministic restrictions without altering acquisition.

## ADDED Requirements

### Requirement: Identity restrictions are immutable closed declarative data
Skills SHALL support allowed actor kinds, registered races, subraces, monster species and required race capabilities. Omitted restrictions add no requirement; an allowed list accepts any member and distinct restrictions combine with AND. Explicit empty lists, unknown identifiers, unsupported capabilities and contradictory identities SHALL fail registry validation.

#### Scenario: Lists combine by declared semantics
- **WHEN** a synthetic skill declares two allowed races and a required capability
- **THEN** either race passes only if its profile supplies that capability; omitted restrictions remain unrestricted

#### Scenario: Invalid authoring fails before play
- **WHEN** a declaration has an empty list, unknown kind/race/subrace/species/capability or no satisfiable actor/identity combination
- **THEN** registry validation rejects it before any invocation

#### Scenario: Parent consistency is authored
- **WHEN** both allowed races and subraces are declared
- **THEN** each allowed subrace belongs to an allowed race or authoring fails

### Requirement: Stored identity determines actor qualification
One pure identity query SHALL serve authored records and runtime entities. Runtime actor kind SHALL derive from deterministic typeclass identity; character subrace gates SHALL validate the stored race/subrace parent pair. Species gates SHALL validate stored species/variant membership. Monsters SHALL remain species identities without artificial races or variant-specific gates.

#### Scenario: Character identity matrix
- **WHEN** synthetic player and NPC identities exercise race-only and subrace gates with absent keys, wrong parents and valid pairs
- **THEN** valid identities pass the declared restrictions and missing or mismatched restricted identities fail

#### Scenario: Monster identity matrix
- **WHEN** synthetic monsters exercise monster-only and species gates with valid, unknown, absent and cross-species variant pairs
- **THEN** monster-only permits monsters without a species gate; species-restricted use requires a valid matching pair

#### Scenario: Incidental attributes grant no actor kind
- **WHEN** a monster carries a character-like race attribute or a character carries species-looking attributes
- **THEN** typeclass identity still determines actor kind and cannot be spoofed by those attributes

#### Scenario: Record queries create nothing
- **WHEN** a validator supplies authored actor kind and identity to the same qualification contract
- **THEN** it obtains the runtime-equivalent result without constructing an entity or mutating state

### Requirement: Qualification does not grant ownership or replace action validation
Identity qualification SHALL supplement ownership, restrictions and prerequisite proficiency. Rejection SHALL occur before dice, resource costs, effects or practice. Passive reads, imports, authored kits and grant paths SHALL enforce the same identity contract; category/group SHALL remain presentation taxonomy.

#### Scenario: Eligibility is not acquisition
- **WHEN** an eligible character or monster lacks an otherwise usable synthetic skill
- **THEN** use remains denied, while an eligible owner of an unrestricted existing skill retains use

#### Scenario: Ineligible root rejects safely
- **WHEN** an actor owns an ineligible prerequisite-free active skill
- **THEN** resolver, preview and revalidation report an identity failure without dereferencing a missing prerequisite; no rolls or writes occur

#### Scenario: Passive and grant containment
- **WHEN** misconfigured ownership or a conferred grant references an identity-ineligible passive
- **THEN** its trait multiplier, rule-table adjustment, movement waiver and other passive reads contribute no effect; a new ineligible grant is rejected

#### Scenario: Import containment
- **WHEN** skills or passives in an authored character record or preset kit fail identity qualification
- **THEN** validation names the field and skill and rejects before persistence, including closure-added prerequisite keys

### Requirement: Divine skill marker is removed by a complete cutover
Divine skills SHALL require the race capability backed by the existing race-profile divine authority. The old skill marker, independent gate, builder arguments and compatibility aliases SHALL be removed. Divine acquisition exclusions and category-specific practice SHALL remain unchanged.

#### Scenario: Capability authority remains data driven
- **WHEN** synthetic race profiles change divine capability independently of their names
- **THEN** eligibility follows the capability rather than an elf-name check; shipped capability values remain unchanged

#### Scenario: Acquisition remains separate
- **WHEN** an actor of any eligible race holds sexual mastery but does not own a divine act
- **THEN** the blanket still excludes all divine-capability acts and ownership-gated rows; eligibility alone acquires nothing

#### Scenario: Cadence remains category scoped
- **WHEN** owned eligible divine-mystery and divine-capability sexual-act skills resolve repeatedly
- **THEN** the mystery retains daily practice claims and rollback while sexual acts keep their existing per-tick cadence

#### Scenario: No parallel gate remains
- **WHEN** production definitions, consumers, builders and affected fixtures are inspected after cutover
- **THEN** no old divine skill field, alias or independent marker path remains

### Requirement: Player catalogs and lineage use identity filtering
Player catalog and lineage projections SHALL exclude identity-ineligible skills and chain entries from display and counts using the pure identity query. Identity-eligible racial character abilities SHALL remain discoverable regardless of ownership or current resources. Isolated prerequisite-free abilities SHALL create no lineage tree.

#### Scenario: Monster content stays private to its actors
- **WHEN** synthetic monster-only roots, children and an isolated ability coexist with racial character abilities
- **THEN** player catalogs and lineage counts include only identity-eligible entries; the isolated ability starts no chain

#### Scenario: Proficiency and resources are separate
- **WHEN** a character qualifies by identity but lacks ownership, proficiency or MP for a catalog entry
- **THEN** the entry may remain visible with its existing usability status; filtering does not duplicate resource or progression checks

