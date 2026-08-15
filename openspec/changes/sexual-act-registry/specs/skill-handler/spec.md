## ADDED Requirements

### Requirement: owned_keys() includes every unlocked sexual act, and base_owned_keys() exposes the pre-extension set
`SkillHandler` SHALL expose `base_owned_keys()`, returning exactly the entity's imported active and
passive keys plus `INNATE_SKILL_ORDER` — the same list `owned_keys()` returned before this
requirement. `owned_keys()` SHALL return `base_owned_keys()` extended with every key in
`entity.sexual.unlocked_act_keys()` (when the entity has a `sexual` attribute), sorted, appended
after the base list. `world/skills/handler.py` SHALL read the entity's sexual state through a
duck-typed `getattr(entity, "sexual", None)` and SHALL import nothing from `world.rules`, preserving
`universal-action-ownership`'s existing "world/skills/ does not depend on world/rules/" requirement.

#### Scenario: base_owned_keys() matches owned_keys()'s pre-extension behaviour exactly
- **WHEN** `base_owned_keys()` is called on any entity
- **THEN** it returns the entity's imported active and passive keys followed by `INNATE_SKILL_ORDER`,
  with no unlocked act key present

#### Scenario: owned_keys() includes unlocked sexual acts
- **WHEN** `owned_keys()` is called on an entity whose `entity.sexual.unlocked_act_keys()` returns a
  non-empty set
- **THEN** every key in that set is present in the returned list, in addition to every key
  `base_owned_keys()` would return

#### Scenario: owned_keys() equals base_owned_keys() when no act is unlocked
- **WHEN** `owned_keys()` is called on an entity whose `entity.sexual.unlocked_act_keys()` returns an
  empty set
- **THEN** the returned list equals `base_owned_keys()`'s return value exactly

#### Scenario: An entity with no sexual attribute still resolves owned_keys()
- **WHEN** `owned_keys()` is called on an entity with no `sexual` attribute at all
- **THEN** it returns `base_owned_keys()`'s value without raising

#### Scenario: world/skills/handler.py imports nothing from world.rules
- **WHEN** `world/skills/handler.py`'s import statements are inspected
- **THEN** none of them reference any `world.rules.*` module, and the sexual-state read is a
  duck-typed attribute access, not an import
