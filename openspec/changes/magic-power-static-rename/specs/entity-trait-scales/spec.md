## MODIFIED Requirements

### Requirement: LivingEntity mounts TraitHandler with the setting's eight-key trait set
`LivingEntity` SHALL mount `evennia.contrib.rpg.traits.TraitHandler` as `entity.traits`. Before a
caller's explicit identity-population step, the handler SHALL be empty because `race`, `subrace`,
or `threat_tier` is not known during generic Evennia object creation. After
`apply_race_baseline()` or `apply_monster_tier()` succeeds, it SHALL contain exactly eight traits
with the trait types design doc §5.2 specifies: `hp`, `mp`, `sp` as
`GaugeTrait`; `atk_phys`, `agility`, `defense`, and `magic_power` as `StaticTrait`; `guild_merit`
as `CounterTrait`.

#### Scenario: All eight traits are present with the correct type
- **WHEN** `entity.traits` is inspected after a valid identity-population method succeeds
- **THEN** it contains exactly the keys `hp`, `mp`, `sp`, `atk_phys`, `agility`, `defense`,
  `magic_power`, `guild_merit`, and each resolves to an instance of the trait type design doc §5.2
  specifies for that key

#### Scenario: A generically created entity is explicitly uninitialized
- **WHEN** Evennia creates a `LivingEntity` before a caller assigns its race or threat tier
- **THEN** `entity.traits` exists but is empty, and population fails clearly if invoked without
  the required identity key

#### Scenario: Gauge traits carry a max and a regen rate
- **WHEN** `entity.traits.hp`, `entity.traits.mp`, or `entity.traits.sp` is inspected
- **THEN** it has both a maximum value and a non-`None` regen rate

#### Scenario: Static traits carry base and mod
- **WHEN** `entity.traits.atk_phys`, `entity.traits.agility`, or `entity.traits.defense` is
  inspected
- **THEN** its value is computed from a `base` plus a `mod`, per `StaticTrait` semantics

### Requirement: Race-driven gauge and counter initial values come from RaceProfile, never a hardcoded per-race number
`world/rules/traits.py` SHALL derive a `PlayerCharacter` or `NPC`'s race-baseline `hp`/`mp`/`sp`
gauge maxima from `RaceProfile.vital_baseline`, and its race-baseline `magic_power` static base
from `RaceProfile.static_baseline.magic_power[0]`, reading both from change 2's
`world.lore.races.RACE_REGISTRY`. No
module added by this change SHALL contain a hardcoded HP, MP, SP, or magic-band number for any
specific race. Race-baseline construction SHALL set `magic_power` to the fourth band's floor
exactly like the other three static axes; no separate starting-magic assignment step exists.

#### Scenario: Elf HP gauge reflects the race's vital baseline
- **WHEN** a `PlayerCharacter` or `NPC` is initialized with `race="elf"`
- **THEN** `entity.traits.hp`'s maximum equals `RACE_REGISTRY["elf"].vital_baseline.hp[0]`, not a
  literal number written in `world/rules/traits.py`

#### Scenario: Human HP gauge reflects the race's vital baseline
- **WHEN** a `PlayerCharacter` or `NPC` is initialized with `race="human"`
- **THEN** `entity.traits.hp`'s maximum equals `RACE_REGISTRY["human"].vital_baseline.hp[0]`, not a
  literal number written in `world/rules/traits.py`

#### Scenario: magic_power base reflects the race's fourth static band
- **WHEN** a `PlayerCharacter` or `NPC` is initialized with any valid race
- **THEN** `entity.traits.magic_power` is a `StaticTrait` whose base equals
  `RACE_REGISTRY[race].static_baseline.magic_power[0]` (the fourth band's floor), never a literal
  number written in `world/rules/traits.py`, and no counter `max` is configured for it

#### Scenario: The vital-pool gap between human and elf propagates from lore to the entity
- **WHEN** an elf `PlayerCharacter`'s `entity.traits.hp` maximum is compared against a human
  `PlayerCharacter`'s `entity.traits.hp` maximum
- **THEN** the elf value is at least 50 times the human value, matching the same magnitude
  assertion change 2 makes directly on `RaceProfile.vital_baseline`

### Requirement: Static combat trait bases are read directly from RaceProfile.static_baseline, never derived from vital_baseline
`world/rules/traits.py` SHALL derive a `PlayerCharacter` or `NPC`'s initial `atk_phys`/`agility`/
`defense` static bases directly from `RaceProfile.static_baseline` (the species-wide floor-to-
ceiling band for those three stats), reading `world.lore.races.RACE_REGISTRY`. No module added by
this change SHALL compute a static trait value as a function of `vital_baseline` or
any other field that is not itself a static-stat field — vital pools and static combat stats scale
by different, independently documented factors between races, and neither is derivable from the
other.

#### Scenario: Elf static trait bases reflect the race's static_baseline, not a vital-pool ratio
- **WHEN** an elf `PlayerCharacter`'s `entity.traits.atk_phys`, `agility`, and `defense` bases are
  inspected
- **THEN** each equals `RACE_REGISTRY["elf"].static_baseline`'s corresponding floor value (70), not
  a value computed from `RACE_REGISTRY["elf"].vital_baseline.hp` scaled against the human baseline

#### Scenario: Human static trait bases are single-digit, matching the source's sample data
- **WHEN** a human `PlayerCharacter`'s `entity.traits.atk_phys`, `agility`, and `defense` bases are
  inspected
- **THEN** each equals `RACE_REGISTRY["human"].static_baseline`'s corresponding floor value (1), and
  none exceeds the species-wide ceiling (22) — at no point does a freshly constructed human's static
  trait value fall in the tens-of-thousands, or even consistently above single digits, range

#### Scenario: The human-to-elf static ratio is roughly 10x, not the vital-pool's roughly 100x
- **WHEN** the elf `static_baseline` floor is compared against the `human_elite` `StaticTier` band
  from `STATIC_TIER_REGISTRY` (the comparison point `world_info.md` itself uses)
- **THEN** the ratio is roughly 8-10x, not the roughly 100x ratio that would result from any
  vital-pool-derived formula

### Requirement: A caller may name a STATIC_TIER_REGISTRY tier to land inside a specific power band instead of the species floor
`world/rules/traits.py`'s trait-construction function SHALL accept an optional `tier` argument
naming a key in `world.lore.races.STATIC_TIER_REGISTRY`. When `tier` is omitted, construction SHALL
behave exactly as it does with no `tier` support (species floor). When `tier` is supplied, the
resulting `atk_phys`/`agility`/`defense` bases SHALL be read from that tier's own `.band` (its floor
value) rather than from `RaceProfile.static_baseline`'s species floor, and the `magic_power` base
SHALL be read from that tier's own `.magic_band` floor; `hp`/`mp`/`sp`
SHALL remain driven by `RaceProfile.vital_baseline` regardless of `tier`, since
`STATIC_TIER_REGISTRY` carries no vital dimension. This mechanism SHALL introduce no
randomization, stat-point allocation, or level-up curve — one named tier always produces one
deterministic value.

#### Scenario: A named tier places static traits inside that tier's own band
- **WHEN** a human `PlayerCharacter` is constructed with `tier="human_swordmaster"`
  (`STATIC_TIER_REGISTRY["human_swordmaster"].band == (18, 22)`)
- **THEN** `entity.traits.atk_phys`, `agility`, and `defense` bases each fall within `18`-`22`,
  and `entity.traits.magic_power`'s base equals `STATIC_TIER_REGISTRY["human_swordmaster"]
  .magic_band[0]`

#### Scenario: A different named tier on the same race places static traits inside its own, different band
- **WHEN** a human `PlayerCharacter` is constructed with `tier="human_commoner"`
  (`STATIC_TIER_REGISTRY["human_commoner"].band == (1, 5)`)
- **THEN** `entity.traits.atk_phys`, `agility`, and `defense` bases each fall within `1`-`5`, not
  `18`-`22`

#### Scenario: Requesting a tier that belongs to a different race fails loudly
- **WHEN** an elf `PlayerCharacter` is constructed with `tier="human_swordmaster"` (a tier whose
  `race_key` is `"human"`, not `"elf"`)
- **THEN** construction raises an error rather than silently returning a human-scale value on the
  elf entity or silently falling back to the elf species floor

#### Scenario: Omitting tier reproduces the unchanged species-floor behavior
- **WHEN** a `PlayerCharacter` or `NPC` is constructed with no `tier` argument
- **THEN** its static trait bases equal `RaceProfile.static_baseline`'s floor values, identical to
  construction before this tier-aware mechanism existed

### Requirement: Monster trait baselines read MonsterTier.static_band and hp_band directly, never a derived multiplier
`world/rules/traits.py` SHALL derive a `Monster`'s initial `atk_phys`/`agility`/`defense` static
bases from its `threat_tier`'s `MonsterTier.static_band`, and its initial `hp` gauge maximum from
`MonsterTier.hp_band`, reading both directly from `world.lore.monsters.MONSTER_TIER_REGISTRY`. No
module added by this change SHALL compute a monster trait value via a multiplier, ladder, or any
formula keyed to tier ordering — every value SHALL be a direct read of the tier's own documented
band.

#### Scenario: A calamity-tier monster's stats reflect MonsterTier.static_band and hp_band directly
- **WHEN** a `Monster` with `threat_tier="calamity"` is initialized
- **THEN** `entity.traits.atk_phys`'s base equals `MONSTER_TIER_REGISTRY["calamity"].static_band
  .atk_phys[0]` (60) and `entity.traits.hp`'s maximum equals
  `MONSTER_TIER_REGISTRY["calamity"].hp_band[0]` (1200) — neither value is computed from a
  power-of-ten multiplier or any other tier-ordering-derived formula

#### Scenario: Higher monster tiers have higher stats, per the tier's own documented band
- **WHEN** a `Monster` with `threat_tier="calamity"` is compared against a `Monster` with
  `threat_tier="low"` for the same trait
- **THEN** the calamity-tier monster's value is higher, because `MONSTER_TIER_REGISTRY["calamity"]`'s
  own `static_band`/`hp_band` values are higher than `MONSTER_TIER_REGISTRY["low"]`'s — not because
  a multiplier was applied to derive one from the other

#### Scenario: A Monster cannot be populated without a resolvable threat_tier
- **WHEN** trait population is requested for a `Monster` whose `threat_tier` does not exist in
  `MONSTER_TIER_REGISTRY`
- **THEN** population raises an error rather than silently defaulting to an arbitrary trait
  scale

#### Scenario: A Monster's mp, sp, and magic_power default to zero, not an invented value
- **WHEN** a `Monster` is initialized with any valid `threat_tier`
- **THEN** `entity.traits.mp` and `entity.traits.sp` maxima are `0` and
  `entity.traits.magic_power`'s base is `0`, since `MonsterTier` documents no numeric MP/SP/magic
  band and this change does not invent one (every tier's `static_band.magic_power` is `(0, 0)`)
