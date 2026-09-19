## Purpose

Define the display-only disguise boundary while preserving authoritative entity trait values.

## Requirements

### Requirement: disguised_stats is stored separately from TraitHandler
`LivingEntity` SHALL store `disguised_stats` as a plain attribute (`entity.db.disguised_stats`)
entirely independent of `entity.traits`, holding a mapping from a subset of the eight trait keys to
a display-only override value. Setting or clearing `disguised_stats` SHALL have no effect on any
value stored in `entity.traits`.

#### Scenario: Setting disguised_stats does not change true trait values
- **WHEN** `entity.db.disguised_stats` is set to `{"atk_phys": 60, "magic_power": 30}` on an entity
  whose true `atk_phys` base is 88 (within the elf `elf_common` `StaticBand` of 70-95 — a base
  value, per design.md D-7, never a skill-multiplied `88000`) and true `magic_power` is 250
- **THEN** `entity.traits.atk_phys.value` still equals 88 and `entity.traits.magic_power.value`
  still equals 250

#### Scenario: disguised_stats may be absent
- **WHEN** an entity has never had `disguised_stats` set
- **THEN** reading `entity.db.disguised_stats` returns `None` or an empty mapping, and true trait
  reads are unaffected

### Requirement: get_display_value is the single sanctioned accessor for a possibly-disguised stat
`world/rules/traits.py` SHALL provide exactly one function, `get_display_value(entity, trait_key)`,
that returns the disguised value for `trait_key` when present in `entity.db.disguised_stats`, and
falls back to the true trait value (`entity.traits.<trait_key>.value`) otherwise. This function
SHALL be the only code path in the project that can return a disguised value.

#### Scenario: get_display_value returns the disguised value when present
- **WHEN** `get_display_value(entity, "atk_phys")` is called on an entity with
  `disguised_stats = {"atk_phys": 60}` and true `atk_phys` base value 88
- **THEN** it returns 60

#### Scenario: get_display_value falls back to the true value when absent
- **WHEN** `get_display_value(entity, "defense")` is called on an entity with `disguised_stats =
  {"atk_phys": 60}` (no `defense` key) and true `defense` base value 90
- **THEN** it returns 90

### Requirement: Combat, resolution, and damage modules never call the disguise accessor
No module implementing combat, action resolution, targeting, or dice/damage logic SHALL reference
`get_display_value` or `disguised_stats`. This boundary SHALL be enforced by an automated
regression test that scans the deterministic-core module paths design doc §3.2 names for combat
and resolution and fails if either symbol appears in any of them.

#### Scenario: The boundary test passes today because no combat module exists yet
- **WHEN** the boundary regression test runs against this change's code, before any later change
  has created `world/rules/combat.py`, `world/rules/action.py`, `world/rules/dice.py`, or
  `world/rules/targeting.py`
- **THEN** the test passes (there is nothing to scan yet), rather than being skipped entirely or
  passing vacuously without ever being wired into the test run

#### Scenario: The boundary test fails the moment a forbidden module reads the disguise layer
- **WHEN** a hypothetical future edit adds a call to `get_display_value` or a reference to
  `disguised_stats` inside `world/rules/combat.py` (once that file exists)
- **THEN** the boundary regression test fails, identifying which forbidden module contains the
  violation

### Requirement: disguised_stats keys are readable by exactly three consumers, including implemented guild registration
The docstring of `get_display_value` and this specification SHALL name exactly three permitted call
sites: appearance rendering (`look`), guild registration records, and appraisal items. Appearance
rendering SHALL be implemented through the `look <target>` displayed-stats block, which SHALL call
the accessor for the displayed combat five (`atk_phys`, `agility`, `defense`, `magic_power`, `hp`).
Guild registration SHALL call the accessor once per documented trait key to persist a historical
displayed-stat snapshot. Appraisal items MAY remain deferred. No other guild operation, including
board eligibility, reward settlement, merit checks, examiner profile selection, combat, or
promotion, SHALL call the accessor or read `disguised_stats`.

This requirement bounds READERS. A CONSUMER is a module that surfaces or resolves a displayed stat
value from the mapping for a player-facing view or a persisted record: the `look <target>`
displayed-stats block and the guild-registration snapshot path, with the status read model
(`world/rules/status_query.py`) being the status-side face of the same appearance-rendering
consumer (master design D2 counts "look / the status read model" as that one consumer).
Perception paths — the NPC-dialogue prompt injection and its no-leak secret set
(`typeclasses/npcs.py` feeding `world/ai/npc_dialogue.py`) and the `status_disguise` cast event
context (`commands/action.py`) — pass the mapping as opaque perceived-display material and never
resolve a gameplay stat from it; they are not consumers and are unchanged by this requirement.

Seeding the layer is a separate, bounded set of WRITERS: `world/imports/loader.py` (import
records) and `world/rules/character_creation.py` (preset activation) SHALL be the only production
modules that seed `entity.db.disguised_stats` from an authored declaration at entity
construction, each never reading the mapping back to make a decision. The companion builder
`world/rules/starting_companions.py` seeds each declared partner preset's own authored card
during preset activation — the same construction-time seeding class, derived entirely from the
partner's registry declaration and never read back. The runtime write for
`status_disguise`, `world/rules/skill_effects.py::apply_disguise_effect`, is sanctioned and bound
by the `skill-handler` capability's own requirement (it touches only the display layer).
Snapshot/restore machinery (the activation, action, clock, and cast-settlement rollback surfaces)
may re-assign the attribute to a previously recorded value; a restore carries its writer's value
and authors none of its own. A writer SHALL NOT be counted as a consumer, and the
forbidden-module list (`world/rules/combat.py`, `world/rules/dice.py`,
`world/rules/targeting.py`) SHALL remain closed to both reads and writes.

#### Scenario: Accessor documentation still names exactly three consumers
- **WHEN** `get_display_value`'s docstring is inspected
- **THEN** it names appearance rendering (`look`), guild registration records, and appraisal items
  as the only permitted callers and states that combat, resolution, and damage must not call it

#### Scenario: Appearance rendering and registration are the only implemented consumers
- **WHEN** production (non-test) source modules are scanned for `get_display_value` or
  `disguised_stats`
- **THEN** the sanctioned readers are exactly the `look <target>` displayed-stats block and the
  guild-registration snapshot path, the sanctioned writers are exactly the import loader and preset
  activation at construction, plus the companion builder seeding each declared partner's own
  preset card during activation (beside the skill-handler-owned runtime write and
  value-carrying restores), and no other module reads the raw disguise mapping directly to
  resolve a gameplay stat value (perception injection and secret-set comparison are perception
  material, not stat resolution)

#### Scenario: Promotion uses canonical state
- **WHEN** a registered actor changes or clears disguise before a guild examination
- **THEN** merit eligibility, examiner stats, combat, and promotion outcomes are unchanged

#### Scenario: The forbidden modules stay closed to the seeding path
- **WHEN** `world/rules/combat.py`, `world/rules/dice.py`, and `world/rules/targeting.py` are scanned
- **THEN** none of them contains `disguised_stats` or `get_display_value`, unchanged by the creation-side writer

### Requirement: The disguise layer records the provenance of the veil it holds
An entity carrying a disguise layer SHALL also carry a record of that veil's PROVENANCE: divine, when a
divine mystery wrote it at cast time, or mundane, for every other origin (an authored import record,
preset activation, or the companion builder). The provenance record SHALL be stored SEPARATELY from the
display mapping, so the mapping's key set, its import schema and every sanctioned reader are unchanged
and continue to see only trait-key overrides. An entity with no provenance record SHALL read as
mundane. Clearing the disguise layer SHALL clear its provenance in the same operation, and both SHALL
be restored together when a resolution is rolled back.

#### Scenario: A divine cast records divine provenance
- **WHEN** a divine mystery writes a veil onto an entity
- **THEN** that entity's veil reads as divine provenance, and its display mapping contains only
  trait-key overrides

#### Scenario: An authored declaration reads as mundane
- **WHEN** an entity is seeded with a disguise layer by an import record or preset activation, with no
  provenance record written
- **THEN** its veil reads as mundane provenance

#### Scenario: Clearing the veil clears its provenance
- **WHEN** an entity's disguise layer is cleared by any sanctioned path
- **THEN** no stale provenance record remains, and the entity reads as unveiled

#### Scenario: A rolled-back resolution restores both records together
- **WHEN** a resolution that wrote or cleared a veil has a later pending effect fail, restoring the
  action snapshot
- **THEN** both the display mapping and the provenance record are byte-equal to their pre-action values

### Requirement: Only an entity that can use divine arts may be seeded with a disguise layer
A disguise layer SHALL exist only on an entity whose race declares that it can use divine arts. The
veil verb is bloodline-gated, and nothing else in the game writes a disguise layer, so a veil on any
other entity describes state the engine would refuse to produce.

Every SEEDING boundary SHALL enforce this before the layer can be persisted: the lore-registry
validation that admits authored preset cards, and the import validation that admits authored records.
Enforcement SHALL fail closed — a race that does not resolve is treated as unable to use divine arts,
so an unknown race cannot smuggle a veil past the check.

The check SHALL read the race's declared divine-arts capability rather than inspecting skill
ownership, so an entity is judged on whether its bloodline could ever place a veil, not on whether
this particular declaration happens to list the veil skill.

This requirement bounds the layer's WEARER. It does not change which values the layer may hold, who
may read it, or which modules may write it; those remain governed by this capability's existing
requirements.

#### Scenario: An authored preset on a non-divine race may not declare a disguise layer
- **WHEN** a preset card whose race cannot use divine arts declares a non-empty `disguised_stats`
- **THEN** lore-registry validation raises at import, naming the preset and the violation, and the
  registry does not load

#### Scenario: An authored preset on a divine-capable race may declare one
- **WHEN** a preset card whose race can use divine arts declares a well-formed `disguised_stats`
- **THEN** validation accepts it, exactly as before this change

#### Scenario: An imported record on a non-divine race may not carry a disguise layer
- **WHEN** a character record whose race cannot use divine arts declares a non-empty `disguised_stats`
- **THEN** import validation reports a rejection naming the record and the field, and no entity is
  constructed

#### Scenario: An unresolvable race cannot carry a disguise layer
- **WHEN** a preset card or a character record declares a disguise layer alongside a race that does
  not resolve in the race registry
- **THEN** the disguise layer is rejected, because an unresolved race is treated as unable to use
  divine arts

#### Scenario: An empty declaration is not a disguise layer
- **WHEN** a preset card or a character record on a non-divine race declares an empty
  `disguised_stats`
- **THEN** validation accepts it, because no layer is seeded
