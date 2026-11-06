## MODIFIED Requirements

### Requirement: RaceProfile encodes the three-race power gap
`world/lore/races.py` SHALL define a frozen `RaceProfile` dataclass with exactly the fields `key`, `lifespan`, `vital_baseline`, `static_baseline`, `learning_multiplier`, `can_use_divine_arts`, `description`, `display_name_zh`, and `allowed_sexes`, and a module-level `RACE_REGISTRY: dict[str, RaceProfile]` containing exactly three entries keyed `"human"`, `"beastfolk"`, and `"elf"`.

#### Scenario: Registry has exactly the three documented races
- **WHEN** `RACE_REGISTRY` is inspected
- **THEN** it contains exactly the keys `"human"`, `"beastfolk"`, and `"elf"`, each mapping to a
  `RaceProfile` instance, and no other keys

#### Scenario: Elf sits roughly two orders of magnitude above human on vital pools
- **WHEN** `RACE_REGISTRY["elf"].vital_baseline.hp[0]` (the elf HP baseline) is compared against
  `RACE_REGISTRY["human"].vital_baseline.hp[1]` (the human HP gifted ceiling)
- **THEN** the elf value is at least 50 times the human value, reflecting the documented
  120-150-vs-10000 gap design doc §5.1 depends on

#### Scenario: Elf sits roughly one order of magnitude above the human elite tier on static stats
- **WHEN** `RACE_REGISTRY["elf"].static_baseline.atk_phys[0]` (the elf `atk_phys` floor) is
  compared against `STATIC_TIER_REGISTRY["human_elite"].band[1]` (the human 精銳-tier `atk_phys`
  ceiling, 14) ;  **not** `RACE_REGISTRY["human"].static_baseline`'s species-wide ceiling, which
  includes the S-rank 大劍豪 tier and would understate the ratio
- **THEN** the ratio is between 5× and 15×, reflecting `world_info.md`'s own worked comparison
  ("對照人類精銳(7-14)約為8-10倍，與設定文字「10倍」相符") ;  and this ratio is checked
  independently of the vital-pool ratio above; neither scenario's assertion may be satisfied by
  deriving one band from the other

#### Scenario: Only elves can use divine arts
- **WHEN** `RACE_REGISTRY` is inspected
- **THEN** `can_use_divine_arts` is `True` for `"elf"` and `False` for `"human"` and `"beastfolk"`

#### Scenario: magic_power band ordering matches the documented gap
- **WHEN** the three races' `static_baseline.magic_power` bands are compared
- **THEN** every upper bound of `beastfolk` is below every lower bound of `human`, and every
  upper bound of `human` is below every lower bound of `elf`, matching the interim table
  and authored band constraints, and no `RaceProfile` field named `magic_cap` or
  `starting_magic_level` exists anywhere in the dataclass

#### Scenario: The fourth band axis is mandatory and integral
- **WHEN** every `StaticBand` instance in the registry modules is inspected
- **THEN** each carries a `magic_power` tuple of two integers with a non-decreasing range, for
  every race baseline and every monster tier band

#### Scenario: StaticBand is four-dimensional
- **WHEN** `StaticBand` is inspected
- **THEN** it is four-dimensional ;  `atk_phys`, `agility`, `defense`, and `magic_power`, each a `tuple[int, int]`

#### Scenario: Race static baselines carry the growth-redesign interim bands
- **WHEN** the three races' `static_baseline` values are inspected
- **THEN** they carry explicit complete authored axis bands; exact endpoints are adjustable game data, with the existing independent power-gap and band-shape constraints retained

#### Scenario: The former magic fields do not exist and the fourth axis is the only bound
- **WHEN** `RaceProfile` is inspected
- **THEN** the former `magic_cap` and `starting_magic_level` fields SHALL NOT exist ;  the fourth `static_baseline` axis is the only race-owned magic-power bound, and no race-owned magic average survives

#### Scenario: Every race declares a non-empty permitted-sex subset
- **WHEN** every `RaceProfile.allowed_sexes` value is inspected
- **THEN** each is a non-empty tuple whose every member is a member of `SEX_VALUES`, and
  `SEX_VALUES` itself is unchanged at exactly `("female", "male", "other")`

#### Scenario: The elf declares female as its only permitted sex
- **WHEN** `RACE_REGISTRY["elf"].allowed_sexes` is inspected
- **THEN** it equals `("female",)`, while `"human"` and `"beastfolk"` each permit `SEX_VALUES` in full
