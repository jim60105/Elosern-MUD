# entity-sex-vocabulary delta

## MODIFIED Requirements

### Requirement: The module documents itself as the single canonical source for this vocabulary
`world/lore/sex.py`'s module docstring SHALL state that it is the single source for `SEX_VALUES` and
`DEFAULT_SEX`, and SHALL name `CHARACTER_SCHEMA_V1`, `LivingEntity.sex`, and `PlayerPreset.sex` as
its current consumers.

#### Scenario: The module docstring names its consumers
- **WHEN** `world/lore/sex.py`'s module docstring is inspected
- **THEN** it names `CHARACTER_SCHEMA_V1` (import validation), `LivingEntity.sex` (the typeclass
  attribute default), and `PlayerPreset.sex` (the player preset registry) as consumers of these
  constants
