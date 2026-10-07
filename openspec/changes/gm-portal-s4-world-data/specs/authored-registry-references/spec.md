## Purpose

Expose an explicit inventory of authored registries and declared bidirectional references without changing authored entry semantics or startup behavior.

## ADDED Requirements

### Requirement: Explicit complete lazy registry inventory
The inventory SHALL use unique snake_case registry names, Traditional Chinese labels, one of the eight approved groups (world, creatures, items/economy, settlements, people, skills, quests, rulebooks), repository-relative source paths, optional summary fields, and lazy loaders returning mappings of keys to frozen dataclass entries. Inventory coverage SHALL include all 21 startup-sync registries plus items, NPC profiles, dialogue rows, assortments, player presets, starting kits, NPC tiers, scene archetypes, skills, sexual acts, quest definitions, and keyed rulebook professions, guild exam profiles, shop configs, service host rows, and monster behaviour profiles. Parameter-only rulebooks SHALL be source-viewer-only. Importing the inventory SHALL NOT eagerly import rules, skills, or quests, and SHALL NOT change startup synchronization.

#### Scenario: Complete inventory contract
- **WHEN** inventory contracts run against shipped data
- **THEN** names are unique, every startup-sync registry is represented, every named additional category is present, loaders yield mappings of frozen dataclass entries, and source paths and display metadata are available

#### Scenario: Lazy import boundary
- **WHEN** the inventory module is imported without invoking loaders
- **THEN** rules, skills, and quest packages are not imported by that module and startup synchronization remains unchanged

### Requirement: Declarative reference traversal
Single-key references SHALL support nullable None only when declared nullable; many-key references SHALL support tuple, list, and frozenset values. References SHALL declare a target registry and named inverse on the referencing dataclass field, including nested dataclasses within entries. Declarations SHALL NOT change field types, defaults, or values. The first batch SHALL cover useful direct-key references in monster species, variants, sites, ambient placements, quest definitions, items, places, settlements, shops, and NPC profiles. Other inventory entries SHALL remain browsable without declared links; composite or parsed/prefixed references SHALL NOT be inferred.

#### Scenario: Nested single and many references
- **WHEN** synthetic entries contain single, nullable, many, and nested references
- **THEN** traversal yields their target keys and complete field paths, skips nullable None, and preserves every input value

#### Scenario: First-batch semantics preserved
- **WHEN** first-batch declarations are added to existing dataclasses
- **THEN** entries retain their field types/defaults/values and only declared direct-key fields produce references

### Requirement: Cached bidirectional integrity model
The reference model SHALL expose forward references by source field and referrers grouped by the declaration's inverse name, cached for the process lifetime because registries are immutable. Integrity checking SHALL report every dangling target as registry, key, field_path, target_registry, and missing_key. Every declaration SHALL name an indexed registry; distinct reference declarations into the same target registry SHALL have distinct inverse names. Repeated instances of one declaration SHALL NOT constitute inverse-name collisions. Shipped-data checks SHALL produce no dangling references; any first-batch dangling data SHALL be corrected before acceptance. These checks SHALL be CI contracts, not new startup enforcement.

#### Scenario: Bidirectional and cached results
- **WHEN** references from nested and repeated synthetic entries are indexed twice
- **THEN** forward and inverse maps agree, each referrer is attributable to its source and field path, and immutable results are reused without rescanning

#### Scenario: Invalid declarations and missing keys
- **WHEN** fixtures declare an absent target registry, duplicate inverse declarations into one target, or missing target keys
- **THEN** contracts reject invalid declarations and integrity diagnostics identify every missing key with the required five fields

#### Scenario: Shipped reference acceptance
- **WHEN** all first-batch shipped references are checked in CI
- **THEN** the dangling list is empty and no new startup validation hook is required
