# lore-registries delta (magic-power-static-rename)

## MODIFIED Requirements

### Requirement: RaceProfile encodes the three-race power gap
`world/lore/races.py` SHALL define a frozen `RaceProfile` dataclass with exactly the fields
`key`, `lifespan`, `vital_baseline`, `static_baseline`, `learning_multiplier`, and
`can_use_divine_arts`, and a module-level `RACE_REGISTRY: dict[str, RaceProfile]` containing
exactly three entries keyed `"human"`, `"beastfolk"`, and `"elf"`. `StaticBand` SHALL be
four-dimensional — `atk_phys`, `agility`, `defense`, and `magic_power`, each a
`tuple[int, int]` — and the race `static_baseline` SHALL carry the growth-redesign interim
bands: human `(1, 22)` on the three combat axes with `magic_power (5, 90)`, beastfolk
`(4, 34)` with `magic_power (1, 30)`, elf `(70, 95)` with `magic_power (100, 900)`. The
former `magic_cap` and `starting_magic_level` fields SHALL NOT exist: the fourth
`static_baseline` axis is the only race-owned magic-power bound, and no race-owned magic
average survives.

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
  ceiling, 14) — **not** `RACE_REGISTRY["human"].static_baseline`'s species-wide ceiling, which
  includes the S-rank 大劍豪 tier and would understate the ratio
- **THEN** the ratio is between 5× and 15×, reflecting `world_info.md`'s own worked comparison
  ("對照人類精銳(7-14)約為8-10倍，與設定文字「10倍」相符") — and this ratio is checked
  independently of the vital-pool ratio above; neither scenario's assertion may be satisfied by
  deriving one band from the other

#### Scenario: Only elves can use divine arts
- **WHEN** `RACE_REGISTRY` is inspected
- **THEN** `can_use_divine_arts` is `True` for `"elf"` and `False` for `"human"` and `"beastfolk"`

#### Scenario: magic_power band ordering matches the documented gap
- **WHEN** the three races' `static_baseline.magic_power` bands are compared
- **THEN** every upper bound of `beastfolk` is below every lower bound of `human`, and every
  upper bound of `human` is below every lower bound of `elf`, matching the interim table
  1–30 / 5–90 / 100–900, and no `RaceProfile` field named `magic_cap` or
  `starting_magic_level` exists anywhere in the dataclass

#### Scenario: The fourth band axis is mandatory and integral
- **WHEN** every `StaticBand` instance in the registry modules is inspected
- **THEN** each carries a `magic_power` tuple of two integers with a non-decreasing range, for
  every race baseline and every monster tier band

### Requirement: StaticTier registry records named power bands within each race's static_baseline
`world/lore/races.py` SHALL define a frozen `StaticTier` dataclass with fields `key`, `race_key`,
`display_name_zh`, `order`, `band: tuple[int, int | None]`, `magic_band: tuple[int, int]`,
`guild_rank_hint`, and `description`, and a module-level
`STATIC_TIER_REGISTRY: dict[str, StaticTier]` containing five human tiers, four beastfolk tiers,
and two elf tiers. `band` remains the shared physical-power band applied to
`atk_phys`/`agility`/`defense`; `magic_band` is the tier's own deterministic `magic_power`
floor-to-ceiling band, replacing the deleted race-level `starting_magic_level` as the source of
tier-built NPC and profile magic power. Registry load SHALL validate every `magic_band` is a
subset of the owning race's `static_baseline.magic_power` band.

#### Scenario: Every tier references a real race and stays within that race's static_baseline
- **WHEN** every entry in `STATIC_TIER_REGISTRY` is inspected
- **THEN** each entry's `race_key` exists as a key in `RACE_REGISTRY`, and each entry's `band` falls
  within (or, for the top tier of a race, extends to) that race's `static_baseline` range on every
  combat axis, and each entry's `magic_band` is a subset of that race's
  `static_baseline.magic_power` range

#### Scenario: Human tiers are ordered and reach the species ceiling
- **WHEN** the five human tiers are sorted by `order`
- **THEN** the sequence is 平民與非戰鬥者, 一般冒險者, 精銳, 一流, 大劍豪 with strictly increasing
  `order`, and the highest tier's `band` upper bound equals `RACE_REGISTRY["human"]
  .static_baseline.atk_phys[1]` (22) — a human S-rank adventurer is numerically representable, not
  capped out by a narrower species band

#### Scenario: Old magic lore anchors survive as tier magic bands
- **WHEN** `STATIC_TIER_REGISTRY["human_adventurer"].magic_band` is inspected
- **THEN** it is mid-band within the human `magic_power` band (5–90), anchored on the old human
  average 30, and the 平民 tier's `magic_band` lower bound is the race floor 5 while the 大劍豪
  tier's upper bound is the race ceiling 90 — the race magic band is spanned deterministically by
  the tier ladder instead of the deleted `starting_magic_level`

#### Scenario: Guild rank hints are present only where world_info.md states them
- **WHEN** every `StaticTier` entry is inspected
- **THEN** `guild_rank_hint` is a non-`None` `GuildRank` key for every human tier above 平民 (F-D,
  C-B, A, S), and `None` for every beastfolk and elf tier, since `world_info.md` does not state a
  guild-rank correlation for those two races; the single-key hints are the lower bound of each
  documented band (`"F"`, `"C"`, `"A"`, and `"S"` respectively)

#### Scenario: An open-ended top tier is representable
- **WHEN** `STATIC_TIER_REGISTRY["elf_prodigy"]` is inspected
- **THEN** its `band` is `(95, None)`, where `None` records the source's lack of a hard ceiling,
  while its `magic_band` is a closed two-integer tuple within the elf `magic_power` band (no
  open-ended magic dimension exists)

#### Scenario: A magic_band outside the race band fails registry load
- **WHEN** a `StaticTier` is constructed with a `magic_band` whose endpoints fall outside the
  owning race's `static_baseline.magic_power` band
- **THEN** registry load raises a named error rather than accepting the deviating tier

## REMOVED Requirements

### Requirement: RankTitle registry is ordered and references magic tiers
**Reason**: the magic-rank display ladder (學徒/術師/大師/賢者/主宰) advertises the XP
system being retired; the title-system change line (`title-fixed-core`) owns title
presentation.
**Migration**: `RANK_TITLE_REGISTRY`, `RankTitle`, and the `rank_titles` DB mirror category are
deleted outright; `MAGIC_TIER_REGISTRY` (cost-tier bands) stays untouched as data labels. No
replacement exists yet in this change — interim display surfaces drop the rank line (see
`webclient-contextual-hud`).
