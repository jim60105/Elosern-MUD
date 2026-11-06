## Purpose

Define the shared living-entity typeclass hierarchy and its deferred integration seams.

## Requirements

### Requirement: LivingEntity is the shared base for characters, NPCs, and monsters
`typeclasses/entities.py` SHALL define a `LivingEntity` typeclass, mixing in
`ComponentHolderMixin` (`evennia.contrib.base_systems.components`), the generated project's
`ObjectParent` common-hook seam, and an Evennia character base, that is the common ancestor of
`PlayerCharacter`, `NPC`, and `Monster`. No other typeclass in the project SHALL duplicate the
trait-mounting or handler-declaration logic `LivingEntity` provides.

#### Scenario: Every subclass inherits from LivingEntity
- **WHEN** `PlayerCharacter`, `NPC`, and `Monster` are inspected
- **THEN** each is a subclass of `LivingEntity`, and none re-implements trait mounting
  independently

#### Scenario: LivingEntity is component-holder capable
- **WHEN** a `LivingEntity` instance is inspected
- **THEN** it exposes the component-registration API `ComponentHolderMixin` provides, so a later
  change can attach a `Component` subclass (e.g. `QuestGiver`, `Merchant`, `GuildStaff`) without
  modifying `LivingEntity`'s base classes

### Requirement: LivingEntity carries race and subrace as lore-registry key attributes
`LivingEntity` SHALL declare `race: str | None` and `subrace: str | None` attributes, both
defaulting to `None`, holding keys into change 2's `RACE_REGISTRY` and `SUBRACE_REGISTRY`
respectively. These are the inputs the trait-scale derivation functions (see the
`entity-trait-scales` capability) read; setting them does not, by itself, mutate `entity.traits`.

#### Scenario: race and subrace default to None on a freshly created entity
- **WHEN** a freshly created `LivingEntity` (or any subclass) is inspected before any race is set
- **THEN** `entity.race` and `entity.subrace` are both `None`

#### Scenario: Setting race alone does not require a subrace
- **WHEN** `entity.race` is set to a valid `RACE_REGISTRY` key and `entity.subrace` is left `None`
- **THEN** the entity remains valid; a subrace is optional, matching change 2's own treatment of
  `Subrace` as optional at the import layer

### Requirement: PlayerCharacter, NPC, and Monster subclass LivingEntity with their documented extra fields
`typeclasses/characters.py::PlayerCharacter`, `typeclasses/npcs.py::NPC`, and
`typeclasses/monsters.py::Monster` SHALL each subclass `LivingEntity` and expose the extra fields
design doc §5.2 names for that class.

#### Scenario: PlayerCharacter exposes guild_rank, quest_log, and wallet
- **WHEN** a `PlayerCharacter` instance is created
- **THEN** it has `guild_rank`, `quest_log`, and `wallet` attributes, each present and readable,
  even though none has behavior beyond storing a default placeholder value

#### Scenario: NPC exposes dialogue_memory and schedule
- **WHEN** an `NPC` instance is created
- **THEN** it has `dialogue_memory` and `schedule` attributes, each present and readable, even
  though neither has behavior beyond storing a default placeholder value

#### Scenario: Monster exposes threat_tier, loot_table, and behaviour_tree
- **WHEN** a `Monster` instance is created
- **THEN** it has `threat_tier`, `loot_table`, and `behaviour_tree` attributes; `threat_tier`
  defaults to `None` until a caller assigns a real `MonsterTier` key and explicitly populates
  traits, while `loot_table` and `behaviour_tree` carry only default placeholder values

### Requirement: LivingEntity non-trait handlers are working implementations including persona
`LivingEntity` SHALL expose `traits`, `sexual`, `buffs`, `equipment`, `skills`, `relations`, and
`persona` as working handlers. `persona` SHALL be a `PersonaStore` mount backed by the verbatim
`entity.db.persona` record.

#### Scenario: Non-trait handlers exist as working implementations
- **WHEN** a freshly created `LivingEntity` (or any subclass) is inspected
- **THEN** `entity.traits` is a `TraitHandler`, `entity.sexual` is a `SexualState`,
  `entity.buffs` is a `BuffHandler`, `entity.equipment` is an `EquipmentHandler`,
  `entity.skills` is a `SkillHandler`, and `entity.relations` is a `RelationHandler` backed by the
  `relations_data` attribute

#### Scenario: persona is a working PersonaStore mount
- **WHEN** a freshly created `LivingEntity` (or any subclass) is inspected
- **THEN** `entity.persona` is a `PersonaStore` instance reading the `entity.db.persona` record,
  and its `flatten()` returns `None` when no persona record exists

#### Scenario: The PersonaStore implementation is authored by its owning change
- **WHEN** the codebase is inspected after the persona-store change lands
- **THEN** `world/rules/persona.py` defines the `PersonaStore` class and no `AttributeProperty`
  persona placeholder remains on `LivingEntity`

#### Scenario: Each handler is owned by its capability change
- **WHEN** handler ownership is traced
- **THEN** traits is owned by entity-traits, sexual by the sexual-state handler, buffs by the buff-handler integration, equipment and skills by equipment-inventory and the skill handler, relations by the affinity capability, and persona by the persona-store capability

### Requirement: Quest logs, dialogue memory, loot tables, and behaviour trees are not built
This change SHALL NOT implement quest-log progression, dialogue-memory storage/retrieval
semantics, loot-table roll logic, or behaviour-tree execution. These remain placeholder fields
whose behavior is added by later changes.

#### Scenario: Placeholder fields have no business logic
- **WHEN** `PlayerCharacter.quest_log`, `NPC.dialogue_memory`, `Monster.loot_table`, and
  `Monster.behaviour_tree` are inspected
- **THEN** none of them has an associated method that mutates game state or drives behavior;
  each is a data attribute only

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
