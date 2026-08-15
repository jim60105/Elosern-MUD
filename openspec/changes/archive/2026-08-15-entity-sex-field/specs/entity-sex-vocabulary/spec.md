## ADDED Requirements

### Requirement: world/lore/sex.py defines the canonical sex vocabulary and its default
`world/lore/sex.py` SHALL define `SEX_VALUES: tuple[str, ...]` equal to exactly
`("female", "male", "other")` and `DEFAULT_SEX: str` equal to `"other"`. This module SHALL contain
no behavior, no state transitions, and no dependency on any `world/rules/` or `world/imports/`
module, matching `world/lore/sexual_vocab.py`'s existing precedent for a single-owner,
dependency-free vocabulary module.

#### Scenario: SEX_VALUES contains exactly the three documented members in order
- **WHEN** `SEX_VALUES` is inspected
- **THEN** it equals `("female", "male", "other")`, in that exact order

#### Scenario: DEFAULT_SEX is the unspecified member of SEX_VALUES
- **WHEN** `DEFAULT_SEX` is inspected
- **THEN** it equals `"other"`, and `"other"` is a member of `SEX_VALUES`

#### Scenario: The module has no import of a rules or imports module
- **WHEN** `world/lore/sex.py`'s own imports are inspected
- **THEN** it imports nothing from `world.rules` or `world.imports`

### Requirement: The module documents itself as the single canonical source for this vocabulary
`world/lore/sex.py`'s module docstring SHALL state that it is the single source for `SEX_VALUES` and
`DEFAULT_SEX`, and SHALL name `CHARACTER_SCHEMA_V1` and `LivingEntity.sex` as its current consumers.

#### Scenario: The module docstring names its consumers
- **WHEN** `world/lore/sex.py`'s module docstring is inspected
- **THEN** it names `CHARACTER_SCHEMA_V1` (import validation) and `LivingEntity.sex` (the typeclass
  attribute default) as consumers of these constants
