## MODIFIED Requirements

### Requirement: Race-driven gauge and counter initial values come from RaceProfile, never a hardcoded per-race number
`world/rules/traits.py` SHALL derive a `PlayerCharacter` or `NPC`'s
race-baseline `hp`/`mp`/`sp` gauge maxima from `RaceProfile.vital_baseline`, and
its race-baseline `magic_level` counter maximum from `RaceProfile.magic_cap`,
reading both from change 2's `world.lore.races.RACE_REGISTRY`. No module added
by this change SHALL contain a hardcoded HP, MP, SP, or magic-cap number for
any specific race. Race-baseline construction SHALL set `magic_level` current
value to `0`; a separately validated player-character activation service may
then assign its lore-owned starting value before enabling gameplay.

#### Scenario: Elf HP gauge reflects the race's vital baseline
- **WHEN** a `PlayerCharacter` or `NPC` is initialized with `race="elf"`
- **THEN** `entity.traits.hp` maximum equals
  `RACE_REGISTRY["elf"].vital_baseline.hp[0]`, not a literal number written in
  `world/rules/traits.py`

#### Scenario: Human HP gauge reflects the race's vital baseline
- **WHEN** a `PlayerCharacter` or `NPC` is initialized with `race="human"`
- **THEN** `entity.traits.hp` maximum equals
  `RACE_REGISTRY["human"].vital_baseline.hp[0]`, not a literal number written
  in `world/rules/traits.py`

#### Scenario: magic_level cap reflects the race's magic_cap
- **WHEN** a `PlayerCharacter` or `NPC` is initialized with any valid race
- **THEN** `entity.traits.magic_level` maximum equals
  `RACE_REGISTRY[race].magic_cap`, and its current value starts at `0` during
  race-baseline construction

#### Scenario: The vital-pool gap between human and elf propagates from lore to the entity
- **WHEN** an elf `PlayerCharacter`'s `entity.traits.hp` maximum is compared
  against a human `PlayerCharacter`'s `entity.traits.hp` maximum
- **THEN** the elf value is at least 50 times the human value, matching the
  same magnitude assertion change 2 makes directly on
  `RaceProfile.vital_baseline`
