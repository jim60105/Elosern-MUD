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
