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

### Requirement: Race-driven gauge and counter initial values come from RaceProfile, never a hardcoded per-race number
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
- **THEN** `entity.traits.magic_level`'s maximum equals `RACE_REGISTRY[race].magic_cap`, and its
  current value starts at `0` (a new character has not yet reached the race's cap)

#### Scenario: The vital-pool gap between human and elf propagates from lore to the entity
- **WHEN** an elf `PlayerCharacter`'s `entity.traits.hp` maximum is compared against a human
  `PlayerCharacter`'s `entity.traits.hp` maximum
- **THEN** the elf value is at least 50 times the human value, matching the same magnitude
  assertion change 2 makes directly on `RaceProfile.vital_baseline`

### Requirement: Static combat trait bases are read directly from RaceProfile.static_baseline, never derived from vital_baseline
`world/rules/traits.py` SHALL derive a `PlayerCharacter` or `NPC`'s initial `atk_phys`/`agility`/
`defense` static bases directly from `RaceProfile.static_baseline` (the species-wide floor-to-
ceiling band for those three stats), reading `world.lore.races.RACE_REGISTRY`. No module added by
this change SHALL compute a static trait value as a function of `vital_baseline`, `magic_cap`, or
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

### Requirement: Subrace static_modifiers and vital_overrides apply in a fixed order: race baseline, then static_modifiers, then vital_overrides
When a `PlayerCharacter` or `NPC` has a `subrace` set, `world/rules/traits.py` SHALL apply
`Subrace.static_modifiers` (fractional deltas over `atk_phys`/`agility`/`defense`) to the race
baseline second, and `Subrace.vital_overrides` (absolute band replacements for named vital stats)
third, always in that order relative to the race baseline computed first. `vital_overrides`, where
present for a stat, SHALL replace that stat's `RaceProfile.vital_baseline`-derived value outright,
never blend or average with it.

#### Scenario: A beastfolk subspecies' static_modifiers adjust the race baseline proportionally
- **WHEN** a beastfolk `NPC` with `subrace="catkin"` is initialized (catkin: atk_phys -0.10,
  agility +0.40, defense -0.30)
- **THEN** its `entity.traits.agility` base is higher than a `subrace="wolfkin"` beastfolk NPC's
  (wolfkin: all modifiers 0.0, i.e. unmodified), and its `entity.traits.defense` base is lower,
  both computed as the beastfolk race floor adjusted by catkin's respective fractional delta

#### Scenario: A subrace vital_override replaces the race baseline outright for that stat
- **WHEN** a beastfolk `NPC` with `subrace="foxkin"` is initialized (foxkin: `vital_overrides =
  {"mp": (50, 70)}`, against the beastfolk species `vital_baseline.mp` of `(30, 50)`)
- **THEN** `entity.traits.mp`'s maximum equals `50` (the override band's floor), not `30` (the
  unmodified species floor) and not a value blended between the two

#### Scenario: A subrace with no static_modifiers or vital_overrides leaves the race baseline unchanged
- **WHEN** an elf `PlayerCharacter` with `subrace="fionnen"` (all `static_modifiers` zero,
  `vital_overrides=None`) is initialized
- **THEN** every trait's initial value equals the plain elf race-baseline value, identical to an
  elf entity constructed with no subrace at all

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

#### Scenario: A Monster cannot be constructed without a resolvable threat_tier
- **WHEN** a `Monster` is initialized with a `threat_tier` value that does not exist in
  `MONSTER_TIER_REGISTRY`
- **THEN** initialization raises an error rather than silently defaulting to an arbitrary trait
  scale

#### Scenario: A Monster's mp, sp, and magic_level default to zero, not an invented value
- **WHEN** a `Monster` is initialized with any valid `threat_tier`
- **THEN** `entity.traits.mp` and `entity.traits.sp` maxima are `0` and `entity.traits.magic_level`'s
  maximum is `0`, since `MonsterTier` documents no numeric MP/SP/magic band and this change does not
  invent one

### Requirement: guild_merit starts at zero with no upper bound
`world/rules/traits.py` SHALL initialize every `LivingEntity`'s `guild_merit` counter at `0` with
no maximum, since no lore source specifies a merit cap.

#### Scenario: guild_merit has no maximum
- **WHEN** `entity.traits.guild_merit` is inspected on a freshly created entity
- **THEN** its current value is `0` and it has no configured maximum

### Requirement: Every stored static trait value is a base value, never a skill-multiplied value
Every `atk_phys`/`agility`/`defense` value `world/rules/traits.py` derives or `TraitHandler` stores
SHALL be a base value falling within the constructing race's or monster tier's documented
`StaticBand`/`static_band` range. This change SHALL NOT apply, and SHALL NOT provide any mechanism
that applies, a skill multiplier (×10/×100/×1000) to a value before it is stored in `entity.traits`.

#### Scenario: A freshly constructed entity's static traits never exceed the documented band
- **WHEN** any `PlayerCharacter`, `NPC`, or `Monster` is constructed via this change's derivation
  functions
- **THEN** every one of `entity.traits.atk_phys`, `agility`, `defense`'s base values falls within
  the exact `StaticBand`/`static_band` range documented for that race/tier — none falls in a range
  that would only be reachable by applying a ×10/×100/×1000 skill multiplier first

#### Scenario: No module added by this change contains skill-multiplier application logic
- **WHEN** `world/rules/traits.py` is inspected
- **THEN** it contains no function that multiplies a stored trait value by 10, 100, or 1000, and no
  reference to a skill-multiplier mechanism — that logic belongs to change 5 (skill effects) and
  change 9 (combat math), applied only at resolution time, never written back into `entity.traits`
