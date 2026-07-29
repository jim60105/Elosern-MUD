## ADDED Requirements

### Requirement: LivingEntity is the shared base for characters, NPCs, and monsters
`typeclasses/entities.py` SHALL define a `LivingEntity` typeclass, mixing in
`ComponentHolderMixin` (`evennia.contrib.base_systems.components`) and a Evennia character base,
that is the common ancestor of `PlayerCharacter`, `NPC`, and `Monster`. No other typeclass in the
project SHALL duplicate the trait-mounting or handler-declaration logic `LivingEntity` provides.

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
- **THEN** it has `threat_tier`, `loot_table`, and `behaviour_tree` attributes; `threat_tier` holds
  a real `MonsterTier` key used to derive its trait values, while `loot_table` and
  `behaviour_tree` are present but carry only a default placeholder value

### Requirement: Non-trait LivingEntity handlers are declared seams, not implementations
`LivingEntity` SHALL declare `sexual`, `buffs`, `equipment`, `skills`, `relations`, and `persona`
as placeholder attributes defaulting to `None`, and SHALL NOT implement any behavior for them.
Only the `traits` handler is a working implementation after this change.

#### Scenario: Non-trait handlers exist but default to None
- **WHEN** a freshly created `LivingEntity` (or any subclass) is inspected
- **THEN** `entity.sexual`, `entity.buffs`, `entity.equipment`, `entity.skills`,
  `entity.relations`, and `entity.persona` are all present as attributes and all equal `None`

#### Scenario: No handler class is authored for a deferred concern
- **WHEN** the codebase added by this change is inspected
- **THEN** it contains no `SexualState`, `BuffHandler`, `EquipmentHandler`, `SkillHandler`,
  `RelationHandler`, or `PersonaStore` class definition — those are owned by later changes

### Requirement: Quest logs, dialogue memory, loot tables, and behaviour trees are not built
This change SHALL NOT implement quest-log progression, dialogue-memory storage/retrieval
semantics, loot-table roll logic, or behaviour-tree execution. These remain placeholder fields
whose behavior is added by later changes.

#### Scenario: Placeholder fields have no business logic
- **WHEN** `PlayerCharacter.quest_log`, `NPC.dialogue_memory`, `Monster.loot_table`, and
  `Monster.behaviour_tree` are inspected
- **THEN** none of them has an associated method that mutates game state or drives behavior;
  each is a data attribute only
