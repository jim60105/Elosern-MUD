# Spec Delta

## MODIFIED Requirements

### Requirement: Ambient and site placement are frozen keyed lore data validated at construction
Placement declarations SHALL publish immutable keyed ecology and manual-site data only after complete reference, geometry, composition, capacity and lifecycle validation.

#### Scenario: An unknown variant reference is rejected at import time
- **WHEN** a site or ecology zone names a variant key absent from the variant registry
- **THEN** registry construction raises a named placement-registry error and no partial registry is published

#### Scenario: Habitat-incompatible authoring fails at construction, not at runtime
- **WHEN** an authored site names a variant whose species' habitat tags do not include the site's habitat
- **THEN** placement-registry construction rejects it, and at runtime no spawn decision anywhere reads habitat tags

#### Scenario: Recovery must be expressible
- **WHEN** a site is authored as recoverable with no recovery condition, or with a free-text condition outside the closed vocabulary
- **THEN** registry construction raises the named error

#### Scenario: Ambient rules are frozen values with the authored fields
- **WHEN** an `EcologyZone` is constructed
- **THEN** it is frozen and carries the stable zone key, parent region, bounded rectangles, weighted composition pool, density values, cell/wave limits and recovery timing

#### Scenario: Sites are frozen values with the authored fields
- **WHEN** a `MonsterSite` is constructed
- **THEN** it is frozen and carries `key`, a kind from the closed vocabulary `camp | nest | boss_site | stray | encounter`, an explicit composition reference, a host anchor or coordinate, capacity, the `one_shot` flag, and — for recoverable sites — a recovery condition drawn from a closed in-game-time/approved-deterministic vocabulary

#### Scenario: An unknown region reference is rejected at construction
- **WHEN** an ecology zone names a region key absent from the region registry
- **THEN** registry construction raises the named placement-registry error and no partial registry is published

### Requirement: Every placed individual carries its owner marker and reconciliation stays inside the owner domain
Ordinary individuals SHALL retain a home ecology-zone marker separately from position, and manual individuals SHALL retain stable site ownership; each owner SHALL modify only its own lawful lifecycle state and never replace living or foreign-owned entities.

#### Scenario: Ambient cleanup leaves site-owned monsters untouched
- **WHEN** ambient reconciliation runs at a coordinate hosting a site-owned individual
- **THEN** the site-owned individual is neither deleted nor moved, and only ambient-marked individuals are reconciled

#### Scenario: Site recovery never reconciles ambient individuals
- **WHEN** a site's recovery or cleanup pass runs
- **THEN** it acts only on individuals carrying that site's marker, and ambient individuals in the same room are unchanged

#### Scenario: Quest-owned targets are foreign to both owners
- **WHEN** an individual bound to an accepted quest record stands inside a site's footprint and either owner reconciles
- **THEN** the quest-bound individual is untouched by both reconciliation passes

#### Scenario: All foreign owners are protected
- **WHEN** either reconciliation pass encounters an individual owned by a quest, story, combat session, or another site
- **THEN** that individual is not deleted, moved, replaced, or modified

#### Scenario: Ambient maintenance never stands in for site lifecycle
- **WHEN** ambient maintenance runs
- **THEN** it never resumes, respawns, clears, or otherwise stands in for a site's lifecycle

## REMOVED Requirements

### Requirement: Placement honors capacity and determinism
**Reason**: Coordinate-hash fixed species and quantity maintenance are replaced by saved occurrence-seeded complete compositions.

**Migration**: Cut all callers and substantively matching test annotations to the replacement contract using tool-generated canonical IDs; retain no legacy behavior, alias or data migration.

## ADDED Requirements

### Requirement: Placement samples complete deterministic occurrences
Manual site population SHALL sample complete authored compositions within site capacity using saved deterministic occurrence state, while ordinary births SHALL obey the regional population contract.

#### Scenario: Capacity is a ceiling, not a reshuffle
- **WHEN** a site already holds its complete living composition of living individuals
- **THEN** reconciliation creates nothing and deletes nothing to "swap" individuals

#### Scenario: Same saved occurrence, same composition
- **WHEN** site selection is evaluated twice for the same saved occurrence
- **THEN** the same full composition is selected both times across restarts without unrecorded randomness

#### Scenario: Selection stays inside the authored variant set
- **WHEN** site population creates an individual
- **THEN** the individual's species/variant is one of its explicitly referenced composition variants

#### Scenario: Selection uses persisted occurrence inputs
- **WHEN** site selection is evaluated
- **THEN** it uses saved seed and sequence with distinct draw purposes, never coordinate-slot identity or global randomness

#### Scenario: Manual exceptions
- **WHEN** a valid explicit site inside a settlement birth buffer or above ordinary cell/zone density matures
- **THEN** its complete lawful composition can be placed and ordinary maintenance neither culls it nor early-recovers any site

#### Scenario: Missing presence is not clearing
- **WHEN** a site-owned living member is temporarily absent from its original cell
- **THEN** ownership and member identity remain; the site does not clear or create replacements

