## MODIFIED Requirements

### Requirement: RaceProfile encodes the three-race power gap
`world/lore/races.py` SHALL define a frozen `RaceProfile` dataclass with exactly
the fields `key`, `lifespan`, `magic_cap`, `starting_magic_level`,
`vital_baseline`, `static_baseline`, `learning_multiplier`, and
`can_use_divine_arts`, and a module-level `RACE_REGISTRY: dict[str, RaceProfile]`
containing exactly three entries keyed `"human"`, `"beastfolk"`, and `"elf"`.

#### Scenario: Registry has exactly the three documented races
- **WHEN** `RACE_REGISTRY` is inspected
- **THEN** it contains exactly the keys `"human"`, `"beastfolk"`, and `"elf"`,
  each mapping to a `RaceProfile` instance, and no other keys

#### Scenario: Elf sits roughly two orders of magnitude above human on vital pools
- **WHEN** `RACE_REGISTRY["elf"].vital_baseline.hp[0]` (the elf HP baseline) is
  compared against `RACE_REGISTRY["human"].vital_baseline.hp[1]` (the human HP
  gifted ceiling)
- **THEN** the elf value is at least 50 times the human value, reflecting the
  documented 120-150-vs-10000 gap design doc §5.1 depends on

#### Scenario: Elf sits roughly one order of magnitude above the human elite tier on static stats
- **WHEN** `RACE_REGISTRY["elf"].static_baseline.atk_phys[0]` (the elf
  `atk_phys` floor) is compared against
  `STATIC_TIER_REGISTRY["human_elite"].band[1]` (the human 精銳-tier `atk_phys`
  ceiling, 14) — **not** `RACE_REGISTRY["human"].static_baseline`'s
  species-wide ceiling, which includes the S-rank 大劍豪 tier and would
  understate the ratio
- **THEN** the ratio is between 5× and 15×, reflecting `world_info.md`'s own
  worked comparison ("對照人類精銳(7-14)約為8-10倍，與設定文字「10倍」相符") — and this
  ratio is checked independently of the vital-pool ratio above; neither
  scenario's assertion may be satisfied by deriving one band from the other

#### Scenario: Only elves can use divine arts
- **WHEN** `RACE_REGISTRY` is inspected
- **THEN** `can_use_divine_arts` is `True` for `"elf"` and `False` for `"human"`
  and `"beastfolk"`

#### Scenario: magic_cap ordering matches the documented gap
- **WHEN** the three races' `magic_cap` values are compared
- **THEN** `beastfolk.magic_cap < human.magic_cap < elf.magic_cap`, matching 30
  / 90 / 900

#### Scenario: Starting magic averages are immutable and cap-safe
- **WHEN** the three races' `starting_magic_level` values are inspected
- **THEN** they are respectively 30, 10, and 300 for human, beastfolk, and elf,
  each is an integer greater than zero and no greater than that race's
  `magic_cap`
