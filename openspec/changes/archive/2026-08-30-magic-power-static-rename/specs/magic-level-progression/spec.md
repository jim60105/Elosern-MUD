## RENAMED Requirements

- FROM: `### Requirement: effective_magic_growth_multiplier combines race, self, and conferred multipliers`
- TO: `### Requirement: effective_growth_multiplier combines race, self, and conferred multipliers`

## MODIFIED Requirements

### Requirement: effective_growth_multiplier combines race, self, and conferred multipliers
`world/rules/progression.py` SHALL define `effective_growth_multiplier(entity)` (renamed from
`effective_magic_growth_multiplier()`; the magic-only name retires with the trait rename) as a pure query
that multiplies together exactly three sources: `RaceProfile.learning_multiplier` for the entity's
race (`1.0` if the entity has no race), a self-multiplier read from the entity's own owned `PASSIVE`
skills via the existing `growth_rate:practice:<N>` effect-ID convention (`1.0` if none owned), and change
6's `growth_rate_multiplier(entity)`. This function SHALL NOT write to any entity attribute.

#### Scenario: An entity with no race, no self-multiplier skill, and no buff returns 1.0
- **WHEN** `effective_growth_multiplier(entity)` is called on an entity with no owned skill
  carrying a `growth_rate:practice:` effect and no active `conferred_growth_rate` buff
- **THEN** it returns exactly `1.0`

#### Scenario: An elf's race learning_multiplier is folded in
- **WHEN** `effective_growth_multiplier(entity)` is called on an entity with `race == "elf"`
  (`RACE_REGISTRY["elf"].learning_multiplier == 10.0`), no self-multiplier skill, and no active buff
- **THEN** it returns exactly `10.0`

#### Scenario: A self-multiplier passive skill is folded in
- **WHEN** `effective_growth_multiplier(entity)` is called on a human entity (`learning_multiplier
  == 1.0`) owning a `PASSIVE` skill whose `effects` includes `"growth_rate:practice:100"`, with no
  active buff
- **THEN** it returns exactly `100.0`

#### Scenario: A conferred_growth_rate buff changes the multiplier through change 6's own function
- **WHEN** a human entity has `world.rules.buffs.grant_conferred_growth_rate(entity,
  source_key="elosia", scale=0.5)` applied, no owned `growth_rate:practice:` skill, and
  `growth_rate_multiplier(entity)` therefore returns `0.5`
- **THEN** `effective_growth_multiplier(entity)` returns exactly `0.5`, and `accrue_magic_study()`
  called on this entity grants exactly half the magic XP it would grant the same entity with no buff
  active for the same elapsed time — proving change 6's conferred grant changes this entity's actual
  progression rate through this change's code, not merely through an unread return value

#### Scenario: All three sources combine multiplicatively, not additively
- **WHEN** an elf entity (`learning_multiplier == 10.0`) owns a `growth_rate:practice:100` passive
  skill and has an active `conferred_growth_rate` buff with `scale=0.5`
- **THEN** `effective_growth_multiplier(entity)` returns exactly `10.0 * 100 * 0.5 == 500.0`

### Requirement: World-clock and combat integration use the progression seams exactly once
The existing `magic_study` world-clock stage SHALL call `accrue_magic_study()` for elapsed non-combat
time, whose SKIP-only source gate remains authoritative. The seam contract is unchanged by the trait
rename; the drained destination trait is now the `magic_power` static (interim state until
`magic-xp-engine-retirement` deletes these seams). Combat action resolution SHALL stage
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
