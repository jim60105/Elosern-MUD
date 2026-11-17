# Spec Delta

## MODIFIED Requirements

### Requirement: The synthetic test-data kit provides registry-compatible catalogs
The repository SHALL provide a shared synthetic game-data kit at
`world/tests/synthetic_data.py`: per-catalog dicts built from the real definition
dataclasses, whose keys carry the reserved `t_` prefix and whose display fields are
invented Traditional-Chinese prose that occurs nowhere in shipped data. The kit itself
and its mirrors SHALL be clean under the test-data lint gate.

#### Scenario: Kit content is gate-clean
- **WHEN** the test-data lint scanner evaluates `world/tests/synthetic_data.py` and the
  JavaScript mirror files
- **THEN** it reports zero shipped-content flags for those files

#### Scenario: Kit catalogs cover the shipped definition domains
- **WHEN** the shared kit's catalogs are inventoried
- **THEN** they cover at least items, skills, races/subraces, player presets, NPC and
  monster tiers, anchors, wilderness regions, scene archetypes,
  shops/economy, quests, titles, dialogue, buffs, and sexual acts

#### Scenario: The kit carries no unused entries
- **WHEN** the shared synthetic catalogs are audited
- **THEN** the kit only carries catalog entries that at least one test consumes

#### Scenario: Exotic shapes go through factories, not shared growth
- **WHEN** a migration change needs an exotic entity shape
- **THEN** it is added through the kit's `make_*` factories with local registration
  rather than growing shared catalogs with unused entries

#### Scenario: Kit keys cannot collide with shipped data
- **WHEN** the kit self-test compares every kit key and display label against the shipped
  catalog token universe
- **THEN** no kit key or label matches a shipped token, and the test fails the moment a
  future rename or new prose would collide

#### Scenario: Local fixture path is first-class
- **WHEN** a test needs an entity shape absent from the shared synthetic catalogs
- **THEN** it builds one with the kit's `make_*` factory and registers it for its own
  scope only, without editing the shared catalogs

