## Purpose

Define universal skill ownership independent of imported or spawned skill data.
## Requirements
### Requirement: INNATE_SKILL_KEYS makes flee and basic_attack ownable by every LivingEntity regardless of import or spawn data
`world/skills/handler.py` SHALL declare `INNATE_SKILL_KEYS: frozenset[str]`, seeded with exactly
`{"flee", "basic_attack"}`, and `SkillHandler.owned_keys()` SHALL include every key in `INNATE_SKILL_KEYS` in its
returned list, in addition to the entity's own imported `active`/`passive` keys.
`basic_attack` SHALL be a zero-cost active SINGLE/ENEMY physical-damage skill, unusable outside
combat, and SHALL resolve through the ordinary ActionResolver path.

#### Scenario: An entity with no imported skill data still owns both innate actions
- **WHEN** `SkillHandler.owned_keys()` is called for an entity whose `entity.db.skills` is unset
  (`None`) or empty
- **THEN** the returned list contains `"flee"` and `"basic_attack"`

#### Scenario: An entity with a full imported skill list also owns both innate actions
- **WHEN** `SkillHandler.owned_keys()` is called for an entity whose `entity.db.skills` contains several
  active and passive keys imported from a character card
- **THEN** the returned list contains every imported key plus `"flee"` and `"basic_attack"`

#### Scenario: A Monster instance can fight without spawned skill data
- **WHEN** `SkillHandler.owned_keys()` is called for a `Monster` instance constructed with no
  `entity.db.skills` data at all (no bestiary/spawn system exists in this project's dependency chain)
- **THEN** it owns both innate actions and its behavior policy can select `basic_attack` against an enemy

#### Scenario: Basic attack does not bypass ActionResolver
- **WHEN** an entity invokes `basic_attack` in combat
- **THEN** ownership, target, capability, damage, EventLog, planner, and commit behavior use the same
  ActionResolver pipeline as a registered imported damage skill

### Requirement: Innate ownership is unconditional and not combat-gated
`SkillHandler.owned_keys()`'s inclusion of `INNATE_SKILL_KEYS` SHALL NOT depend on whether the entity is
currently a member of any `Battlefield`, and `world/skills/handler.py` SHALL contain no reference to
combat state anywhere in this mechanism.

#### Scenario: Innate ownership holds identically in and out of combat
- **WHEN** `SkillHandler.owned_keys()` is called for the same entity once while it is a `Battlefield`
  roster member and once while it is not
- **THEN** both calls return a list containing `"flee"`, with no difference attributable to combat
  membership

#### Scenario: No combat-state token appears in this mechanism's implementation
- **WHEN** the portion of `world/skills/handler.py` implementing `INNATE_SKILL_KEYS`/`owned_keys()` is
  inspected
- **THEN** it contains no reference to `Battlefield`, `in_combat`, or any combat-state concept

### Requirement: world/skills/ does not depend on world/rules/ to define innate ownership
`INNATE_SKILL_KEYS` SHALL be declared inside `world/skills/handler.py` itself, not imported from
`world/rules/`, preserving this project's existing dependency direction (`world/rules/` depends on
`world/skills/`, never the reverse). `world/rules/disengage.py` SHALL import `INNATE_SKILL_KEYS` from
`world.skills.handler`, not the other way around.

#### Scenario: world/skills/handler.py has no import from world/rules/
- **WHEN** `world/skills/handler.py`'s import statements are inspected
- **THEN** none of them reference `world.rules.disengage` or any other `world.rules.*` module

#### Scenario: world/rules/disengage.py reads INNATE_SKILL_KEYS from world/skills/handler.py
- **WHEN** `world/rules/disengage.py`'s import statements are inspected
- **THEN** it imports `INNATE_SKILL_KEYS` (or reads it) from `world.skills.handler`

### Requirement: flee declares its skill category at its own construction site
`world/rules/disengage.py`'s direct `SkillDef(...)` construction for `flee` SHALL declare
`category=SkillCategory.MOVEMENT`. This classification SHALL be supplied at `flee`'s own construction
site, not inferred or special-cased elsewhere, consistent with this capability's existing requirement
that `world/skills/` never import from `world/rules/`.

#### Scenario: flee is classified MOVEMENT
- **WHEN** `SKILL_REGISTRY["flee"]` is inspected after `world.rules.disengage` has been imported
- **THEN** its `category` is `SkillCategory.MOVEMENT` and its `group` is `None`

#### Scenario: disengage.py fails to import without an explicit category
- **WHEN** `world/rules/disengage.py`'s `SkillDef(...)` construction for `flee` is inspected
- **THEN** it supplies an explicit `category` argument, because `SkillDef.category` has no default and omitting it raises `TypeError` at import time

