# Spec Delta

## MODIFIED Requirements

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
- **THEN** coverage includes all 21 startup-sync registries plus items, NPC profiles, dialogue rows, assortments, player presets, starting kits, NPC tiers, scene archetypes, skills, sexual acts, quest definitions, and keyed guild exam profiles, shop configs, service host rows, and monster behaviour profiles

#### Scenario: Parameter-only rulebooks are source-viewer-only
- **WHEN** a parameter-only rulebook appears in the inventory
- **THEN** it is exposed as source-viewer-only
