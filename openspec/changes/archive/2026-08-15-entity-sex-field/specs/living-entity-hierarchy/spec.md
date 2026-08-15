## ADDED Requirements

### Requirement: LivingEntity carries sex as a bounded-vocabulary attribute, defaulting to other
`LivingEntity` SHALL declare `sex: str`, defaulting to `world.lore.sex.DEFAULT_SEX` (`"other"`), read
from `world.lore.sex.SEX_VALUES` — a flat, dependency-free vocabulary, not a keyed registry like
`RACE_REGISTRY`/`SUBRACE_REGISTRY`. Unlike `race`/`subrace` (which default to `None` because their
registries have no "unspecified" member), `sex` defaults directly to the string `"other"`, because
`SEX_VALUES` already contains an explicit unspecified/non-binary member and a second null state
would be redundant.

#### Scenario: sex defaults to other on a freshly created entity
- **WHEN** a freshly created `LivingEntity` (or any subclass) is inspected before any sex is set
- **THEN** `entity.sex` equals `"other"`

#### Scenario: A Monster reads the default with no special-case code
- **WHEN** a `Monster` instance is constructed with no import record (the only construction path
  available today, since no bestiary/spawn system exists)
- **THEN** `entity.sex` equals `"other"`, with no `Monster`-specific override anywhere in this
  mechanism

#### Scenario: sex is never None
- **WHEN** `entity.sex`'s declared type is inspected
- **THEN** it is `str`, not `str | None`, distinguishing it from `race`/`subrace`'s declared type
