# Spec Delta

## MODIFIED Requirements

### Requirement: Static combat trait bases are read directly from RaceProfile.static_baseline, never derived from vital_baseline
`world/rules/traits.py` SHALL derive a `PlayerCharacter` or `NPC`'s initial `atk_phys`/`agility`/
`defense` static bases directly from `RaceProfile.static_baseline` (the species-wide floor-to-
ceiling band for those three stats), reading `world.lore.races.RACE_REGISTRY`. No module added by
this change SHALL compute a static trait value as a function of `vital_baseline` or
any other field that is not itself a static-stat field.

#### Scenario: Elf static trait bases reflect the race's static_baseline, not a vital-pool ratio
- **WHEN** an elf `PlayerCharacter`'s `entity.traits.atk_phys`, `agility`, and `defense` bases are
  inspected
- **THEN** each equals `RACE_REGISTRY["t_elf"].static_baseline`'s corresponding floor value (70), not
  a value computed from `RACE_REGISTRY["t_elf"].vital_baseline.hp` scaled against the human baseline

#### Scenario: Human static trait bases are single-digit, matching the source's sample data
- **WHEN** a human `PlayerCharacter`'s `entity.traits.atk_phys`, `agility`, and `defense` bases are
  inspected
- **THEN** each equals `RACE_REGISTRY["t_human"].static_baseline`'s corresponding floor value (1), and
  none exceeds the species-wide ceiling (22) ;  at no point does a freshly constructed human's static
  trait value fall in the tens-of-thousands, or even consistently above single digits, range

#### Scenario: The human-to-elf static ratio is roughly 10x, not the vital-pool's roughly 100x
- **WHEN** the elf `static_baseline` floor is compared against the `human_elite` `StaticTier` band
  from `STATIC_TIER_REGISTRY` (the comparison point `world_info.md` itself uses)
- **THEN** the ratio is roughly 8-10x, not the roughly 100x ratio that would result from any
  vital-pool-derived formula

#### Scenario: Vital pools and static combat stats are independently documented, not derivable
- **WHEN** a module attempted to compute a static combat stat from `vital_baseline` or any other
  non-static-stat field
- **THEN** it would be unsound: vital pools and static combat stats scale by different,
  independently documented factors between races, and neither is derivable from the other

#### Scenario: Fixed fixture distinguishes transformation from production tuning
- **WHEN** these mechanism cases run with independently authored synthetic race/subrace/tier data
- **THEN** exact fixture outcomes prove source selection and application order without any expected production balance table; numerical examples in these scenarios describe the fixed fixture rather than shipped-value approval


### Requirement: Subrace static_modifiers and vital_overrides apply in a fixed order: race baseline, then static_modifiers, then vital_overrides
When a `PlayerCharacter` or `NPC` has a `subrace` set, `world/rules/traits.py` SHALL apply
`Subrace.static_modifiers` to the race baseline second, and `Subrace.vital_overrides`
third, always in that order relative to the race baseline computed first. `vital_overrides`, where
present for a stat, SHALL replace that stat's `RaceProfile.vital_baseline`-derived value outright,
never blend or average with it.

#### Scenario: The two subrace adjustment kinds are fractional deltas and absolute band swaps
- **WHEN** a `Subrace`'s adjustments are applied to a race baseline
- **THEN** `static_modifiers` are fractional deltas over `atk_phys`/`agility`/`defense`
- **AND** `vital_overrides` are absolute band replacements for named vital stats

#### Scenario: A beastfolk subspecies' static_modifiers adjust the race baseline proportionally
- **WHEN** a beastfolk `NPC` with `subrace="t_catkin"` is initialized (catkin: atk_phys -0.10,
  agility +0.40, defense -0.30)
- **THEN** its `entity.traits.agility` base is higher than a `subrace="t_wolfkin"` beastfolk NPC's
  (wolfkin: all modifiers 0.0, i.e. unmodified), and its `entity.traits.defense` base is lower,
  both computed as the beastfolk race floor adjusted by catkin's respective fractional delta

#### Scenario: A subrace vital_override replaces the race baseline outright for that stat
- **WHEN** a beastfolk `NPC` with `subrace="t_foxkin"` is initialized (foxkin: `vital_overrides =
  {"mp": (50, 70)}`, against the beastfolk species `vital_baseline.mp` of `(30, 50)`)
- **THEN** `entity.traits.mp`'s maximum equals `50` (the override band's floor), not `30` (the
  unmodified species floor) and not a value blended between the two

#### Scenario: A subrace with no static_modifiers or vital_overrides leaves the race baseline unchanged
- **WHEN** an elf `PlayerCharacter` with `subrace="fionnen"` (all `static_modifiers` zero,
  `vital_overrides=None`) is initialized
- **THEN** every trait's initial value equals the plain elf race-baseline value, identical to an
  elf entity constructed with no subrace at all

#### Scenario: Fixed fixture distinguishes transformation from production tuning
- **WHEN** these mechanism cases run with independently authored synthetic race/subrace/tier data
- **THEN** exact fixture outcomes prove source selection and application order without any expected production balance table; numerical examples in these scenarios describe the fixed fixture rather than shipped-value approval


### Requirement: A caller may name a STATIC_TIER_REGISTRY tier to land inside a specific power band instead of the species floor
`world/rules/traits.py`'s trait-construction function SHALL accept an optional `tier` argument
naming a key in `world.lore.races.STATIC_TIER_REGISTRY`. When `tier` is supplied, the
resulting `atk_phys`/`agility`/`defense` bases SHALL be read from that tier's own `.band` (its floor
value) rather than from `RaceProfile.static_baseline`'s species floor, and the `magic_power` base
SHALL be read from that tier's own `.magic_band` floor.

#### Scenario: A named tier places static traits inside that tier's own band
- **WHEN** a human `PlayerCharacter` is constructed with `tier="t_human_swordmaster"`
  (`STATIC_TIER_REGISTRY["t_human_swordmaster"].band == (18, 22)`)
- **THEN** `entity.traits.atk_phys`, `agility`, and `defense` bases each fall within `18`-`22`,
  and `entity.traits.magic_power`'s base equals `STATIC_TIER_REGISTRY["t_human_swordmaster"]
  .magic_band[0]`

#### Scenario: A different named tier on the same race places static traits inside its own, different band
- **WHEN** a human `PlayerCharacter` is constructed with `tier="t_human_commoner"`
  (`STATIC_TIER_REGISTRY["t_human_commoner"].band == (1, 5)`)
- **THEN** `entity.traits.atk_phys`, `agility`, and `defense` bases each fall within `1`-`5`, not
  `18`-`22`

#### Scenario: Requesting a tier that belongs to a different race fails loudly
- **WHEN** an elf `PlayerCharacter` is constructed with `tier="t_human_swordmaster"` (a tier whose
  `race_key` is `"t_human"`, not `"t_elf"`)
- **THEN** construction raises an error rather than silently returning a human-scale value on the
  elf entity or silently falling back to the elf species floor

#### Scenario: Omitting tier reproduces the unchanged species-floor behavior
- **WHEN** a `PlayerCharacter` or `NPC` is constructed with no `tier` argument
- **THEN** its static trait bases equal `RaceProfile.static_baseline`'s floor values, identical to
  construction before this tier-aware mechanism existed

#### Scenario: Vitals ignore the tier because the registry carries no vital dimension
- **WHEN** a `PlayerCharacter` or `NPC` is constructed with any `tier`
- **THEN** `hp`/`mp`/`sp` remain driven by `RaceProfile.vital_baseline` regardless of `tier`, since
  `STATIC_TIER_REGISTRY` carries no vital dimension

#### Scenario: Tier selection is purely deterministic
- **WHEN** the tier mechanism is exercised across any constructions
- **THEN** it introduces no randomization, stat-point allocation, or level-up curve ;  one named
  tier always produces one deterministic value

#### Scenario: Fixed fixture distinguishes transformation from production tuning
- **WHEN** these mechanism cases run with independently authored synthetic race/subrace/tier data
- **THEN** exact fixture outcomes prove source selection and application order without any expected production balance table; numerical examples in these scenarios describe the fixed fixture rather than shipped-value approval

