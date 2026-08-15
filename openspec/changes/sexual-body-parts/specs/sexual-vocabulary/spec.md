## MODIFIED Requirements

### Requirement: world/lore/sexual_vocab.py defines the sexual-state vocabularies SexualState is built from
`world/lore/sexual_vocab.py` SHALL define six module-level tuples of Traditional Chinese level
names, ordered from lowest to highest intensity, matching design doc §6.4 exactly:
`AROUSAL_LEVELS`, `WETNESS_LEVELS`, `SHAME_LEVELS`, `EXPOSURE_LEVELS`, `CLIMAX_PHASE_LEVELS`, and
`SENSITIVITY_LEVELS`. It SHALL additionally define `BODY_PARTS`, a 10-member tuple of Traditional
Chinese body-part names (unordered — there is no meaningful intensity ordering among body parts),
naming the key vocabulary `SexualState.sensitivity` values are indexed by, and `GENERIC_BODY_PART`,
a single sentinel string that is not a member of `BODY_PARTS`. This module SHALL contain no
behavior, no state transitions, and no dependency on any `world/rules/` or `world/imports/` module.

#### Scenario: AROUSAL_LEVELS matches the documented ladder in order
- **WHEN** `AROUSAL_LEVELS` is inspected
- **THEN** it equals `("平靜", "微興奮", "中等", "高度", "極限")`, in that exact order

#### Scenario: WETNESS_LEVELS matches the documented ladder in order
- **WHEN** `WETNESS_LEVELS` is inspected
- **THEN** it equals `("乾燥", "微濕", "濕潤", "大量", "泛濫")`, in that exact order

#### Scenario: SHAME_LEVELS matches the documented ladder in order
- **WHEN** `SHAME_LEVELS` is inspected
- **THEN** it equals `("無", "輕微", "中等", "強烈", "成癮")`, in that exact order

#### Scenario: EXPOSURE_LEVELS matches the documented ladder in order
- **WHEN** `EXPOSURE_LEVELS` is inspected
- **THEN** it equals `("極低", "低", "中等", "高", "極高")`, in that exact order

#### Scenario: CLIMAX_PHASE_LEVELS matches the documented ladder in order
- **WHEN** `CLIMAX_PHASE_LEVELS` is inspected
- **THEN** it equals `("未達", "接近", "進行中", "餘韻")`, in that exact order

#### Scenario: SENSITIVITY_LEVELS matches the documented ladder in order
- **WHEN** `SENSITIVITY_LEVELS` is inspected
- **THEN** it equals `("普通", "高", "極高", "敏感異常")`, in that exact order

#### Scenario: BODY_PARTS matches the documented set in order
- **WHEN** `BODY_PARTS` is inspected
- **THEN** it equals `("口唇", "頸項", "耳朵", "乳房", "腰腹", "臀部", "大腿", "足部", "私處",
  "後庭")`, in that exact order, and has exactly 10 members

#### Scenario: GENERIC_BODY_PART is not a member of BODY_PARTS
- **WHEN** `GENERIC_BODY_PART` is inspected
- **THEN** it equals `"軀體"`, and `GENERIC_BODY_PART not in BODY_PARTS` holds — a structural
  guarantee, not a convention

#### Scenario: The module has no import of a rules or imports module
- **WHEN** `world/lore/sexual_vocab.py`'s own imports are inspected
- **THEN** it imports nothing from `world.rules` or `world.imports`, keeping the dependency
  direction one-way (lore is read by imports and rules, never the reverse)

### Requirement: The module documents itself as the single canonical source for every vocabulary it defines
`world/lore/sexual_vocab.py`'s module docstring SHALL state that it is the single source for these
level-name vocabularies, that `import-contract` (this change) is its first consumer of the six
ordered-level tuples, and that a future `sexual-state` change is expected to import those same
tuples rather than redefine them. It SHALL additionally state that `BODY_PARTS` and
`GENERIC_BODY_PART` have **no current consumer** in the codebase, and SHALL name the future
`sexual-act-registry` and `sexual-act-effects` capabilities as their expected first consumers,
which are expected to import these constants rather than redefine the vocabulary or invent a
per-monster-archetype body-part table.

#### Scenario: The module docstring names both the current and expected future consumer of the ordered-level tuples
- **WHEN** `world/lore/sexual_vocab.py`'s module docstring is inspected
- **THEN** it names `CHARACTER_SCHEMA_V1`/import validation as a current consumer of the six
  ordered-level tuples and states that a future ordered-level `Trait` subclass (design doc §6.4)
  should import these tuples rather than redefine the vocabulary

#### Scenario: The module docstring states BODY_PARTS and GENERIC_BODY_PART have no current consumer
- **WHEN** `world/lore/sexual_vocab.py`'s module docstring is inspected
- **THEN** it states that `BODY_PARTS` and `GENERIC_BODY_PART` have no current consumer in the
  codebase and names the future `sexual-act-registry` and `sexual-act-effects` capabilities as their
  expected first consumers
