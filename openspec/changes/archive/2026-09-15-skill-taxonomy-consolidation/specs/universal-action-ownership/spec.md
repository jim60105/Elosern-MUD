## MODIFIED Requirements

### Requirement: flee declares its skill category at its own construction site
`world/rules/disengage.py`'s direct `SkillDef(...)` construction for `flee` SHALL declare
`category=SkillCategory.MARTIAL_ARTS` (re-homed from the retired `MOVEMENT` branch by the Phase B
taxonomy consolidation, pairing `flee` with its `INNATE_SKILL_KEYS` sibling `basic_attack`). This
classification SHALL be supplied at `flee`'s own construction site, not inferred or special-cased
elsewhere, consistent with this capability's existing requirement that `world/skills/` never import
from `world/rules/`.

#### Scenario: flee is classified MOVEMENT
- **WHEN** `SKILL_REGISTRY["flee"]` is inspected after `world.rules.disengage` has been imported
- **THEN** its `category` is `SkillCategory.MARTIAL_ARTS` (re-homed from the retired `MOVEMENT`
  branch by the Phase B taxonomy consolidation; the scenario name predates the re-homing) and its
  `group` is `None`

#### Scenario: disengage.py fails to import without an explicit category
- **WHEN** `world/rules/disengage.py`'s `SkillDef(...)` construction for `flee` is inspected
- **THEN** it supplies an explicit `category` argument, because `SkillDef.category` has no default and omitting it raises `TypeError` at import time
