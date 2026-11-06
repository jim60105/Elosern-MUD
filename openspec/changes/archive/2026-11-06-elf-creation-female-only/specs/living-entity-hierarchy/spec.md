## MODIFIED Requirements

### Requirement: LivingEntity carries sex as a bounded-vocabulary attribute, defaulting to other
`LivingEntity` SHALL declare `sex: str`, defaulting to `world.lore.sex.DEFAULT_SEX` (`"other"`), read
from `world.lore.sex.SEX_VALUES` — a flat, dependency-free vocabulary, not a keyed registry like
`RACE_REGISTRY`/`SUBRACE_REGISTRY`. Every creation path SHALL resolve the persisted value through
the single deterministic `world.rules.identity` seam, and a race declaring exactly one permitted
sex SHALL resolve to that member when no sex is declared.

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

#### Scenario: The direct "other" default is deliberate against the race/subrace pattern
- **WHEN** `sex`'s default is compared with `race`/`subrace`'s `None` defaults
- **THEN** `race`/`subrace` default to `None` because their registries have no "unspecified" member, while `sex` defaults directly to the string `"other"` because `SEX_VALUES` already contains an explicit unspecified/non-binary member and a second null state would be redundant

#### Scenario: A race declaring one permitted sex resolves to that member
- **WHEN** an NPC is created with no declared sex on a path that supplies none — a quest scene occupant, a published-encounter role, or a dream/scenario-director-generated scene character — for a race whose registry entry declares exactly one permitted sex
- **THEN** the seam writes that single permitted member, so the entity never keeps the vocabulary default and the world's canon admits no such character in the other sexes

#### Scenario: A declared sex outside the race's set is refused before the write
- **WHEN** any creation path declares a `SEX_VALUES` member the entity's race does not permit
- **THEN** the seam raises before assigning the attribute, so no path can persist that combination, while a declaration the race permits is written unchanged

#### Scenario: Races permitting the declared value are untouched
- **WHEN** a human or beastfolk NPC is created with `sex="male"`, `"female"`, or `"other"`
- **THEN** the seam writes that exact member, and an omitted sex on those races still resolves to `DEFAULT_SEX`

#### Scenario: The generative blueprint stays sex-less
- **WHEN** the scenario-director blueprint and its published scene packages are inspected
- **THEN** they declare no sex for any role, because `world/ai/` never writes state: the deterministic instantiator supplies the sex from the role's race, and the blueprint cannot propose one

#### Scenario: One seam owns the write for every creation path
- **WHEN** the production modules are inspected
- **THEN** no module outside `world/rules/identity.py` assigns an entity's `sex` attribute, and the import loader, the place-host sync, the shared scene/encounter spawn, the starting-companion builder, and the player creation preflight all resolve through that seam — so a new creation path cannot silently bypass the rule

#### Scenario: The NPC authoring guide states how each path resolves sex
- **WHEN** `docs/development/adding-npcs.md` is read
- **THEN** its creation-path table and mechanism paragraph state that every path resolves the sex through the seam, and its NPC card rules state what an elf card must declare and what an author sees when they write a non-female sex for an elf
