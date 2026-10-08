# authored-registry-references Specification

## Purpose
Expose an explicit inventory of authored registries and declared bidirectional references without changing authored entry semantics or startup behavior.

## Requirements

### Requirement: Explicit complete lazy registry inventory
The inventory SHALL use unique snake_case registry names, Traditional Chinese labels, one of the eight approved groups (world, creatures, items/economy, settlements, people, skills, quests, rulebooks), repository-relative source paths, optional summary fields, and lazy loaders returning mappings of keys to frozen dataclass entries.

#### Scenario: Complete inventory contract
- **WHEN** inventory contracts run against shipped data
- **THEN** names are unique, every startup-sync registry is represented, every named additional category is present, loaders yield mappings of frozen dataclass entries, and source paths and display metadata are available

#### Scenario: Lazy import boundary
- **WHEN** the inventory module is imported without invoking loaders
- **THEN** rules, skills, and quest packages are not imported by that module and startup synchronization remains unchanged

#### Scenario: Full inventory coverage
- **WHEN** the inventory is enumerated
- **THEN** coverage includes all 21 startup-sync registries plus items, NPC profiles, dialogue rows, assortments, player presets, starting kits, NPC tiers, scene archetypes, skills, sexual acts, quest definitions, and keyed rulebook professions, guild exam profiles, shop configs, service host rows, and monster behaviour profiles

#### Scenario: Parameter-only rulebooks are source-viewer-only
- **WHEN** a parameter-only rulebook appears in the inventory
- **THEN** it is exposed as source-viewer-only

### Requirement: Declarative reference traversal
Single-key references SHALL support nullable None only when declared nullable; many-key references SHALL support tuple, list, and frozenset values. References SHALL declare a target registry and named inverse on the referencing dataclass field, including nested dataclasses within entries. Declarations SHALL NOT change field types, defaults, or values.

#### Scenario: Nested single and many references
- **WHEN** synthetic entries contain single, nullable, many, and nested references
- **THEN** traversal yields their target keys and complete field paths, skips nullable None, and preserves every input value

#### Scenario: First-batch semantics preserved
- **WHEN** first-batch declarations are added to existing dataclasses
- **THEN** entries retain their field types/defaults/values and only declared direct-key fields produce references

#### Scenario: First-batch reference coverage
- **WHEN** the first batch of reference declarations lands
- **THEN** it covers useful direct-key references in monster species, variants, sites, ambient placements, quest definitions, items, places, settlements, shops, and NPC profiles

#### Scenario: Undeclared and non-simple references are not inferred
- **WHEN** inventory entries carry no declared links, or carry composite or parsed/prefixed references
- **THEN** those entries remain browsable without declared links and such references are not inferred

### Requirement: Cached bidirectional integrity model
The reference model SHALL expose forward references by source field and referrers grouped by the declaration's inverse name, cached for the process lifetime because registries are immutable. Integrity checking SHALL report every dangling target as registry, key, field_path, target_registry, and missing_key.

#### Scenario: Bidirectional and cached results
- **WHEN** references from nested and repeated synthetic entries are indexed twice
- **THEN** forward and inverse maps agree, each referrer is attributable to its source and field path, and immutable results are reused without rescanning

#### Scenario: Invalid declarations and missing keys
- **WHEN** fixtures declare an absent target registry, duplicate inverse declarations into one target, or missing target keys
- **THEN** contracts reject invalid declarations and integrity diagnostics identify every missing key with the required five fields

#### Scenario: Shipped reference acceptance
- **WHEN** all first-batch shipped references are checked in CI
- **THEN** the dangling list is empty and no new startup validation hook is required

#### Scenario: Declaration validity rules
- **WHEN** reference declarations are registered
- **THEN** every declaration names an indexed registry, distinct reference declarations into the same target registry have distinct inverse names, and repeated instances of one declaration do not constitute inverse-name collisions

#### Scenario: Shipped data corrected before acceptance
- **WHEN** shipped data is checked for dangling references
- **THEN** the checks produce no dangling references, and any first-batch dangling data is corrected before acceptance

#### Scenario: Checks are CI contracts only
- **WHEN** the integrity checks run
- **THEN** they act as CI contracts and no new startup enforcement is added
