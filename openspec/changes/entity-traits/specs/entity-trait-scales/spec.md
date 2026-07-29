## ADDED Requirements

### Requirement: LivingEntity mounts TraitHandler with the setting's eight-key trait set
`LivingEntity` SHALL mount `evennia.contrib.rpg.traits.TraitHandler` as `entity.traits`, containing
exactly eight traits with the trait types design doc §5.2 specifies: `hp`, `mp`, `sp` as
`GaugeTrait`; `atk_phys`, `agility`, `defense` as `StaticTrait`; `magic_level`, `guild_merit` as
`CounterTrait`.

#### Scenario: All eight traits are present with the correct type
- **WHEN** `entity.traits` is inspected on any `LivingEntity` instance
- **THEN** it contains exactly the keys `hp`, `mp`, `sp`, `atk_phys`, `agility`, `defense`,
  `magic_level`, `guild_merit`, and each resolves to an instance of the trait type design doc §5.2
  specifies for that key

#### Scenario: Gauge traits carry a max and a regen rate
- **WHEN** `entity.traits.hp`, `entity.traits.mp`, or `entity.traits.sp` is inspected
- **THEN** it has both a maximum value and a non-`None` regen rate

#### Scenario: Static traits carry base and mod
- **WHEN** `entity.traits.atk_phys`, `entity.traits.agility`, or `entity.traits.defense` is
  inspected
- **THEN** its value is computed from a `base` plus a `mod`, per `StaticTrait` semantics

### Requirement: Race-driven initial trait values come from RaceProfile, never a hardcoded per-race number
`world/rules/traits.py` SHALL derive a `PlayerCharacter` or `NPC`'s initial `hp`/`mp`/`sp` gauge
maxima from `RaceProfile.vital_baseline`, and its initial `magic_level` counter maximum from
`RaceProfile.magic_cap`, reading both from change 2's `world.lore.races.RACE_REGISTRY`. No module
added by this change SHALL contain a hardcoded HP, MP, SP, or magic-cap number for any specific
race.

#### Scenario: Elf HP gauge reflects the race's vital baseline
- **WHEN** a `PlayerCharacter` or `NPC` is initialized with `race="elf"`
- **THEN** `entity.traits.hp`'s maximum equals `RACE_REGISTRY["elf"].vital_baseline.hp[0]`, not a
  literal number written in `world/rules/traits.py`

#### Scenario: Human HP gauge reflects the race's vital baseline
- **WHEN** a `PlayerCharacter` or `NPC` is initialized with `race="human"`
- **THEN** `entity.traits.hp`'s maximum equals `RACE_REGISTRY["human"].vital_baseline.hp[0]`, not a
  literal number written in `world/rules/traits.py`

#### Scenario: magic_level cap reflects the race's magic_cap
- **WHEN** a `PlayerCharacter` or `NPC` is initialized with any valid race
- **THEN** `entity.traits.magic_level`'s maximum equals `RACE_REGISTRY[race].magic_cap`

#### Scenario: The three-orders-of-magnitude gap propagates from lore to the entity
- **WHEN** an elf `PlayerCharacter`'s `entity.traits.hp` maximum is compared against a human
  `PlayerCharacter`'s `entity.traits.hp` maximum
- **THEN** the elf value is at least 50 times the human value, matching the same magnitude
  assertion change 2 makes directly on `RaceProfile.vital_baseline`

### Requirement: Static combat trait bases are derived from a race scale factor, not invented per race
`world/rules/traits.py` SHALL define a single race-independent reference baseline for
`atk_phys`/`agility`/`defense`, and a `race_scale_factor()` function computed from
`RaceProfile.vital_baseline.hp`, and SHALL apply that factor uniformly to derive every race's
initial static trait bases. No per-race static-trait number SHALL be hardcoded outside this
mechanism.

#### Scenario: Elf static traits scale with the same ratio as elf HP
- **WHEN** an elf `PlayerCharacter`'s `entity.traits.atk_phys` base is compared against a human
  `PlayerCharacter`'s `entity.traits.atk_phys` base
- **THEN** the ratio between them equals `race_scale_factor` computed for elf, which itself equals
  the ratio between elf and human `vital_baseline.hp[0]`

#### Scenario: Human static traits equal the reference baseline exactly
- **WHEN** a human `PlayerCharacter`'s `entity.traits.atk_phys`, `agility`, and `defense` bases are
  inspected
- **THEN** each equals its corresponding `REFERENCE_STATIC_BASELINE` entry, since human
  `race_scale_factor` is 1.0 by construction

### Requirement: Monster trait baselines derive from MonsterTier ordering
`world/rules/traits.py` SHALL derive a `Monster`'s initial trait values from its `threat_tier`
(a `MonsterTier` key) via an order-of-magnitude multiplier keyed to `MonsterTier`'s documented
F-E/D-C/B-A/災厄級 ordering, applied to the same human reference baseline the race-driven path
uses. No hardcoded per-monster or per-species number SHALL appear in this change's code.

#### Scenario: Higher monster tiers scale trait values up
- **WHEN** a `Monster` with `threat_tier` in the highest band (災厄級) is compared against a
  `Monster` with `threat_tier` in the lowest band (F-E) for the same trait
- **THEN** the higher-tier monster's value is at least ten times the lower-tier monster's value

#### Scenario: A Monster cannot be constructed without a resolvable threat_tier
- **WHEN** a `Monster` is initialized with a `threat_tier` value that does not exist in
  `MONSTER_TIER_REGISTRY`
- **THEN** initialization raises an error rather than silently defaulting to an arbitrary trait
  scale

### Requirement: guild_merit starts at zero with no upper bound
`world/rules/traits.py` SHALL initialize every `LivingEntity`'s `guild_merit` counter at `0` with
no maximum, since no lore source specifies a merit cap.

#### Scenario: guild_merit has no maximum
- **WHEN** `entity.traits.guild_merit` is inspected on a freshly created entity
- **THEN** its current value is `0` and it has no configured maximum
