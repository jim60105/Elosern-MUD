# magic-level-progression Specification

## Purpose
Define deterministic magic-level progression from study time and tiered monster kills.

## Requirements

### Requirement: effective_magic_growth_multiplier combines race, self, and conferred multipliers
`world/rules/progression.py` SHALL define `effective_magic_growth_multiplier(entity)` as a pure query
that multiplies together exactly three sources: `RaceProfile.learning_multiplier` for the entity's
race (`1.0` if the entity has no race), a self-multiplier read from the entity's own owned `PASSIVE`
skills via the existing `growth_rate:magic:<N>` effect-ID convention (`1.0` if none owned), and change
6's `growth_rate_multiplier(entity)`. This function SHALL NOT write to any entity attribute.

#### Scenario: An entity with no race, no self-multiplier skill, and no buff returns 1.0
- **WHEN** `effective_magic_growth_multiplier(entity)` is called on an entity with no owned skill
  carrying a `growth_rate:magic:` effect and no active `conferred_growth_rate` buff
- **THEN** it returns exactly `1.0`

#### Scenario: An elf's race learning_multiplier is folded in
- **WHEN** `effective_magic_growth_multiplier(entity)` is called on an entity with `race == "elf"`
  (`RACE_REGISTRY["elf"].learning_multiplier == 10.0`), no self-multiplier skill, and no active buff
- **THEN** it returns exactly `10.0`

#### Scenario: A self-multiplier passive skill is folded in
- **WHEN** `effective_magic_growth_multiplier(entity)` is called on a human entity (`learning_multiplier
  == 1.0`) owning a `PASSIVE` skill whose `effects` includes `"growth_rate:magic:100"`, with no
  active buff
- **THEN** it returns exactly `100.0`

#### Scenario: A conferred_growth_rate buff changes the multiplier through change 6's own function
- **WHEN** a human entity has `world.rules.buffs.grant_conferred_growth_rate(entity,
  source_key="elosia", scale=0.5)` applied, no owned `growth_rate:magic:` skill, and
  `growth_rate_multiplier(entity)` therefore returns `0.5`
- **THEN** `effective_magic_growth_multiplier(entity)` returns exactly `0.5`, and `accrue_magic_study()`
  called on this entity grants exactly half the magic XP it would grant the same entity with no buff
  active for the same elapsed time — proving change 6's conferred grant changes this entity's actual
  progression rate through this change's code, not merely through an unread return value

#### Scenario: All three sources combine multiplicatively, not additively
- **WHEN** an elf entity (`learning_multiplier == 10.0`) owns a `growth_rate:magic:100` passive
  skill and has an active `conferred_growth_rate` buff with `scale=0.5`
- **THEN** `effective_magic_growth_multiplier(entity)` returns exactly `10.0 * 100 * 0.5 == 500.0`

### Requirement: accrue_magic_study grants magic XP only for SKIP-sourced elapsed time
`world/rules/progression.py` SHALL define `accrue_magic_study(entities, seconds, source)` as a
settlement-stage-shaped callable that, for each entity in `entities`, grants
`(seconds / 3600) * STUDY_BASE_XP_PER_HOUR * effective_magic_growth_multiplier(entity)` magic XP when
`source is AdvanceSource.SKIP`, and grants nothing and performs no other side effect for any other
`AdvanceSource` value. This function SHALL NOT iterate per-second or per-quantum — it SHALL compute
its result once per entity per call regardless of the magnitude of `seconds`.

#### Scenario: A SKIP-sourced advance grants magic XP proportional to elapsed hours
- **WHEN** `accrue_magic_study([entity], 3600, AdvanceSource.SKIP)` is called on an entity with
  `effective_magic_growth_multiplier(entity) == 1.0` and `entity.db.magic_xp` starting at `0.0`
- **THEN** `entity.db.magic_xp` equals exactly `STUDY_BASE_XP_PER_HOUR` afterward

#### Scenario: A COMMAND-sourced advance grants no magic study XP
- **WHEN** `accrue_magic_study([entity], 6, AdvanceSource.COMMAND)` is called
- **THEN** `entity.db.magic_xp` is unchanged from before the call

#### Scenario: A COMBAT-sourced advance grants no magic study XP
- **WHEN** `accrue_magic_study([entity], 36, AdvanceSource.COMBAT)` is called (e.g., six rounds of
  combat at 6 seconds each)
- **THEN** `entity.db.magic_xp` is unchanged from before the call — ambient study XP and combat-kill XP
  (a separate function) are never both applied for the same elapsed combat interval

#### Scenario: A long skip is computed in one step, not iterated
- **WHEN** `accrue_magic_study([entity], 28800, AdvanceSource.SKIP)` (an 8-hour skip) is called
- **THEN** the resulting `entity.db.magic_xp` gain equals exactly `(28800 / 3600) *
  STUDY_BASE_XP_PER_HOUR * effective_magic_growth_multiplier(entity)`, computed without any per-second
  or per-quantum loop

### Requirement: grant_combat_kill_xp awards magic XP scaled by monster tier and the entity's growth multiplier
`world/rules/progression.py` SHALL define `grant_combat_kill_xp(entity, monster_tier_key)` as a
declared integration seam that adds `COMBAT_KILL_XP_TABLE[monster_tier_key] *
effective_magic_growth_multiplier(entity)` to the entity's magic XP accumulator, raising a lookup error
for an unrecognized `monster_tier_key` rather than silently granting zero XP.

#### Scenario: A kill against a known monster tier grants scaled XP
- **WHEN** `grant_combat_kill_xp(entity, "mid")` is called on an entity with
  `effective_magic_growth_multiplier(entity) == 2.0`
- **THEN** `entity.db.magic_xp` increases by exactly `COMBAT_KILL_XP_TABLE["mid"] * 2.0`

#### Scenario: An unknown monster tier key fails loudly
- **WHEN** `grant_combat_kill_xp(entity, "not_a_real_tier")` is called
- **THEN** a lookup error is raised and `entity.db.magic_xp` is unchanged

#### Scenario: Combat-kill XP table entries are strictly ordered by tier severity
- **WHEN** `COMBAT_KILL_XP_TABLE`'s four entries (`low`, `mid`, `high`, `calamity`) are inspected
- **THEN** their values are strictly increasing in that order

### Requirement: magic_level never exceeds the entity's race-driven cap regardless of XP surplus
`world/rules/progression.py` SHALL ensure that any function which grants magic XP (`accrue_magic_study`,
`grant_combat_kill_xp`) drains that XP into `entity.traits.magic_level` using a closed-form computation
that never sets `magic_level` above its configured maximum (`RaceProfile.magic_cap`, or `0` for an
entity with no race), and SHALL discard XP surplus once the cap is reached rather than banking it.

#### Scenario: A massive XP surplus still caps magic_level at the entity's configured maximum
- **WHEN** an elf entity (`entity.traits.magic_level.max == 900`) has `entity.db.magic_xp` set to a
  value far exceeding what 900 levels would cost, and a magic-XP-granting function is called
- **THEN** `entity.traits.magic_level.value` equals exactly `900`, never higher, and
  `entity.db.magic_xp` equals `0.0` afterward

#### Scenario: An entity already at its cap accrues no further level and its XP accumulator is reset
- **WHEN** `accrue_magic_study` or `grant_combat_kill_xp` is called on an entity whose
  `entity.traits.magic_level.value` already equals `entity.traits.magic_level.max`
- **THEN** `entity.traits.magic_level.value` is unchanged and `entity.db.magic_xp` equals `0.0`
  afterward

#### Scenario: A Monster's magic_level (capped at 0 by entity-traits) never grows
- **WHEN** `grant_combat_kill_xp(monster, "low")` is called on a `Monster` entity (whose
  `entity.traits.magic_level.max == 0`, per entity-traits' own construction rule)
- **THEN** `entity.traits.magic_level.value` remains `0` and `entity.db.magic_xp` is reset to `0.0`

#### Scenario: The level-up computation is closed-form, not a loop bounded by XP magnitude
- **WHEN** `_apply_level_ups` is invoked with an XP surplus large enough to cross many levels at once
- **THEN** the resulting `magic_level` and remaining `magic_xp` are computed via floor-division and a
  single `min()` against the cap, not by iterating one level at a time

### Requirement: World-clock and combat integration use the progression seams exactly once
The existing `magic_study` world-clock stage SHALL call `accrue_magic_study()` for elapsed non-combat
time, whose SKIP-only source gate remains authoritative. Combat action resolution SHALL stage
`grant_combat_kill_xp()` in the same atomic commit for each unique, resolved tiered monster newly reduced
from positive HP to zero, using its `threat_tier`; it SHALL not award XP for non-monsters, an already-dead
target, or duplicate target references. Combat upkeep settlement SHALL additionally stage exactly one
`grant_combat_kill_xp()` for a tiered monster whose lethal HP crossing was caused by an attributed
damaging rate tick (a buff carrying a resolvable `source_pk`), in the same combat-round transaction. An
unattributed tick, a simulated (guild-exam) tick, a non-Monster target, and a target whose death was
already credited by an action SHALL award no XP.

#### Scenario: A SKIP advance reaches the real study callable
- **WHEN** `WorldClock.advance` receives `AdvanceSource.SKIP` and an eligible entity
- **THEN** its magic XP increases through `accrue_magic_study()`

#### Scenario: Defeating a tiered monster awards the attacker once
- **WHEN** a successful combat action reduces a monster with `threat_tier == "low"` from positive HP to zero
- **THEN** the acting entity receives exactly one low-tier combat-kill XP award

#### Scenario: An attributed lethal rate tick awards the caster exactly once
- **WHEN** the player's `fire_scorch` tick reduces a monster with `threat_tier == "low"` from positive HP to zero during combat upkeep
- **THEN** the acting entity receives exactly one low-tier combat-kill XP award committed with that round

#### Scenario: An unattributed or simulated lethal tick awards nothing
- **WHEN** a lethal rate tick has no resolvable source, or fires inside a guild examination
- **THEN** no entity receives combat-kill XP and no progression attribute changes as a result of the tick

### Requirement: Magic-growth values are finite and non-negative
`grant_conferred_growth_rate()` SHALL reject a non-numeric, boolean, negative, infinite, or NaN scale.
Progression SHALL reject a non-finite or negative accumulated XP or effective growth multiplier before it
writes progression state. A failure from an action's deferred combat-kill award SHALL roll back the
action's damage, resource spend, skill practice, and progression attributes.

#### Scenario: Invalid growth-rate scale is rejected before persistence
- **WHEN** a caller grants a conferred growth rate with `-1`, `NaN`, or infinity
- **THEN** the call raises `ValueError` and no buff is added

#### Scenario: Invalid legacy multiplier rolls back a combat action
- **WHEN** a combat action would defeat a monster while an internally injected invalid multiplier is active
- **THEN** the action is rejected and its target HP, resources, magic XP, and skill proficiency are restored
