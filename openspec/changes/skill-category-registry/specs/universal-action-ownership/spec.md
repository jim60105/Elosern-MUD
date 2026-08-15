## ADDED Requirements

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
